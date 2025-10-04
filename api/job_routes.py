"""
Job Management API routes for Cloud Run Jobs.
"""
import logging
from flask import Blueprint, Response, jsonify, request, session

from api.auth_routes import login_required
from middleware.csrf_protection import csrf_protect
try:
    from services.job_orchestrator import get_job_orchestrator
    JOB_ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    # Fallback for when job orchestrator dependencies are missing
    import logging
    logging.warning(f"Job orchestrator not available: {e}")
    get_job_orchestrator = None
    JOB_ORCHESTRATOR_AVAILABLE = False
from jobs.shared.schemas import JobError, JobAlreadyRunningError, InsufficientResourcesError

logger = logging.getLogger(__name__)

# Create Blueprint
job_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')


def get_current_user():
    """Helper to get current user info from session."""
    return {
        'user_id': session.get('user_id'),
        'user_email': session.get('user_email'),
        'user_name': session.get('user_name', '')
    }


@job_bp.route('/<job_id>/status', methods=['GET'])
@login_required
def get_job_status(job_id: str):
    """
    Get status of a specific job.

    Returns:
        JSON response with job status information
    """
    try:
        if not JOB_ORCHESTRATOR_AVAILABLE:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'SERVICE_UNAVAILABLE',
                    'message': 'Job orchestrator service is not available'
                }
            }), 503

        job_orchestrator = get_job_orchestrator()
        job_status = job_orchestrator.get_job_status(job_id)

        if not job_status:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'JOB_NOT_FOUND',
                    'message': f'Job {job_id} not found'
                }
            }), 404

        # Verify user has permission to view this job
        user = get_current_user()
        # TODO: Add proper authorization check when job payload includes user_id

        return jsonify({
            'success': True,
            'job': job_status.to_dict()
        })

    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Failed to retrieve job status'
            }
        }), 500


@job_bp.route('/<job_id>/cancel', methods=['POST'])
@login_required
@csrf_protect
def cancel_job(job_id: str):
    """
    Cancel a running job.

    Returns:
        JSON response indicating success or failure
    """
    try:
        if not JOB_ORCHESTRATOR_AVAILABLE:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'SERVICE_UNAVAILABLE',
                    'message': 'Job orchestrator service is not available'
                }
            }), 503

        user = get_current_user()
        user_id = user['user_id']

        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'User not authenticated'
                }
            }), 401

        job_orchestrator = get_job_orchestrator()
        success = job_orchestrator.cancel_job(job_id, user_id)

        if success:
            return jsonify({
                'success': True,
                'message': f'Job {job_id} has been cancelled'
            })
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'CANCEL_FAILED',
                    'message': 'Failed to cancel job or job not found'
                }
            }), 400

    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Failed to cancel job'
            }
        }), 500


@job_bp.route('/project/<project_id>', methods=['GET'])
@login_required
def list_project_jobs(project_id: str):
    """
    List all jobs for a specific project.

    Query parameters:
        limit: Maximum number of jobs to return (default: 10)

    Returns:
        JSON response with list of jobs
    """
    try:
        if not JOB_ORCHESTRATOR_AVAILABLE:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'SERVICE_UNAVAILABLE',
                    'message': 'Job orchestrator service is not available'
                }
            }), 503

        # Verify user has access to this project
        user = get_current_user()
        # TODO: Add proper project authorization check

        limit = request.args.get('limit', 10, type=int)
        if limit > 50:  # Prevent excessive requests
            limit = 50

        job_orchestrator = get_job_orchestrator()
        jobs = job_orchestrator.list_project_jobs(project_id, limit)

        return jsonify({
            'success': True,
            'jobs': [job.to_dict() for job in jobs],
            'count': len(jobs)
        })

    except Exception as e:
        logger.error(f"Failed to list jobs for project {project_id}: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Failed to retrieve project jobs'
            }
        }), 500


@job_bp.route('/trigger/stitching', methods=['POST'])
@login_required
@csrf_protect
def trigger_stitching_job():
    """
    Trigger a video stitching job.

    Request body:
        {
            "project_id": "string",
            "clip_paths": ["gs://bucket/path1.mp4", "gs://bucket/path2.mp4"],
            "output_path": "gs://bucket/output.mp4",
            "orientation": "portrait|landscape" (optional),
            "compression": "optimized|lossless" (optional),
            "force_restart": boolean (optional)
        }

    Returns:
        JSON response with job execution details
    """
    try:
        if not JOB_ORCHESTRATOR_AVAILABLE:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'SERVICE_UNAVAILABLE',
                    'message': 'Job orchestrator service is not available'
                }
            }), 503

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Request body must be JSON'
                }
            }), 400

        # Validate required fields
        required_fields = ['project_id', 'clip_paths', 'output_path']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_FIELDS',
                    'message': f'Missing required fields: {missing_fields}'
                }
            }), 400

        # Get user info
        user = get_current_user()
        user_id = user['user_id']

        if not user_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'User not authenticated'
                }
            }), 401

        # Validate clip_paths
        clip_paths = data['clip_paths']
        if not isinstance(clip_paths, list) or len(clip_paths) < 2:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_CLIPS',
                    'message': 'At least 2 clip paths are required'
                }
            }), 400

        # Trigger the job
        job_orchestrator = get_job_orchestrator()
        job_execution = job_orchestrator.trigger_stitching_job(
            project_id=data['project_id'],
            user_id=user_id,
            clip_paths=clip_paths,
            output_path=data['output_path'],
            orientation=data.get('orientation', 'portrait'),
            compression=data.get('compression', 'optimized'),
            force_restart=data.get('force_restart', False)
        )

        return jsonify({
            'success': True,
            'job': {
                'job_id': job_execution.job_id,
                'job_type': job_execution.job_type,
                'status': job_execution.status,
                'created_at': job_execution.created_at.isoformat()
            }
        })

    except JobAlreadyRunningError as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'JOB_ALREADY_RUNNING',
                'message': str(e)
            }
        }), 409

    except InsufficientResourcesError as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INSUFFICIENT_RESOURCES',
                'message': str(e)
            }
        }), 400

    except JobError as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'JOB_ERROR',
                'message': str(e)
            }
        }), 500

    except Exception as e:
        logger.error(f"Failed to trigger stitching job: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Failed to trigger stitching job'
            }
        }), 500


@job_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for job services.

    Returns:
        JSON response with service health status
    """
    try:
        # Check basic connectivity
        health_status = {
            'service': 'job_management',
            'status': 'healthy',
            'timestamp': 'now',
            'checks': {
                'orchestrator': 'ok',
                'database': 'ok',
                'queue': 'ok'
            }
        }

        # TODO: Add actual health checks for:
        # - Firestore connectivity
        # - Cloud Tasks queue status
        # - Service account permissions

        return jsonify(health_status)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'service': 'job_management',
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@job_bp.route('/<job_id>/progress', methods=['GET'])
@login_required
def get_job_progress(job_id: str):
    """
    Get real-time job progress by polling logs and job status.

    Returns:
        JSON response with progress information and recent log messages
    """
    try:
        if not JOB_ORCHESTRATOR_AVAILABLE:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'SERVICE_UNAVAILABLE',
                    'message': 'Job orchestrator service is not available'
                }
            }), 503

        job_orchestrator = get_job_orchestrator()
        job_status = job_orchestrator.get_job_status(job_id)

        if not job_status:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'JOB_NOT_FOUND',
                    'message': f'Job {job_id} not found'
                }
            }), 404

        # Get user info for authorization
        user = get_current_user()
        # TODO: Add proper authorization check when job payload includes user_id

        # Parse recent logs to extract progress information
        progress_info = _parse_job_progress_from_logs(job_id, job_status)

        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': job_status.status,
            'progress': progress_info['progress'],
            'current_step': progress_info['current_step'],
            'total_steps': progress_info['total_steps'],
            'message': progress_info['message'],
            'recent_logs': progress_info['recent_logs'],
            'estimated_time_remaining': progress_info['estimated_time_remaining'],
            'created_at': job_status.created_at.isoformat() if job_status.created_at else None,
            'started_at': job_status.started_at.isoformat() if job_status.started_at else None
        })

    except Exception as e:
        logger.error(f"Failed to get job progress for {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Failed to retrieve job progress'
            }
        }), 500


def _parse_job_progress_from_logs(job_id: str, job_status):
    """Parse job logs to extract progress information."""
    try:
        import subprocess
        import json
        from datetime import datetime, timedelta

        # Default progress info
        progress_info = {
            'progress': 0.0,
            'current_step': 0,
            'total_steps': 0,
            'message': 'Starting...',
            'recent_logs': [],
            'estimated_time_remaining': None
        }

        # Use job status progress if available
        if hasattr(job_status, 'progress') and job_status.progress:
            progress_info['progress'] = job_status.progress

        if hasattr(job_status, 'message') and job_status.message:
            progress_info['message'] = job_status.message

        # Try to get recent logs from Cloud Logging
        try:
            # Query logs for the last 10 minutes for this job
            since_time = (datetime.utcnow() - timedelta(minutes=10)).isoformat() + 'Z'

            cmd = [
                'gcloud', 'logging', 'read',
                f'resource.type="cloud_run_job" AND jsonPayload.job_id="{job_id}" AND timestamp>="{since_time}"',
                '--format=json',
                '--limit=20'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logs = json.loads(result.stdout) if result.stdout.strip() else []

                # Parse logs for progress indicators
                for log_entry in reversed(logs):  # Most recent first
                    if 'textPayload' in log_entry:
                        text = log_entry['textPayload']
                        timestamp = log_entry.get('timestamp', '')

                        # Add to recent logs
                        progress_info['recent_logs'].append({
                            'timestamp': timestamp,
                            'message': text
                        })

                        # Parse progress patterns
                        if 'Downloaded clip' in text:
                            # Extract: "Downloaded clip 3/15"
                            import re
                            match = re.search(r'Downloaded clip (\d+)/(\d+)', text)
                            if match:
                                current, total = int(match.group(1)), int(match.group(2))
                                progress_info['current_step'] = current
                                progress_info['total_steps'] = total
                                progress_info['progress'] = (current / total) * 30  # Download is ~30% of total
                                progress_info['message'] = f'Downloading clips ({current}/{total})'

                        elif 'FFmpeg' in text and 'progress' in text:
                            # Extract FFmpeg progress
                            match = re.search(r'progress[:\s]*(\d+)%', text)
                            if match:
                                ffmpeg_progress = int(match.group(1))
                                progress_info['progress'] = 30 + (ffmpeg_progress * 0.6)  # FFmpeg is 60% of total
                                progress_info['message'] = f'Processing video ({ffmpeg_progress}%)'

                        elif 'Uploaded' in text and 'stitched' in text:
                            progress_info['progress'] = 95.0
                            progress_info['message'] = 'Uploading result...'

                        elif 'completed successfully' in text:
                            progress_info['progress'] = 100.0
                            progress_info['message'] = 'Completed successfully!'

                # Limit recent logs to last 5
                progress_info['recent_logs'] = progress_info['recent_logs'][-5:]

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout getting logs for job {job_id}")
        except Exception as e:
            logger.warning(f"Failed to parse logs for job {job_id}: {e}")

        # Estimate time remaining based on current progress
        if progress_info['progress'] > 0 and job_status.created_at:
            elapsed_seconds = (datetime.now(job_status.created_at.tzinfo) - job_status.created_at).total_seconds()
            if elapsed_seconds > 0:
                total_estimated = elapsed_seconds / (progress_info['progress'] / 100)
                remaining = max(0, total_estimated - elapsed_seconds)
                progress_info['estimated_time_remaining'] = int(remaining)

        return progress_info

    except Exception as e:
        logger.error(f"Error parsing job progress: {e}")
        return {
            'progress': 0.0,
            'current_step': 0,
            'total_steps': 0,
            'message': 'Processing...',
            'recent_logs': [],
            'estimated_time_remaining': None
        }


@job_bp.route('/stats', methods=['GET'])
@login_required
def job_statistics():
    """
    Get job execution statistics.

    Query parameters:
        days: Number of days to look back (default: 7)

    Returns:
        JSON response with job statistics
    """
    try:
        days = request.args.get('days', 7, type=int)
        if days > 30:  # Limit lookback period
            days = 30

        # TODO: Implement statistics gathering
        # This would query Firestore for job statistics

        stats = {
            'period_days': days,
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'average_duration_seconds': 0,
            'job_types': {
                'video_stitching': {
                    'total': 0,
                    'completed': 0,
                    'failed': 0
                }
            }
        }

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        logger.error(f"Failed to get job statistics: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Failed to retrieve job statistics'
            }
        }), 500


# Error handlers
@job_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
                'success': False,
        'error': {
            'code': 'NOT_FOUND',
            'message': 'Endpoint not found'
        }
    }), 404


@job_bp.route('/<job_id>/reconcile', methods=['POST'])
@login_required
@csrf_protect
def reconcile_job_state(job_id: str):
    """
    Manually trigger job state reconciliation.
    
    This checks:
    - If output exists in GCS
    - Cloud Run execution actual status
    - If job is stale/timed out
    
    And updates Firestore accordingly.
    """
    try:
        if not JOB_ORCHESTRATOR_AVAILABLE:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'SERVICE_UNAVAILABLE',
                    'message': 'Job orchestrator service is not available'
                }
            }), 503
        
        orchestrator = get_job_orchestrator()
        
        # Get job data
        job_doc = orchestrator.db.collection('reel_jobs').document(job_id).get()
        if not job_doc.exists:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': f'Job {job_id} not found'
                }
            }), 404
        
        job_data = job_doc.to_dict()
        
        # Perform reconciliation
        was_updated = orchestrator._auto_reconcile_job_state(job_id, job_data)
        
        # Get updated data
        updated_doc = orchestrator.db.collection('reel_jobs').document(job_id).get()
        updated_data = updated_doc.to_dict()
        
        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'was_updated': was_updated,
                'status': updated_data.get('status'),
                'message': updated_data.get('message', ''),
                'reconciliation_performed': True
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to reconcile job {job_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'RECONCILIATION_FAILED',
                'message': str(e)
            }
        }), 500


@job_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        'success': False,
        'error': {
            'code': 'METHOD_NOT_ALLOWED',
            'message': 'Method not allowed for this endpoint'
        }
    }), 405


@job_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error in job routes: {error}")
    return jsonify({
        'success': False,
        'error': {
            'code': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }
    }), 500
