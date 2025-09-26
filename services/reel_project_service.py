"""Reel Project Service for managing video project CRUD operations"""
from __future__ import annotations
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from firebase_admin import firestore

from services.veo_video_generation_service import VeoGenerationParams, veo_video_service
from services.realtime_event_bus import realtime_event_bus
from services.gcs_media_service import GCSMediaService
from services.video_stitching_service import VideoStitchingService

logger = logging.getLogger(__name__)

class ReelProjectService:
    """Service for managing reel maker projects and operations"""
    
    def __init__(self):
        self.db = firestore.client()
        self.collection = 'reel_maker_projects'
        self.gcs_service = GCSMediaService()
        self.stitching_service = VideoStitchingService()
        
    def list_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """List all projects for a user, ordered by updatedAt desc"""
        try:
            query = (self.db.collection(self.collection)
                    .where('userId', '==', user_id)
                    .where('status', '!=', 'archived')
                    .order_by('updatedAt', direction=firestore.Query.DESCENDING))
            
            projects = []
            for doc in query.stream():
                project_data = doc.to_dict()
                project_data['projectId'] = doc.id
                
                # Convert timestamps to ISO strings for JSON serialization
                if 'createdAt' in project_data and project_data['createdAt']:
                    project_data['createdAt'] = project_data['createdAt'].isoformat()
                if 'updatedAt' in project_data and project_data['updatedAt']:
                    project_data['updatedAt'] = project_data['updatedAt'].isoformat()
                    
                projects.append(project_data)
                
            return projects
        except Exception as e:
            logger.error(f"Error listing user projects: {e}")
            raise
            
    def create_project(self, user_id: str, user_email: str, title: str) -> Dict[str, Any]:
        """Create a new reel project with default settings"""
        try:
            project_data = {
                'userId': user_id,
                'userEmail': user_email,
                'title': title,
                'orientation': 'portrait',
                'durationSeconds': 8,
                'compression': 'optimized',
                'model': 'veo-3.0-fast-generate-001',
                'audioEnabled': True,
                'promptList': [],
                'clipFilenames': [],
                'stitchedFilename': None,
                'status': 'draft',
                'errorInfo': None,
                'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref = self.db.collection(self.collection).add(project_data)
            project_id = doc_ref[1].id
            
            # Get the created project with timestamps
            created_project = self.get_project(project_id, user_id)
            return created_project
            
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            raise
            
    def get_project(self, project_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get project details with ownership verification"""
        try:
            doc_ref = self.db.collection(self.collection).document(project_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
                
            project_data = doc.to_dict()
            
            # Verify ownership
            if project_data.get('userId') != user_id:
                return None
                
            project_data['projectId'] = doc.id
            
            # Convert timestamps
            if 'createdAt' in project_data and project_data['createdAt']:
                project_data['createdAt'] = project_data['createdAt'].isoformat()
            if 'updatedAt' in project_data and project_data['updatedAt']:
                project_data['updatedAt'] = project_data['updatedAt'].isoformat()
                
            # Add computed asset URLs if clips exist
            if project_data.get('clipFilenames'):
                project_data['clipUrls'] = self.gcs_service.get_clip_urls(
                    user_id, project_id, project_data['clipFilenames']
                )
                
            if project_data.get('stitchedFilename'):
                project_data['stitchedUrl'] = self.gcs_service.get_stitched_url(
                    user_id, project_id, project_data['stitchedFilename']
                )
                
            return project_data
            
        except Exception as e:
            logger.error(f"Error getting project: {e}")
            raise
            
    def update_project(self, project_id: str, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update project with ownership verification"""
        try:
            doc_ref = self.db.collection(self.collection).document(project_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
                
            project_data = doc.to_dict()
            if project_data.get('userId') != user_id:
                return None
                
            # Add updatedAt timestamp
            updates['updatedAt'] = firestore.SERVER_TIMESTAMP
            
            doc_ref.update(updates)
            
            # Return updated project
            return self.get_project(project_id, user_id)
            
        except Exception as e:
            logger.error(f"Error updating project: {e}")
            raise
            
    def delete_project(self, project_id: str, user_id: str) -> bool:
        """Soft delete project by marking as archived"""
        try:
            doc_ref = self.db.collection(self.collection).document(project_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
                
            project_data = doc.to_dict()
            if project_data.get('userId') != user_id:
                return False
                
            # Mark as archived
            doc_ref.update({
                'status': 'archived',
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting project: {e}")
            raise
            
    def start_generation(self, project_id: str, user_id: str, prompts: List[str]) -> Dict[str, Any]:
        """Start video generation for project prompts"""
        try:
            # Verify project ownership
            project = self.get_project(project_id, user_id)
            if not project:
                return {"success": False, "error": "Project not found"}
                
            # Update project with new prompts and status
            self.update_project(project_id, user_id, {
                'promptList': prompts,
                'status': 'generating',
                'clipFilenames': [],  # Clear previous clips
                'stitchedFilename': None,
                'errorInfo': None
            })
            
            # Start generation in background thread
            job_id = f"reel_{project_id}_{int(datetime.now().timestamp())}"
            thread = threading.Thread(
                target=self._run_generation,
                args=(job_id, project_id, user_id, prompts, project)
            )
            thread.start()
            
            return {
                "success": True,
                "job_id": job_id,
                "message": f"Started generation for {len(prompts)} prompts"
            }
            
        except Exception as e:
            logger.error(f"Error starting generation: {e}")
            raise
            
    def _run_generation(self, job_id: str, project_id: str, user_id: str, prompts: List[str], project: Dict[str, Any]):
        """Background thread for video generation"""
        topic = f"reel_{project_id}"
        clip_filenames = []
        
        try:
            # Get storage URI for this project
            storage_uri = self.gcs_service.get_project_storage_uri(user_id, project_id)
            
            for idx, prompt in enumerate(prompts):
                realtime_event_bus.publish(topic, 'generation.started', {
                    "prompt_index": idx,
                    "prompt": prompt
                })
                
                try:
                    # Build generation parameters with project defaults
                    params = VeoGenerationParams(
                        model=project.get('model', 'veo-3.0-fast-generate-001'),
                        prompt=prompt,
                        aspect_ratio='9:16' if project.get('orientation') == 'portrait' else '16:9',
                        duration_seconds=project.get('durationSeconds', 8),
                        sample_count=1,
                        generate_audio=project.get('audioEnabled', True),
                        enhance_prompt=True,
                        compression_quality=project.get('compression', 'optimized'),
                        storage_uri=storage_uri
                    )
                    
                    # Generate video
                    result = veo_video_service.generate_video(params)
                    
                    if result.success and result.gcs_uris:
                        # Extract filename from GCS URI
                        filename = result.gcs_uris[0].split('/')[-1]
                        clip_filenames.append(filename)
                        
                        realtime_event_bus.publish(topic, 'generation.completed', {
                            "prompt_index": idx,
                            "filename": filename,
                            "gcs_uri": result.gcs_uris[0]
                        })
                    else:
                        realtime_event_bus.publish(topic, 'generation.failed', {
                            "prompt_index": idx,
                            "error": result.error or "Unknown error"
                        })
                        
                except Exception as e:
                    logger.error(f"Error generating video for prompt {idx}: {e}")
                    realtime_event_bus.publish(topic, 'generation.failed', {
                        "prompt_index": idx,
                        "error": str(e)
                    })
                    
            # Update project with results
            if clip_filenames:
                self.update_project(project_id, user_id, {
                    'clipFilenames': clip_filenames,
                    'status': 'ready'
                })
                
                realtime_event_bus.publish(topic, 'generation.job_completed', {
                    "clip_count": len(clip_filenames),
                    "total_prompts": len(prompts)
                })
            else:
                self.update_project(project_id, user_id, {
                    'status': 'error',
                    'errorInfo': {
                        'code': 'GENERATION_FAILED',
                        'message': 'No clips were generated successfully'
                    }
                })
                
        except Exception as e:
            logger.error(f"Error in generation job {job_id}: {e}")
            self.update_project(project_id, user_id, {
                'status': 'error',
                'errorInfo': {
                    'code': 'GENERATION_ERROR',
                    'message': str(e)
                }
            })
            
    def start_stitching(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """Start video stitching job for project clips"""
        try:
            # Verify project and check clips
            project = self.get_project(project_id, user_id)
            if not project:
                return {"success": False, "error": "Project not found"}
                
            clip_filenames = project.get('clipFilenames', [])
            if len(clip_filenames) < 2:
                return {
                    "success": False, 
                    "error": "At least 2 clips required for stitching"
                }
                
            # Start stitching in background
            job_id = f"stitch_{project_id}_{int(datetime.now().timestamp())}"
            thread = threading.Thread(
                target=self._run_stitching,
                args=(job_id, project_id, user_id, project)
            )
            thread.start()
            
            return {
                "success": True,
                "job_id": job_id,
                "message": f"Started stitching {len(clip_filenames)} clips"
            }
            
        except Exception as e:
            logger.error(f"Error starting stitching: {e}")
            raise
            
    def _run_stitching(self, job_id: str, project_id: str, user_id: str, project: Dict[str, Any]):
        """Background thread for video stitching"""
        topic = f"reel_{project_id}"
        
        try:
            realtime_event_bus.publish(topic, 'stitching.started', {
                "clip_count": len(project['clipFilenames'])
            })
            
            # Run stitching service
            result = self.stitching_service.stitch_videos(
                user_id=user_id,
                project_id=project_id,
                clip_filenames=project['clipFilenames'],
                project_config=project
            )
            
            if result['success']:
                # Update project with stitched file
                self.update_project(project_id, user_id, {
                    'stitchedFilename': result['filename'],
                    'status': 'ready'
                })
                
                realtime_event_bus.publish(topic, 'stitching.completed', {
                    "filename": result['filename'],
                    "duration": result.get('duration')
                })
            else:
                self.update_project(project_id, user_id, {
                    'status': 'error',
                    'errorInfo': {
                        'code': 'STITCHING_FAILED',
                        'message': result['error']
                    }
                })
                
                realtime_event_bus.publish(topic, 'stitching.failed', {
                    "error": result['error']
                })
                
        except Exception as e:
            logger.error(f"Error in stitching job {job_id}: {e}")
            self.update_project(project_id, user_id, {
                'status': 'error',
                'errorInfo': {
                    'code': 'STITCHING_ERROR',
                    'message': str(e)
                }
            })
            
    def get_clip_stream(self, project_id: str, user_id: str, filename: str):
        """Get clip streaming response after ownership verification"""
        try:
            # Verify project ownership and clip exists
            project = self.get_project(project_id, user_id)
            if not project:
                return None
                
            clip_filenames = project.get('clipFilenames', [])
            if filename not in clip_filenames:
                return None
                
            # Use GCS service to stream the file
            return self.gcs_service.stream_clip(user_id, project_id, filename)
            
        except Exception as e:
            logger.error(f"Error getting clip stream: {e}")
            return None