"""
Service for deleting reel maker projects and all associated resources.

This service handles complete cleanup of:
- Firestore documents (project, jobs, progress logs)
- Google Cloud Storage files (clips, stitched videos, prompts)
- Any other related data
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from google.cloud import firestore, storage
from google.api_core import exceptions as gcp_exceptions

logger = logging.getLogger(__name__)

# Initialize clients
db = firestore.Client()
storage_client = storage.Client()


class ReelDeletionService:
    """Service for deleting reel maker projects and all associated resources."""

    def __init__(self, bucket_name: str = "phoenix-videos"):
        self.bucket_name = bucket_name
        self.bucket = storage_client.bucket(bucket_name)

    def delete_project(
        self, 
        project_id: str, 
        user_id: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a reel maker project and ALL associated resources.

        Args:
            project_id: The project ID to delete
            user_id: The user ID (for authorization)
            dry_run: If True, only report what would be deleted (don't actually delete)

        Returns:
            Dictionary with deletion report:
            {
                "success": bool,
                "project_id": str,
                "deleted": {
                    "firestore_docs": int,
                    "gcs_files": int,
                    "gcs_bytes": int
                },
                "errors": List[str],
                "dry_run": bool
            }
        """
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting deletion of project {project_id} for user {user_id}")

        report = {
            "success": False,
            "project_id": project_id,
            "deleted": {
                "firestore_docs": 0,
                "gcs_files": 0,
                "gcs_bytes": 0
            },
            "errors": [],
            "dry_run": dry_run
        }

        try:
            # 1. Verify project exists and user owns it
            project_ref = db.collection('reel_projects').document(project_id)
            project_doc = project_ref.get()

            if not project_doc.exists:
                report["errors"].append(f"Project {project_id} not found")
                return report

            project_data = project_doc.to_dict()
            if project_data.get('userId') != user_id:
                report["errors"].append(f"User {user_id} does not own project {project_id}")
                return report

            logger.info(f"Project {project_id} verified - owned by user {user_id}")

            # 2. Delete GCS files (clips, stitched video, prompt files)
            gcs_result = self._delete_gcs_files(project_id, user_id, dry_run)
            report["deleted"]["gcs_files"] = gcs_result["files_deleted"]
            report["deleted"]["gcs_bytes"] = gcs_result["bytes_deleted"]
            if gcs_result["errors"]:
                report["errors"].extend(gcs_result["errors"])

            # 3. Delete Firestore documents
            firestore_result = self._delete_firestore_docs(project_id, dry_run)
            report["deleted"]["firestore_docs"] = firestore_result["docs_deleted"]
            if firestore_result["errors"]:
                report["errors"].extend(firestore_result["errors"])

            # 4. Mark as success if no critical errors
            report["success"] = len(report["errors"]) == 0

            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Deletion complete for project {project_id}: "
                f"{report['deleted']['firestore_docs']} Firestore docs, "
                f"{report['deleted']['gcs_files']} GCS files "
                f"({report['deleted']['gcs_bytes'] / (1024*1024):.2f} MB)"
            )

            return report

        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}", exc_info=True)
            report["errors"].append(f"Unexpected error: {str(e)}")
            return report

    def _delete_gcs_files(
        self, 
        project_id: str, 
        user_id: str, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Delete all GCS files associated with a project.

        Deletes:
        - reel-maker/{user_id}/{project_id}/clips/*.mp4
        - reel-maker/{user_id}/{project_id}/stitched/*.mp4
        - reel-maker/{user_id}/{project_id}/prompts.json (if exists)
        - Entire reel-maker/{user_id}/{project_id}/ folder

        Returns:
            {
                "files_deleted": int,
                "bytes_deleted": int,
                "errors": List[str]
            }
        """
        result = {
            "files_deleted": 0,
            "bytes_deleted": 0,
            "errors": []
        }

        try:
            # Delete the entire project folder
            prefix = f"reel-maker/{user_id}/{project_id}/"
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting GCS files with prefix: {prefix}")

            blobs = list(self.bucket.list_blobs(prefix=prefix))
            
            if not blobs:
                logger.info(f"No GCS files found for project {project_id}")
                return result

            for blob in blobs:
                try:
                    file_size = blob.size
                    file_name = blob.name
                    
                    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting: {file_name} ({file_size / (1024*1024):.2f} MB)")
                    
                    if not dry_run:
                        blob.delete()
                    
                    result["files_deleted"] += 1
                    result["bytes_deleted"] += file_size

                except Exception as e:
                    error_msg = f"Failed to delete GCS file {blob.name}: {str(e)}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)

            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}GCS deletion complete: "
                f"{result['files_deleted']} files, "
                f"{result['bytes_deleted'] / (1024*1024):.2f} MB"
            )

        except Exception as e:
            error_msg = f"Failed to list/delete GCS files for project {project_id}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)

        return result

    def _delete_firestore_docs(
        self, 
        project_id: str, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Delete all Firestore documents associated with a project.

        Deletes:
        - reel_projects/{project_id}
        - reel_jobs (where payload.project_id == project_id)
        - reel_jobs/{job_id}/progress_logs/* (subcollections)

        Returns:
            {
                "docs_deleted": int,
                "errors": List[str]
            }
        """
        result = {
            "docs_deleted": 0,
            "errors": []
        }

        try:
            # 1. Delete reel_jobs and their subcollections
            jobs_result = self._delete_project_jobs(project_id, dry_run)
            result["docs_deleted"] += jobs_result["docs_deleted"]
            result["errors"].extend(jobs_result["errors"])

            # 2. Delete the project document itself
            project_ref = db.collection('reel_projects').document(project_id)
            
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting project document: reel_projects/{project_id}")
            
            if not dry_run:
                project_ref.delete()
            
            result["docs_deleted"] += 1

        except Exception as e:
            error_msg = f"Failed to delete Firestore docs for project {project_id}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)

        return result

    def _delete_project_jobs(
        self, 
        project_id: str, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Delete all jobs associated with a project.

        This includes:
        - Job documents in reel_jobs collection
        - progress_logs subcollections for each job

        Returns:
            {
                "docs_deleted": int,
                "errors": List[str]
            }
        """
        result = {
            "docs_deleted": 0,
            "errors": []
        }

        try:
            # Query all jobs for this project
            jobs_query = db.collection('reel_jobs').where(
                filter=firestore.FieldFilter('payload.project_id', '==', project_id)
            )
            
            jobs = list(jobs_query.stream())
            
            if not jobs:
                logger.info(f"No jobs found for project {project_id}")
                return result

            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Found {len(jobs)} jobs for project {project_id}")

            for job_doc in jobs:
                job_id = job_doc.id
                
                try:
                    # Delete progress_logs subcollection
                    progress_result = self._delete_progress_logs(job_id, dry_run)
                    result["docs_deleted"] += progress_result["docs_deleted"]
                    result["errors"].extend(progress_result["errors"])

                    # Delete the job document
                    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting job document: reel_jobs/{job_id}")
                    
                    if not dry_run:
                        job_doc.reference.delete()
                    
                    result["docs_deleted"] += 1

                except Exception as e:
                    error_msg = f"Failed to delete job {job_id}: {str(e)}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Failed to query/delete jobs for project {project_id}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)

        return result

    def _delete_progress_logs(
        self, 
        job_id: str, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Delete all progress_logs for a job.

        Returns:
            {
                "docs_deleted": int,
                "errors": List[str]
            }
        """
        result = {
            "docs_deleted": 0,
            "errors": []
        }

        try:
            progress_ref = db.collection('reel_jobs').document(job_id).collection('progress_logs')
            progress_docs = list(progress_ref.stream())

            if not progress_docs:
                return result

            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting {len(progress_docs)} progress logs for job {job_id}")

            for doc in progress_docs:
                if not dry_run:
                    doc.reference.delete()
                result["docs_deleted"] += 1

        except Exception as e:
            error_msg = f"Failed to delete progress logs for job {job_id}: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)

        return result

    def get_project_size(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get the size of a project (useful before deletion).

        Returns:
            {
                "project_id": str,
                "gcs_files": int,
                "gcs_bytes": int,
                "gcs_mb": float,
                "firestore_docs": int
            }
        """
        # Use dry_run to calculate size without deleting
        report = self.delete_project(project_id, user_id, dry_run=True)
        
        return {
            "project_id": project_id,
            "gcs_files": report["deleted"]["gcs_files"],
            "gcs_bytes": report["deleted"]["gcs_bytes"],
            "gcs_mb": report["deleted"]["gcs_bytes"] / (1024 * 1024),
            "firestore_docs": report["deleted"]["firestore_docs"]
        }


# Singleton instance
_deletion_service = None


def get_deletion_service() -> ReelDeletionService:
    """Get singleton instance of deletion service."""
    global _deletion_service
    if _deletion_service is None:
        _deletion_service = ReelDeletionService()
    return _deletion_service
