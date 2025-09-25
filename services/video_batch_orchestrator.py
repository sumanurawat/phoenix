"""Video Batch Orchestrator

Phase 1 implementation:
 - Creates job + prompt message docs
 - Spawns background thread to process prompts sequentially (simple, deterministic)
 - Updates Firestore per prompt and aggregate job doc counters
 - Publishes realtime events through in-process event bus
 - Supports basic concatenate (placeholder – operates on local paths / gcsUris list)

Future (not yet): true asyncio concurrency / distributed workers / retry queue.
"""
from __future__ import annotations

import asyncio
import uuid
import logging
import threading
import time
from typing import List, Dict, Any, Optional
from firebase_admin import firestore

from services.veo_video_generation_service import VeoVideoGenerationService, VeoGenerationParams
from services.video_processing_service import VideoProcessingService
from services.realtime_event_bus import realtime_event_bus
from services.video_prompt_parser import VideoPromptParser
from services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class VideoBatchOrchestrator:
    def __init__(self, db=None,
                 generation_svc: Optional[VeoVideoGenerationService] = None,
                 processing_svc: Optional[VideoProcessingService] = None,
                 parser: Optional[VideoPromptParser] = None):
        self.db = db or firestore.client()
        self.generation = generation_svc or VeoVideoGenerationService()
        self.processing = processing_svc or VideoProcessingService()
        self.parser = parser or VideoPromptParser()
        self._tasks: Dict[str, List[asyncio.Task]] = {}

    def start_batch(self, conversation_id: str, user_id: str, user_email: str, prompts: List[str], options: Dict[str, Any]) -> Dict[str, Any]:
        """Create job + prompt messages and spawn background worker thread.

        Returns lightweight job summary immediately.
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job_doc = {
            "job_id": job_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "status": "pending",
            "video_urls": [],
            "final_video_url": None,
            "total_prompts": len(prompts),
            "completed_prompts": 0,
            "failed_prompts": 0,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "completed_at": None,
            "error_logs": []
        }
        logger.debug("Creating video job doc job_id=%s total_prompts=%d", job_id, len(prompts))
        self.db.collection('video_jobs').document(job_id).set(job_doc)
        # Create message docs for each prompt (simplified placeholder)
        batch = self.db.batch()
        for idx, p in enumerate(prompts):
            mid = f"msg_{uuid.uuid4().hex[:12]}"
            batch.set(self.db.collection('messages').document(mid), {
                "message_id": mid,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "user_email": user_email,
                "role": "user",
                "content": p,
                "content_type": "video_prompt",
                "sequence_number": 0,  # not sequencing precisely for MVP
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "is_deleted": False,
                "is_edited": False,
                "job_id": job_id,
                "video_metadata": {
                    "prompt_index": idx,
                    "prompt_text": p,
                    "status": "queued",
                    "video_url": None,
                    "thumbnail_url": None,
                    "error_message": None,
                    "veo_job_id": None,
                }
            })
        batch.commit()
        logger.debug("Created %d prompt message docs for job_id=%s", len(prompts), job_id)
        realtime_event_bus.publish(job_id, 'batch.started', {"job_id": job_id, "total": len(prompts)})
        # Background processing thread (sequential for now)
        thread = threading.Thread(target=self._process_job_thread, args=(job_id, prompts, options), daemon=True)
        thread.start()
        logger.debug("Background processing thread started job_id=%s", job_id)
        return {"success": True, "job_id": job_id, "total_prompts": len(prompts), "status": "pending"}

    # ---------------- Internal processing -----------------
    def _process_job_thread(self, job_id: str, prompts: List[str], options: Dict[str, Any]):
        job_ref = self.db.collection('video_jobs').document(job_id)
        try:
            # Mark job processing
            job_ref.update({"status": "processing", "updated_at": firestore.SERVER_TIMESTAMP})
            logger.debug("Job status set to processing job_id=%s", job_id)
        except Exception:
            pass
        for idx, prompt in enumerate(prompts):
            logger.debug("Starting prompt generation job_id=%s prompt_index=%d", job_id, idx)
            self._update_prompt_status(job_id, idx, "generating")
            realtime_event_bus.publish(job_id, 'video.started', {"job_id": job_id, "prompt_index": idx})
            try:
                # Use underlying synchronous Veo service (simpler than async wrapper for MVP)
                result = self.generation.veo.generate_video(
                    prompt=prompt,
                    model=options.get('model'),
                    aspect_ratio=options.get('aspect_ratio') or options.get('aspectRatio'),
                    duration_seconds=options.get('duration_seconds') or options.get('durationSeconds'),
                    seed=options.get('seed'),
                    sample_count=options.get('sample_count') or options.get('sampleCount', 1),
                    negative_prompt=options.get('negative_prompt') or options.get('negativePrompt'),
                    enhance_prompt=options.get('enhance_prompt', True),
                    person_generation=options.get('person_generation') or options.get('personGeneration'),
                    resolution=options.get('resolution'),
                    generate_audio=options.get('generate_audio') or options.get('generateAudio'),
                    storage_uri=options.get('storage_uri') or options.get('storageUri'),
                )
                if result.get('success'):
                    logger.debug("Prompt success job_id=%s prompt_index=%d", job_id, idx)
                    video_url = (result.get('gcs_uris') or [result.get('video_path')])[0]
                    self._update_prompt_status(job_id, idx, 'completed', {
                        'video_url': video_url,
                        'veo_job_id': result.get('job_id'),
                    })
                    self._increment_job(job_id, success=True, video_url=video_url)
                    realtime_event_bus.publish(job_id, 'video.completed', {"job_id": job_id, "prompt_index": idx, "video_url": video_url})
                else:
                    logger.debug("Prompt failed job_id=%s prompt_index=%d error=%s", job_id, idx, result.get('error'))
                    self._update_prompt_status(job_id, idx, 'failed', {"error_message": result.get('error')})
                    self._increment_job(job_id, success=False, error=result.get('error'), idx=idx)
                    realtime_event_bus.publish(job_id, 'video.failed', {"job_id": job_id, "prompt_index": idx, "error": result.get('error')})
            except Exception as e:  # noqa
                logger.exception("Prompt generation failed")
                self._update_prompt_status(job_id, idx, 'failed', {"error_message": str(e)})
                self._increment_job(job_id, success=False, error=str(e), idx=idx)
                realtime_event_bus.publish(job_id, 'video.failed', {"job_id": job_id, "prompt_index": idx, "error": str(e)})
        # Finalize
        logger.debug("All prompts processed; finalizing job_id=%s", job_id)
        self._finalize_job(job_id)

    def _update_prompt_status(self, job_id: str, prompt_index: int, status: str, extra: Optional[Dict[str, Any]] = None):
        extra = extra or {}
        # Query message by job_id + video_metadata.prompt_index
        try:
            msgs = self.db.collection('messages').where('job_id', '==', job_id).where('video_metadata.prompt_index', '==', prompt_index).limit(1).stream()
            for doc in msgs:
                update_fields = {"video_metadata.status": status}
                for k, v in extra.items():
                    update_fields[f"video_metadata.{k}"] = v
                update_fields['updated_at'] = firestore.SERVER_TIMESTAMP
                doc.reference.update(update_fields)
        except Exception:
            logger.debug("Failed updating prompt status", exc_info=True)

    def _increment_job(self, job_id: str, success: bool, video_url: Optional[str] = None, error: Optional[str] = None, idx: Optional[int] = None):
        job_ref = self.db.collection('video_jobs').document(job_id)
        def _tx(transaction):
            snap = job_ref.get(transaction=transaction)
            if not snap.exists:
                return
            data = snap.to_dict() or {}
            completed = data.get('completed_prompts', 0)
            failed = data.get('failed_prompts', 0)
            video_urls = data.get('video_urls', [])
            if success:
                completed += 1
                if video_url:
                    video_urls.append(video_url)
            else:
                failed += 1
                errors = data.get('error_logs', [])
                errors.append({"prompt_index": idx, "error": error, "ts": time.time()})
                transaction.update(job_ref, {
                    'failed_prompts': failed,
                    'error_logs': errors,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                return
            transaction.update(job_ref, {
                'completed_prompts': completed,
                'video_urls': video_urls,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
        self.db.transaction().call(_tx)

    def _finalize_job(self, job_id: str):
        job_ref = self.db.collection('video_jobs').document(job_id)
        snap = job_ref.get()
        if not snap.exists:
            return
        data = snap.to_dict() or {}
        total = data.get('total_prompts', 0)
        completed = data.get('completed_prompts', 0)
        failed = data.get('failed_prompts', 0)
        if completed == total:
            status = 'completed'
        elif failed == total:
            status = 'failed'
        elif failed > 0:
            status = 'partial'
        else:
            status = 'processing'
        logger.debug("Finalize job job_id=%s status=%s completed=%d failed=%d total=%d", job_id, status, completed, failed, total)
        job_ref.update({'status': status, 'completed_at': firestore.SERVER_TIMESTAMP, 'updated_at': firestore.SERVER_TIMESTAMP})
        realtime_event_bus.publish(job_id, 'batch.completed', {
            'job_id': job_id,
            'status': status,
            'completed': completed,
            'failed': failed,
            'total': total
        })

    # ---------------- Public helpers -----------------
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        snap = self.db.collection('video_jobs').document(job_id).get()
        return snap.to_dict() if snap.exists else None

    def list_prompt_statuses(self, job_id: str) -> List[Dict[str, Any]]:
        out = []
        try:
            msgs = self.db.collection('messages').where('job_id', '==', job_id).stream()
            for m in msgs:
                d = m.to_dict() or {}
                vm = d.get('video_metadata') or {}
                out.append({
                    'prompt_index': vm.get('prompt_index'),
                    'status': vm.get('status'),
                    'video_url': vm.get('video_url'),
                    'error_message': vm.get('error_message')
                })
            out.sort(key=lambda x: x.get('prompt_index') or 0)
        except Exception:
            logger.debug("Failed listing prompt statuses", exc_info=True)
        return out

    def combine_videos(self, job_id: str) -> Dict[str, Any]:
        job = self.get_job(job_id)
        if not job:
            return {"success": False, "error": "job not found"}
        videos = job.get('video_urls') or []
        if not videos:
            return {"success": False, "error": "no completed videos"}
        # For MVP just echo list (real concatenation would download and invoke processing service)
        # Could call: await processing.concatenate(...). Keeping sync stub for now.
        try:
            job_ref = self.db.collection('video_jobs').document(job_id)
            final_url = videos[0]  # placeholder: first video
            job_ref.update({'final_video_url': final_url, 'updated_at': firestore.SERVER_TIMESTAMP})
            realtime_event_bus.publish(job_id, 'sequence.completed', {'job_id': job_id, 'final_video_url': final_url})
            return {"success": True, "final_video_url": final_url}
        except Exception as e:  # noqa
            return {"success": False, "error": str(e)}

# Singleton orchestrator
video_batch_orchestrator = VideoBatchOrchestrator()
