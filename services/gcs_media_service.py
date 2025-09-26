"""GCS Media Service for managing video asset storage in Google Cloud Storage"""
from __future__ import annotations
import logging
import os
import tempfile
from typing import List, Optional, Dict, Any
from flask import Response, send_file

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None

logger = logging.getLogger(__name__)

class GCSMediaService:
    """Service for managing video assets in Google Cloud Storage"""
    
    def __init__(self):
        self.bucket_name = os.getenv('GCS_BUCKET_NAME', 'phoenix-video-assets')
        self.base_path = 'reel-maker'
        
        if GCS_AVAILABLE:
            try:
                self.client = storage.Client()
                self.bucket = self.client.bucket(self.bucket_name)
            except Exception as e:
                logger.warning(f"GCS client initialization failed: {e}")
                self.client = None
                self.bucket = None
        else:
            logger.warning("Google Cloud Storage not available - using local fallback")
            self.client = None
            self.bucket = None
            
    def get_project_storage_uri(self, user_id: str, project_id: str) -> str:
        """Get GCS storage URI for a project's raw videos"""
        return f"gs://{self.bucket_name}/{self.base_path}/{user_id}/{project_id}/raw/"
        
    def get_stitched_storage_uri(self, user_id: str, project_id: str) -> str:
        """Get GCS storage URI for a project's stitched video"""
        return f"gs://{self.bucket_name}/{self.base_path}/{user_id}/{project_id}/stitched/"
        
    def get_clip_urls(self, user_id: str, project_id: str, filenames: List[str]) -> List[str]:
        """Get accessible URLs for clip files"""
        if not self.client or not filenames:
            return []
            
        urls = []
        for filename in filenames:
            try:
                blob_path = f"{self.base_path}/{user_id}/{project_id}/raw/{filename}"
                blob = self.bucket.blob(blob_path)
                
                if blob.exists():
                    # Generate signed URL valid for 1 hour
                    signed_url = blob.generate_signed_url(
                        expiration=3600,  # 1 hour
                        method='GET'
                    )
                    urls.append(signed_url)
                else:
                    logger.warning(f"Clip file not found: {blob_path}")
                    
            except Exception as e:
                logger.error(f"Error generating signed URL for {filename}: {e}")
                
        return urls
        
    def get_stitched_url(self, user_id: str, project_id: str, filename: str) -> Optional[str]:
        """Get accessible URL for stitched video file"""
        if not self.client or not filename:
            return None
            
        try:
            blob_path = f"{self.base_path}/{user_id}/{project_id}/stitched/{filename}"
            blob = self.bucket.blob(blob_path)
            
            if blob.exists():
                # Generate signed URL valid for 1 hour
                signed_url = blob.generate_signed_url(
                    expiration=3600,  # 1 hour
                    method='GET'
                )
                return signed_url
            else:
                logger.warning(f"Stitched file not found: {blob_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating signed URL for stitched file {filename}: {e}")
            return None
            
    def stream_clip(self, user_id: str, project_id: str, filename: str) -> Optional[Response]:
        """Stream a clip file through Flask after downloading from GCS"""
        if not self.client:
            logger.error("GCS client not available for streaming")
            return None
            
        try:
            blob_path = f"{self.base_path}/{user_id}/{project_id}/raw/{filename}"
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                logger.warning(f"Clip file not found for streaming: {blob_path}")
                return None
                
            # Download to temporary file and stream
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                blob.download_to_filename(temp_file.name)
                
                # Stream the file
                return send_file(
                    temp_file.name,
                    mimetype='video/mp4',
                    as_attachment=False,
                    download_name=filename
                )
                
        except Exception as e:
            logger.error(f"Error streaming clip {filename}: {e}")
            return None
            
    def upload_stitched_video(self, user_id: str, project_id: str, local_path: str, filename: str) -> bool:
        """Upload stitched video to GCS"""
        if not self.client:
            logger.error("GCS client not available for upload")
            return False
            
        try:
            blob_path = f"{self.base_path}/{user_id}/{project_id}/stitched/{filename}"
            blob = self.bucket.blob(blob_path)
            
            # Upload file
            blob.upload_from_filename(local_path)
            
            # Set content type
            blob.content_type = 'video/mp4'
            blob.patch()
            
            logger.info(f"Successfully uploaded stitched video: {blob_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading stitched video: {e}")
            return False
            
    def download_clips_for_stitching(self, user_id: str, project_id: str, filenames: List[str], temp_dir: str) -> List[str]:
        """Download clips to temporary directory for stitching"""
        if not self.client:
            logger.error("GCS client not available for download")
            return []
            
        downloaded_paths = []
        
        for filename in filenames:
            try:
                blob_path = f"{self.base_path}/{user_id}/{project_id}/raw/{filename}"
                blob = self.bucket.blob(blob_path)
                
                if not blob.exists():
                    logger.warning(f"Clip file not found for download: {blob_path}")
                    continue
                    
                # Download to temp directory
                local_path = os.path.join(temp_dir, filename)
                blob.download_to_filename(local_path)
                downloaded_paths.append(local_path)
                
                logger.debug(f"Downloaded clip: {filename}")
                
            except Exception as e:
                logger.error(f"Error downloading clip {filename}: {e}")
                
        return downloaded_paths
        
    def cleanup_project_assets(self, user_id: str, project_id: str) -> bool:
        """Clean up all assets for a project (for hard delete)"""
        if not self.client:
            logger.warning("GCS client not available for cleanup")
            return False
            
        try:
            # Delete all blobs in the project directory
            prefix = f"{self.base_path}/{user_id}/{project_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            deleted_count = 0
            for blob in blobs:
                try:
                    blob.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting blob {blob.name}: {e}")
                    
            logger.info(f"Cleaned up {deleted_count} assets for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up project assets: {e}")
            return False
            
    def get_project_storage_info(self, user_id: str, project_id: str) -> Dict[str, Any]:
        """Get storage information for a project"""
        if not self.client:
            return {
                "raw_clips": 0,
                "stitched_videos": 0,
                "total_size_mb": 0,
                "available": False
            }
            
        try:
            raw_prefix = f"{self.base_path}/{user_id}/{project_id}/raw/"
            stitched_prefix = f"{self.base_path}/{user_id}/{project_id}/stitched/"
            
            raw_blobs = list(self.bucket.list_blobs(prefix=raw_prefix))
            stitched_blobs = list(self.bucket.list_blobs(prefix=stitched_prefix))
            
            total_size = sum(blob.size or 0 for blob in raw_blobs + stitched_blobs)
            
            return {
                "raw_clips": len(raw_blobs),
                "stitched_videos": len(stitched_blobs),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "available": True
            }
            
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                "raw_clips": 0,
                "stitched_videos": 0,
                "total_size_mb": 0,
                "available": False,
                "error": str(e)
            }