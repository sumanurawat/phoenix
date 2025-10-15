"""
Reel Project Service - Firestore CRUD operations for reel maker projects.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from firebase_admin import firestore
from google.api_core import exceptions as google_exceptions
from google.cloud.firestore_v1 import FieldFilter
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Collection name
COLLECTION_NAME = "reel_maker_projects"

@dataclass
class ReelProject:
    """Reel project data model matching Firestore schema."""
    project_id: str
    user_id: str
    user_email: str
    title: str
    orientation: str = "portrait"  # "portrait" | "landscape"  
    duration_seconds: int = 8
    compression: str = "optimized"
    model: str = "veo-3.1-fast-generate-preview"
    audio_enabled: bool = True
    prompt_list: List[str] = None
    clip_filenames: List[str] = None
    stitched_filename: Optional[str] = None
    status: str = "draft"  # "draft" | "generating" | "error" | "ready"
    error_info: Optional[Dict[str, str]] = None
    created_at: Any = None
    updated_at: Any = None
    
    def __post_init__(self):
        if self.prompt_list is None:
            self.prompt_list = []
        if self.clip_filenames is None:
            self.clip_filenames = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore-compatible dict."""
        data = {
            'userId': self.user_id,
            'userEmail': self.user_email,
            'title': self.title,
            'orientation': self.orientation,
            'durationSeconds': self.duration_seconds,
            'compression': self.compression,
            'model': self.model,
            'audioEnabled': self.audio_enabled,
            'promptList': self.prompt_list,
            'clipFilenames': self.clip_filenames,
            'status': self.status,
        }
        
        # Add optional fields if present
        if self.stitched_filename:
            data['stitchedFilename'] = self.stitched_filename
        if self.error_info:
            data['errorInfo'] = self.error_info
            
        return data

    @classmethod
    def from_firestore_doc(cls, doc) -> 'ReelProject':
        """Create ReelProject from Firestore document."""
        data = doc.to_dict()
        return cls(
            project_id=doc.id,
            user_id=data.get('userId', ''),
            user_email=data.get('userEmail', ''),
            title=data.get('title', ''),
            orientation=data.get('orientation', 'portrait'),
            duration_seconds=data.get('durationSeconds', 8),
            compression=data.get('compression', 'optimized'),
            model=data.get('model', 'veo-3.1-fast-generate-preview'),
            audio_enabled=data.get('audioEnabled', True),
            prompt_list=data.get('promptList', []),
            clip_filenames=data.get('clipFilenames', []),
            stitched_filename=data.get('stitchedFilename'),
            status=data.get('status', 'draft'),
            error_info=data.get('errorInfo'),
            created_at=data.get('createdAt'),
            updated_at=data.get('updatedAt'),
        )


class ReelProjectService:
    """Service for managing reel maker projects in Firestore."""
    
    def __init__(self):
        self.db = firestore.client()
        self.collection = self.db.collection(COLLECTION_NAME)
    
    def create_project(self, user_id: str, user_email: str, title: str) -> ReelProject:
        """Create a new reel project with defaults."""
        if not title or not title.strip():
            raise ValueError("Project title is required")
        
        project = ReelProject(
            project_id="",  # Will be set by Firestore
            user_id=user_id,
            user_email=user_email,
            title=title.strip()
        )
        
        # Add timestamps
        doc_data = project.to_dict()
        doc_data['createdAt'] = firestore.SERVER_TIMESTAMP
        doc_data['updatedAt'] = firestore.SERVER_TIMESTAMP
        
        # Create document
        doc_ref = self.collection.add(doc_data)[1]
        project.project_id = doc_ref.id
        now = datetime.now(timezone.utc)
        project.created_at = now
        project.updated_at = now
        
        logger.info(f"Created reel project {doc_ref.id} for user {user_id}")
        return project
    
    def get_user_projects(self, user_id: str, limit: int = 50) -> List[ReelProject]:
        """Get all projects for a user, ordered by updatedAt desc."""
        try:
            query = (
                self.collection
                .where(filter=FieldFilter('userId', '==', user_id))
                .order_by('updatedAt', direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            docs = query.stream()
            projects = [ReelProject.from_firestore_doc(doc) for doc in docs]

            logger.info(f"Retrieved {len(projects)} projects for user {user_id}")
            return projects

        except google_exceptions.FailedPrecondition as e:
            if "index" not in str(e).lower():
                logger.error(f"Failed to get projects for user {user_id}: {e}")
                raise

            logger.warning(
                "Missing composite index for userId+updatedAt. Falling back to client-side sort."
            )
            fallback_query = (
                self.collection
                .where(filter=FieldFilter('userId', '==', user_id))
                .limit(limit * 2 if limit else 50)
            )

            docs = fallback_query.stream()
            projects = [ReelProject.from_firestore_doc(doc) for doc in docs]

            def _timestamp_value(project: ReelProject):
                value = project.updated_at or project.created_at
                if isinstance(value, datetime):
                    return value
                to_datetime = getattr(value, "to_datetime", None)
                if callable(to_datetime):
                    try:
                        return to_datetime()
                    except Exception:  # pragma: no cover - best effort conversion
                        return datetime.min.replace(tzinfo=timezone.utc)
                return datetime.min.replace(tzinfo=timezone.utc)

            projects.sort(key=_timestamp_value, reverse=True)
            if limit:
                projects = projects[:limit]

            return projects

        except Exception as e:
            logger.error(f"Failed to get projects for user {user_id}: {e}")
            raise
    
    def get_project(self, project_id: str, user_id: str) -> Optional[ReelProject]:
        """Get a specific project, ensuring ownership."""
        try:
            doc = self.collection.document(project_id).get()
            
            if not doc.exists:
                return None
            
            project = ReelProject.from_firestore_doc(doc)
            
            # Enforce ownership
            if project.user_id != user_id:
                logger.warning(f"User {user_id} attempted to access project {project_id} owned by {project.user_id}")
                return None
            
            return project
        
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            raise
    
    def update_project(self, project_id: str, user_id: str, **updates) -> bool:
        """Update project fields, ensuring ownership."""
        try:
            doc_ref = self.collection.document(project_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            project = ReelProject.from_firestore_doc(doc)
            
            # Enforce ownership
            if project.user_id != user_id:
                logger.warning(f"User {user_id} attempted to update project {project_id} owned by {project.user_id}")
                return False
            
            # Build update data
            update_data = {}
            allowed_fields = {
                'title', 'orientation', 'audio_enabled', 'prompt_list', 
                'clip_filenames', 'stitched_filename', 'status', 'error_info'
            }
            
            for field, value in updates.items():
                if field in allowed_fields:
                    # Convert snake_case to camelCase for Firestore
                    firestore_field = {
                        'audio_enabled': 'audioEnabled',
                        'prompt_list': 'promptList', 
                        'clip_filenames': 'clipFilenames',
                        'stitched_filename': 'stitchedFilename',
                        'error_info': 'errorInfo'
                    }.get(field, field)
                    
                    update_data[firestore_field] = value
            
            if update_data:
                update_data['updatedAt'] = firestore.SERVER_TIMESTAMP
                doc_ref.update(update_data)
                logger.info(f"Updated project {project_id} fields: {list(update_data.keys())}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            raise
    
    def update_project_status(self, project_id: str, user_id: str, status: str) -> bool:
        """Convenience method to update project status."""
        return self.update_project(project_id, user_id, status=status)
    
    def update_project_stitched_file(self, project_id: str, user_id: str, stitched_filename: str) -> bool:
        """Convenience method to update stitched filename."""
        return self.update_project(project_id, user_id, stitched_filename=stitched_filename)
    
    def delete_project(self, project_id: str, user_id: str) -> bool:
        """Delete a project, ensuring ownership."""
        try:
            doc_ref = self.collection.document(project_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            project = ReelProject.from_firestore_doc(doc)
            
            # Enforce ownership
            if project.user_id != user_id:
                logger.warning(f"User {user_id} attempted to delete project {project_id} owned by {project.user_id}")
                return False
            
            # For now, hard delete. TODO: Consider soft delete with status="archived"
            doc_ref.delete()
            logger.info(f"Deleted project {project_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            raise
    
    def get_completion_status(self, project: ReelProject, verify_gcs: bool = False) -> Dict[str, Any]:
        """
        Calculate project completion status.
        
        Args:
            project: ReelProject instance
            verify_gcs: If True, verify each clip exists in GCS (slower but accurate)
        
        Returns:
            Dict with:
                - total_clips: Total number of prompts
                - existing_clips: Number of clips with filenames
                - missing_clips: Number of clips that need generation
                - completion_percentage: 0-100
                - is_complete: True if all clips exist
                - status_label: "Ready" | "Incomplete" | "Not Started"
        """
        try:
            total_clips = len(project.prompt_list or [])
            
            if total_clips == 0:
                return {
                    'total_clips': 0,
                    'existing_clips': 0,
                    'missing_clips': 0,
                    'completion_percentage': 0,
                    'is_complete': False,
                    'status_label': 'Not Started'
                }
            
            clip_filenames = project.clip_filenames or []
            
            # Count existing clips (non-None, non-empty strings)
            if verify_gcs and hasattr(self, 'storage_service'):
                # Verify clips exist in GCS (requires storage service)
                from services.reel_storage_service import reel_storage_service
                existing_count = 0
                for clip_path in clip_filenames:
                    if clip_path:
                        try:
                            blob = reel_storage_service._ensure_bucket().blob(clip_path)
                            if blob.exists():
                                existing_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to verify clip in GCS: {clip_path} - {e}")
                            continue
            else:
                # Quick check: count non-empty clip paths
                existing_count = sum(1 for clip in clip_filenames if clip)
            
            missing_count = total_clips - existing_count
            completion_percentage = int((existing_count / total_clips) * 100)
            is_complete = existing_count == total_clips
            
            # Determine status label
            if is_complete:
                status_label = "Ready"
            elif existing_count > 0:
                status_label = f"Incomplete ({existing_count}/{total_clips})"
            else:
                status_label = "Not Started"
            
            return {
                'total_clips': total_clips,
                'existing_clips': existing_count,
                'missing_clips': missing_count,
                'completion_percentage': completion_percentage,
                'is_complete': is_complete,
                'status_label': status_label
            }
        
        except Exception as e:
            logger.error(f"Failed to calculate completion status: {e}")
            return {
                'total_clips': 0,
                'existing_clips': 0,
                'missing_clips': 0,
                'completion_percentage': 0,
                'is_complete': False,
                'status_label': 'Error'
            }

# Singleton instance
reel_project_service = ReelProjectService()

# Singleton instance
reel_project_service = ReelProjectService()