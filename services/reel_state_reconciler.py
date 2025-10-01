"""
Reel State Reconciliation Service
Ensures project state matches actual GCS assets, preventing stuck states.
"""
import logging
from typing import Optional, Dict, Any, List
from services.reel_project_service import reel_project_service, ReelProject
from services.reel_storage_service import reel_storage_service

logger = logging.getLogger(__name__)


class ReelStateReconciler:
    """
    Verifies project state against actual GCS assets and corrects inconsistencies.
    Prevents projects from getting stuck in 'generating' when clips already exist.
    """
    
    def __init__(self, project_service=None, storage=None):
        self.project_service = project_service or reel_project_service
        self.storage = storage or reel_storage_service
    
    def reconcile_project(self, project_id: str, user_id: str, auto_fix: bool = True) -> Dict[str, Any]:
        """
        Verify project state against actual GCS assets.
        
        Args:
            project_id: Project to reconcile
            user_id: Owner user ID
            auto_fix: If True, automatically correct state in Firestore
        
        Returns:
            Reconciliation report with:
            - originalStatus: Status before reconciliation
            - correctedStatus: Status after reconciliation  
            - verifiedClips: Number of clips that exist in GCS
            - missingClips: List of claimed clips not found in GCS
            - action: 'no_change' | 'corrected' | 'error'
        """
        try:
            project = self.project_service.get_project(project_id, user_id)
            if not project:
                return {
                    "error": "Project not found",
                    "projectId": project_id,
                    "action": "error"
                }
            
            report = {
                "projectId": project_id,
                "originalStatus": project.status,
                "claimedClips": len(project.clip_filenames or []),
                "verifiedClips": 0,
                "missingClips": [],
                "correctedStatus": project.status,
                "action": "no_change"
            }
            
            # Verify each claimed clip actually exists in GCS
            verified_clips: List[Optional[str]] = []
            missing_clips: List[str] = []
            
            claimed_clips = project.clip_filenames or []
            prompt_count = len(project.prompt_list or [])
            
            # Build verified clip array matching prompt count
            for idx in range(prompt_count):
                if idx < len(claimed_clips) and claimed_clips[idx]:
                    clip_path = claimed_clips[idx]
                    if self._verify_clip_exists(clip_path):
                        verified_clips.append(clip_path)
                        logger.debug(f"Verified clip {idx}: {clip_path}")
                    else:
                        verified_clips.append(None)
                        missing_clips.append(clip_path)
                        logger.warning(f"Project {project_id} claims clip {clip_path} but it doesn't exist in GCS")
                else:
                    verified_clips.append(None)
            
            verified_count = sum(1 for clip in verified_clips if clip)
            report["verifiedClips"] = verified_count
            report["missingClips"] = missing_clips
            
            # Determine correct status based on verified clips
            new_status = self._determine_status(project, verified_count, prompt_count)
            report["correctedStatus"] = new_status
            
            # Apply corrections if needed
            needs_update = (
                new_status != project.status or 
                verified_count != len(claimed_clips) or
                len(missing_clips) > 0
            )
            
            if needs_update and auto_fix:
                logger.info(
                    f"Reconciling project {project_id}: "
                    f"status {project.status} -> {new_status}, "
                    f"clips {len(claimed_clips)} -> {verified_count}/{prompt_count}"
                )
                
                # Update project with verified clips only
                self.project_service.update_project(
                    project_id,
                    user_id,
                    clip_filenames=verified_clips,
                    status=new_status,
                    error_info=None if new_status != "error" else project.error_info
                )
                report["action"] = "corrected"
            
            return report
        
        except Exception as e:
            logger.error(f"Failed to reconcile project {project_id}: {e}")
            return {
                "error": str(e),
                "projectId": project_id,
                "action": "error"
            }
    
    def _verify_clip_exists(self, clip_path: str) -> bool:
        """Check if clip actually exists in GCS."""
        if not clip_path:
            return False
        
        try:
            bucket = self.storage._ensure_bucket()
            blob = bucket.blob(clip_path)
            exists = blob.exists()
            return exists
        except Exception as e:
            logger.error(f"Failed to verify clip {clip_path}: {e}")
            return False
    
    def _determine_status(self, project: ReelProject, verified_count: int, prompt_count: int) -> str:
        """
        Determine correct status based on verified clips vs prompts.
        
        Rules:
        - No prompts → draft
        - All prompts have verified clips → ready
        - Some clips verified, not generating → draft (need regeneration)
        - Some clips verified, currently generating → generating (in progress)
        - No clips, was generating → error (generation failed)
        - No clips, not generating → draft
        """
        # No prompts defined yet
        if prompt_count == 0:
            return "draft"
        
        # All clips exist - project is complete
        if verified_count > 0 and verified_count == prompt_count:
            return "ready"
        
        # Partial clips
        if 0 < verified_count < prompt_count:
            # Keep generating status if currently in progress
            if project.status == "generating":
                return "generating"
            # Otherwise needs regeneration
            return "draft"
        
        # No clips at all
        if verified_count == 0:
            # Was generating but has no clips - likely failed
            if project.status == "generating":
                return "error"
            # Not generating, just empty
            return "draft"
        
        # Default: keep current status
        return project.status


# Singleton instance
reel_state_reconciler = ReelStateReconciler()
