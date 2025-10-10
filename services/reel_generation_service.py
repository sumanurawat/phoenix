"""Reel Maker generation workflow orchestration."""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

from firebase_admin import firestore

from services.realtime_event_bus import realtime_event_bus
from services.reel_project_service import reel_project_service, ReelProject
from services.reel_storage_service import reel_storage_service
from services.veo_video_generation_service import VeoGenerationParams, veo_video_service
from services.website_stats_service import WebsiteStatsService

logger = logging.getLogger(__name__)

# Firestore collection for background jobs
JOBS_COLLECTION = "reel_maker_jobs"


@dataclass
class GenerationContext:
    project: ReelProject
    user_id: str
    user_email: str
    prompts: List[str]
    job_id: str

    @property
    def topic(self) -> str:
        return f"reel-project:{self.project.project_id}"

    @property
    def aspect_ratio(self) -> str:
        return "9:16" if self.project.orientation == "portrait" else "16:9"

    @property
    def compression_quality(self) -> Optional[str]:
        allowed = {"optimized", "lossless"}
        return self.project.compression if self.project.compression in allowed else None


class ReelGenerationService:
    """Coordinates Veo video generation for reel projects."""

    def __init__(
        self,
        project_service=reel_project_service,
        storage_service=reel_storage_service,
        veo_service=veo_video_service,
        db=None,
        stats_service=None,
    ):
        self.project_service = project_service
        self.storage = storage_service
        self.veo = veo_service
        self.db = db or firestore.client()
        self.stats_service = stats_service or WebsiteStatsService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start_generation(
        self,
        project_id: str,
        user_id: str,
        user_email: str,
        prompts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Kick off asynchronous clip generation for a project."""
        project = self.project_service.get_project(project_id, user_id)
        if not project:
            raise ValueError("Project not found or access denied")

        if prompts is None:
            prompts = project.prompt_list or []

        cleaned_prompts = [str(p).strip() for p in prompts if str(p).strip()]
        if not cleaned_prompts:
            raise ValueError("At least one prompt is required to start generation")
        if len(cleaned_prompts) > 50:
            raise ValueError("A maximum of 50 prompts is supported per generation job")

        # Ensure storage bucket configured before we spawn worker threads
        try:
            bucket_name = self.storage.bucket_name
        except RuntimeError as exc:
            logger.error("Cannot start reel generation: %s", exc)
            raise

        job_id = f"reeljob-{uuid.uuid4().hex[:12]}"

        # Persist job record for observability
        job_doc = {
            "jobId": job_id,
            "projectId": project.project_id,
            "userId": user_id,
            "userEmail": user_email,
            "status": "queued",
            "promptCount": len(cleaned_prompts),
            "completedPrompts": 0,
            "failedPrompts": 0,
            "clipRelativePaths": [],
            "bucket": bucket_name,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "error": None,
        }
        self.db.collection(JOBS_COLLECTION).document(job_id).set(job_doc)

        # Smart clip preservation: keep existing clips, only generate missing ones
        existing_clips = project.clip_filenames or []
        preserved_clips = []
        
        # Build initial clip array matching prompt count
        # Fill with existing clips where available, None for missing
        for idx in range(len(cleaned_prompts)):
            if idx < len(existing_clips) and existing_clips[idx]:
                # Verify the clip still exists in GCS (optional but safer)
                clip_path = existing_clips[idx]
                try:
                    blob = self.storage._ensure_bucket().blob(clip_path)
                    if blob.exists():
                        preserved_clips.append(clip_path)
                        logger.info(f"Preserving existing clip {idx} for project {project.project_id}")
                    else:
                        preserved_clips.append(None)
                        logger.warning(f"Clip {idx} missing from GCS, will regenerate: {clip_path}")
                except Exception as e:
                    # If verification fails, assume we need to regenerate
                    preserved_clips.append(None)
                    logger.warning(f"Failed to verify clip {idx}, will regenerate: {e}")
            else:
                # No existing clip at this index
                preserved_clips.append(None)
        
        clips_to_generate = sum(1 for clip in preserved_clips if clip is None)
        clips_preserved = len(preserved_clips) - clips_to_generate
        
        logger.info(
            f"Project {project.project_id}: {clips_preserved}/{len(cleaned_prompts)} clips exist, "
            f"{clips_to_generate} need generation"
        )

        # Update project state upfront (preserve existing clips, mark generating)
        self.project_service.update_project(
            project.project_id,
            user_id,
            prompt_list=cleaned_prompts,
            clip_filenames=preserved_clips,
            stitched_filename=None if clips_to_generate > 0 else project.stitched_filename,
            status="generating",
            error_info=None,
        )

        # Update in-memory snapshot so worker thread reads current values
        project.prompt_list = cleaned_prompts
        project.status = "generating"
        project.clip_filenames = preserved_clips

        ctx = GenerationContext(
            project=project,
            user_id=user_id,
            user_email=user_email,
            prompts=cleaned_prompts,
            job_id=job_id,
        )

        realtime_event_bus.publish(
            ctx.topic,
            "job.accepted",
            {
                "jobId": job_id,
                "promptCount": len(cleaned_prompts),
                "bucket": bucket_name,
            },
        )

        thread = threading.Thread(target=self._process_job, args=(ctx,), daemon=True)
        thread.start()

        return {"jobId": job_id, "promptCount": len(cleaned_prompts)}

    @staticmethod
    def topic_for_project(project_id: str) -> str:
        return f"reel-project:{project_id}"

    def get_job(self, job_id: str, user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.collection(JOBS_COLLECTION).document(job_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        if data.get("userId") != user_id or data.get("projectId") != project_id:
            return None
        return data
    
    def check_stale_jobs(self, timeout_minutes: int = 30) -> List[str]:
        """
        Find jobs stuck in 'processing' for >timeout_minutes and mark them as failed.
        Returns list of affected project IDs.
        
        This prevents projects from being stuck in 'generating' state forever
        if generation crashes or times out.
        """
        from datetime import datetime, timedelta
        
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        stale_projects = []
        
        try:
            # Query jobs that have been processing for too long
            jobs = self.db.collection(JOBS_COLLECTION)\
                .where(filter=firestore.FieldFilter('status', '==', 'processing'))\
                .stream()
            
            for job_doc in jobs:
                job_data = job_doc.to_dict()
                started_at = job_data.get('startedAt')
                
                # Skip if no start time or started recently
                if not started_at:
                    continue
                
                # Convert Firestore timestamp to datetime
                if hasattr(started_at, 'timestamp'):
                    started_dt = datetime.fromtimestamp(started_at.timestamp())
                else:
                    continue
                
                # Check if job is stale
                if started_dt < cutoff:
                    project_id = job_data.get('projectId')
                    user_id = job_data.get('userId')
                    
                    logger.warning(
                        f"Detected stale job {job_doc.id} for project {project_id} "
                        f"(started {started_dt}, cutoff {cutoff})"
                    )
                    
                    # Mark job as failed
                    job_doc.reference.update({
                        'status': 'failed',
                        'error': f'Job timed out after {timeout_minutes} minutes',
                        'updatedAt': firestore.SERVER_TIMESTAMP
                    })
                    
                    # Update project status
                    if project_id and user_id:
                        try:
                            self.project_service.update_project(
                                project_id,
                                user_id,
                                status='error',
                                error_info={'message': f'Generation timed out after {timeout_minutes} minutes'}
                            )
                            stale_projects.append(project_id)
                        except Exception as e:
                            logger.error(f"Failed to update project {project_id} after timeout: {e}")
        
        except Exception as e:
            logger.error(f"Failed to check stale jobs: {e}")
        
        return stale_projects

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _process_job(self, ctx: GenerationContext) -> None:
        job_ref = self.db.collection(JOBS_COLLECTION).document(ctx.job_id)
        
        # Start with preserved clips from project (if prompts unchanged)
        clip_paths: List[str] = list(ctx.project.clip_filenames or [])
        completed = 0

        try:
            job_ref.update({"status": "processing", "startedAt": firestore.SERVER_TIMESTAMP, "updatedAt": firestore.SERVER_TIMESTAMP})
        except Exception:
            logger.debug("Failed to update job status to processing", exc_info=True)

        for idx, prompt in enumerate(ctx.prompts):
            # Skip if we already have a clip for this prompt index
            if idx < len(clip_paths) and clip_paths[idx]:
                logger.info(f"Skipping prompt {idx} for project {ctx.project.project_id} - clip already exists: {clip_paths[idx]}")
                completed += 1
                
                realtime_event_bus.publish(
                    ctx.topic,
                    "prompt.completed",
                    {
                        "jobId": ctx.job_id,
                        "promptIndex": idx,
                        "clipRelativePaths": [clip_paths[idx]],
                        "skipped": True,
                    },
                )
                continue

            realtime_event_bus.publish(
                ctx.topic,
                "prompt.started",
                {"jobId": ctx.job_id, "promptIndex": idx, "prompt": prompt},
            )

            try:
                clip_paths_for_prompt = self._generate_single_prompt(ctx, idx, prompt)
                
                # Insert the new clip at the correct index (or extend if at end)
                if idx < len(clip_paths):
                    clip_paths[idx] = clip_paths_for_prompt[0] if clip_paths_for_prompt else None
                else:
                    clip_paths.extend(clip_paths_for_prompt)
                    
                completed += 1

                # Increment global stats for video seconds generated
                video_duration = ctx.project.duration_seconds or 8
                try:
                    self.stats_service.increment_video_seconds_generated(video_duration)
                except Exception as stats_error:
                    logger.warning(f"Failed to update video stats: {stats_error}")

                job_ref.update(
                    {
                        "completedPrompts": completed,
                        "clipRelativePaths": clip_paths,
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                    }
                )

                self.project_service.update_project(
                    ctx.project.project_id,
                    ctx.user_id,
                    clip_filenames=clip_paths,
                    status="generating",
                    error_info=None,
                )

                realtime_event_bus.publish(
                    ctx.topic,
                    "prompt.completed",
                    {
                        "jobId": ctx.job_id,
                        "promptIndex": idx,
                        "clipRelativePaths": clip_paths_for_prompt,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - want to capture any runtime failure
                logger.exception("Prompt generation failed for project %s", ctx.project.project_id)
                error_message = str(exc)
                failed = len(ctx.prompts) - completed

                job_ref.update(
                    {
                        "status": "failed",
                        "failedPrompts": failed,
                        "clipRelativePaths": clip_paths,
                        "completedPrompts": completed,
                        "error": error_message,
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                    }
                )

                self.project_service.update_project(
                    ctx.project.project_id,
                    ctx.user_id,
                    status="error",
                    error_info={"message": error_message},
                )

                realtime_event_bus.publish(
                    ctx.topic,
                    "prompt.failed",
                    {
                        "jobId": ctx.job_id,
                        "promptIndex": idx,
                        "error": error_message,
                    },
                )

                realtime_event_bus.publish(
                    ctx.topic,
                    "job.failed",
                    {
                        "jobId": ctx.job_id,
                        "completedPrompts": completed,
                        "failedPrompts": failed,
                        "error": error_message,
                    },
                )
                return

        # If all prompts succeeded
        try:
            job_ref.update(
                {
                    "status": "completed",
                    "clipRelativePaths": clip_paths,
                    "completedPrompts": completed,
                    "failedPrompts": 0,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                    "completedAt": firestore.SERVER_TIMESTAMP,
                    "error": None,
                }
            )
        except Exception:
            logger.debug("Failed to update job status to completed", exc_info=True)

        # Get current project to preserve stitched filename if it exists
        try:
            current_project = self.project_service.get_project(ctx.project.project_id, ctx.user_id)
            stitched_filename = current_project.stitched_filename
        except Exception:
            stitched_filename = None
            logger.debug("Could not fetch project to preserve stitched filename", exc_info=True)

        update_fields = {
            "clip_filenames": clip_paths,
            "status": "ready",
            "error_info": None,
        }
        
        # Preserve stitched filename if it exists
        if stitched_filename:
            update_fields["stitched_filename"] = stitched_filename
            logger.info(f"Preserved stitched filename for project {ctx.project.project_id}: {stitched_filename}")

        self.project_service.update_project(
            ctx.project.project_id,
            ctx.user_id,
            **update_fields
        )

        realtime_event_bus.publish(
            ctx.topic,
            "job.completed",
            {
                "jobId": ctx.job_id,
                "clipRelativePaths": clip_paths,
                "completedPrompts": completed,
            },
        )

    def _generate_single_prompt(self, ctx: GenerationContext, prompt_index: int, prompt: str) -> List[str]:
        """Generate clips for a single prompt and persist the outputs."""
        storage_uri = self._build_storage_uri(ctx, prompt_index)
        logger.info("Generating video for prompt %d with storage_uri: %s", prompt_index, storage_uri)
        
        params = VeoGenerationParams(
            model=ctx.project.model or "veo-3.0-fast-generate-001",
            prompt=prompt,
            aspect_ratio=ctx.aspect_ratio,
            duration_seconds=ctx.project.duration_seconds or 8,
            enhance_prompt=True,
            sample_count=1,
            generate_audio=ctx.project.audio_enabled,
            storage_uri=storage_uri,
            compression_quality=ctx.compression_quality,
        )

        result = self.veo.start_generation(params, poll=True)
        if not result.success:
            error_msg = result.error or "Video generation failed"
            logger.error("Veo generation failed for prompt %d: %s", prompt_index, error_msg)
            raise RuntimeError(error_msg)

        clip_uris: List[str] = []
        if result.gcs_uris:
            clip_uris.extend(result.gcs_uris)
        else:
            clip_uris.extend(self._persist_non_gcs_outputs(ctx, prompt_index, result))

        if not clip_uris:
            logger.error(
                "Generation completed but no video outputs were returned. "
                "GCS URIs: %s, Video bytes count: %d, Local paths: %s",
                result.gcs_uris,
                len(result.video_bytes) if result.video_bytes else 0,
                result.local_paths
            )
            raise RuntimeError(
                "Generation completed but no video outputs were returned. "
                "This may indicate an API error or unexpected response format."
            )

        return [self.storage.extract_relative_path(uri) for uri in clip_uris]

    def _build_storage_uri(self, ctx: GenerationContext, prompt_index: int) -> str:
        prefix = self.storage.clip_prefix_for_prompt(
            ctx.user_id,
            ctx.project.project_id,
            ctx.job_id,
            prompt_index,
        )
        # Vertex AI expects a GCS URI prefix; ensure trailing slash
        return self.storage.to_gcs_uri(f"{prefix}/")

    def _persist_non_gcs_outputs(self, ctx: GenerationContext, prompt_index: int, result) -> List[str]:
        """Upload local file outputs or raw bytes to GCS and return their URIs."""
        uris: List[str] = []
        if result.local_paths:
            for path_str in result.local_paths:
                path = Path(path_str)
                filename = path.name or f"clip_{ctx.job_id}_{prompt_index:02d}.mp4"
                relative_path = self.storage.clip_destination_path(
                    ctx.user_id,
                    ctx.project.project_id,
                    ctx.job_id,
                    prompt_index,
                    filename,
                )
                gcs_uri = self.storage.upload_file(str(path), relative_path)
                uris.append(gcs_uri)
        elif result.video_bytes:
            for idx, payload in enumerate(result.video_bytes):
                filename = f"clip_{ctx.job_id}_{prompt_index:02d}_{idx:02d}.mp4"
                relative_path = self.storage.clip_destination_path(
                    ctx.user_id,
                    ctx.project.project_id,
                    ctx.job_id,
                    prompt_index,
                    filename,
                )
                gcs_uri = self.storage.upload_bytes(payload, relative_path)
                uris.append(gcs_uri)
        return uris


# Singleton instance
reel_generation_service = ReelGenerationService()
