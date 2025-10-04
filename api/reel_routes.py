"""
Reel Maker API routes - REST endpoints for reel project management.
"""
import json
import logging
import time
from flask import Blueprint, Response, jsonify, request, session, stream_with_context
from api.auth_routes import login_required
from middleware.csrf_protection import csrf_protect
from services.reel_generation_service import reel_generation_service
from services.realtime_event_bus import realtime_event_bus
from services.reel_project_service import reel_project_service
from services.reel_state_reconciler import reel_state_reconciler

logger = logging.getLogger(__name__)

# Create Blueprint
reel_bp = Blueprint('reel', __name__, url_prefix='/api/reel')


def serialize_timestamp(value):
    """Convert Firestore timestamp/datetime objects to ISO strings."""
    if value is None:
        return None

    try:
        return value.isoformat()
    except AttributeError:
        return str(value)


def get_current_user():
    """Helper to get current user info from session."""
    return {
        'user_id': session.get('user_id'),
        'user_email': session.get('user_email'),
        'user_name': session.get('user_name', '')
    }

@reel_bp.route('/projects', methods=['GET'])
@login_required
def list_projects():
    """List all projects for the current user."""
    try:
        user = get_current_user()
        user_id = user['user_id']
        
        if not user_id:
            return jsonify({
                "success": False, 
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401
        
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 100)  # Cap at 100
        
        projects = reel_project_service.get_user_projects(user_id, limit=limit)
        
        # Convert to API format
        project_list = []
        for project in projects:
            # Calculate completion status for each project
            completion = reel_project_service.get_completion_status(project, verify_gcs=False)
            
            project_data = {
                'projectId': project.project_id,
                'title': project.title,
                'orientation': project.orientation,
                'status': project.status,
                'clipCount': len(project.clip_filenames),
                'hasStitchedReel': bool(project.stitched_filename),
                'createdAt': serialize_timestamp(project.created_at),
                'updatedAt': serialize_timestamp(project.updated_at),
                # Add completion metadata
                'completionStatus': completion
            }
            project_list.append(project_data)

        return jsonify({
            "success": True,
            "projects": project_list,
            "count": len(project_list)
        })
    
    except Exception as e:
        logger.error(f"Failed to list projects for user {session.get('user_id')}: {e}")
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to retrieve projects"}
        }), 500

@reel_bp.route('/projects', methods=['POST'])
@csrf_protect
@login_required
def create_project():
    """Create a new reel project."""
    try:
        user = get_current_user()
        user_id = user['user_id']
        user_email = user['user_email']
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401
        
        # Parse request data
        data = request.get_json() or {}
        title = data.get('title', '').strip()
        
        if not title:
            return jsonify({
                "success": False,
                "error": {"code": "VALIDATION_ERROR", "message": "Project title is required"}
            }), 400
        
        if len(title) > 100:
            return jsonify({
                "success": False,
                "error": {"code": "VALIDATION_ERROR", "message": "Project title must be 100 characters or less"}
            }), 400
        
        # Create project
        project = reel_project_service.create_project(
            user_id=user_id,
            user_email=user_email or '',
            title=title
        )
        
        # Return created project
        return jsonify({
            "success": True,
            "project": {
                'projectId': project.project_id,
                'title': project.title,
                'orientation': project.orientation,
                'durationSeconds': project.duration_seconds,
                'compression': project.compression,
                'model': project.model,
                'audioEnabled': project.audio_enabled,
                'status': project.status,
                'clipCount': 0,
                'hasStitchedReel': False,
                'createdAt': serialize_timestamp(project.created_at),
                'updatedAt': serialize_timestamp(project.updated_at)
            }
        }), 201
    
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": str(e)}
        }), 400
    
    except Exception as e:
        logger.error(f"Failed to create project for user {session.get('user_id')}: {e}")
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to create project"}
        }), 500

@reel_bp.route('/projects/<project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    """Get a specific project with full details."""
    try:
        user = get_current_user()
        user_id = user['user_id']
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401
        
        project = reel_project_service.get_project(project_id, user_id)
        
        if not project:
            return jsonify({
                "success": False,
                "error": {"code": "NOT_FOUND", "message": "Project not found"}
            }), 404
        
        # Return full project details
        return jsonify({
            "success": True,
            "project": {
                'projectId': project.project_id,
                'title': project.title,
                'orientation': project.orientation,
                'durationSeconds': project.duration_seconds,
                'compression': project.compression,
                'model': project.model,
                'audioEnabled': project.audio_enabled,
                'promptList': project.prompt_list,
                'clipFilenames': project.clip_filenames,
                'stitchedFilename': project.stitched_filename,
                'status': project.status,
                'errorInfo': project.error_info,
                'createdAt': serialize_timestamp(project.created_at),
                'updatedAt': serialize_timestamp(project.updated_at),
                'clipCount': len(project.clip_filenames),
                'hasStitchedReel': bool(project.stitched_filename),
                # Add completion status for smart UI display
                'completionStatus': reel_project_service.get_completion_status(project, verify_gcs=False)
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}")
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to retrieve project"}
        }), 500

@reel_bp.route('/projects/<project_id>/reconcile', methods=['POST'])
@csrf_protect
@login_required
def reconcile_project_state(project_id):
    """
    Reconcile project state with actual GCS assets.
    Verifies claimed clips exist and corrects status if needed.
    Called automatically on project load to prevent stuck states.
    """
    try:
        user = get_current_user()
        user_id = user['user_id']
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401
        
        # Run reconciliation
        report = reel_state_reconciler.reconcile_project(project_id, user_id, auto_fix=True)
        
        if "error" in report:
            return jsonify({
                "success": False,
                "error": {"code": "NOT_FOUND", "message": report["error"]},
                "report": report
            }), 404
        
        return jsonify({
            "success": True,
            "report": report
        }), 200
    
    except Exception as e:
        logger.exception(f"Failed to reconcile project {project_id}")
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Reconciliation failed"}
        }), 500

@reel_bp.route('/projects/<project_id>', methods=['PUT'])
@csrf_protect
@login_required
def update_project(project_id):
    """Update project title and configuration."""
    try:
        user = get_current_user()
        user_id = user['user_id']
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401
        
        # Parse request data
        data = request.get_json() or {}
        
        # Build updates dict
        updates = {}
        
        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return jsonify({
                    "success": False,
                    "error": {"code": "VALIDATION_ERROR", "message": "Title cannot be empty"}
                }), 400
            if len(title) > 100:
                return jsonify({
                    "success": False,  
                    "error": {"code": "VALIDATION_ERROR", "message": "Title must be 100 characters or less"}
                }), 400
            updates['title'] = title
        
        if 'orientation' in data:
            orientation = data['orientation']
            if orientation not in ['portrait', 'landscape']:
                return jsonify({
                    "success": False,
                    "error": {"code": "VALIDATION_ERROR", "message": "Orientation must be 'portrait' or 'landscape'"}
                }), 400
            updates['orientation'] = orientation
        
        if 'audioEnabled' in data:
            updates['audio_enabled'] = bool(data['audioEnabled'])

        if 'promptList' in data:
            prompt_list = data['promptList']
            if not isinstance(prompt_list, list):
                return jsonify({
                    "success": False,
                    "error": {"code": "VALIDATION_ERROR", "message": "promptList must be an array"}
                }), 400

            cleaned_prompts = [str(item).strip() for item in prompt_list if str(item).strip()]
            updates['prompt_list'] = cleaned_prompts
        
        if not updates:
            return jsonify({
                "success": False,
                "error": {"code": "VALIDATION_ERROR", "message": "No valid fields to update"}
            }), 400
        
        # Update project
        success = reel_project_service.update_project(project_id, user_id, **updates)
        
        if not success:
            return jsonify({
                "success": False,
                "error": {"code": "NOT_FOUND", "message": "Project not found or access denied"}
            }), 404
        
        return jsonify({
            "success": True,
            "message": "Project updated successfully"
        })
    
    except Exception as e:
        logger.error(f"Failed to update project {project_id}: {e}")
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to update project"}
        }), 500

@reel_bp.route('/projects/<project_id>', methods=['DELETE'])
@csrf_protect
@login_required
def delete_project(project_id):
    """
    Delete a project and ALL associated resources.
    
    This will permanently delete:
    - All video clips from GCS
    - Stitched video from GCS
    - Prompt files from GCS
    - Project document from Firestore
    - All job documents from Firestore
    - All progress logs from Firestore
    
    WARNING: This action cannot be undone!
    """
    try:
        user = get_current_user()
        user_id = user['user_id']
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401
        
        # Import deletion service
        from services.reel_deletion_service import get_deletion_service
        deletion_service = get_deletion_service()
        
        # Perform comprehensive deletion
        report = deletion_service.delete_project(
            project_id=project_id,
            user_id=user_id,
            dry_run=False
        )
        
        if not report["success"]:
            # Check if it's an authorization error
            if any("does not own" in err for err in report["errors"]):
                return jsonify({
                    "success": False,
                    "error": {"code": "FORBIDDEN", "message": "You do not have permission to delete this project"}
                }), 403
            
            # Check if project not found
            if any("not found" in err for err in report["errors"]):
                return jsonify({
                    "success": False,
                    "error": {"code": "NOT_FOUND", "message": "Project not found"}
                }), 404
            
            # Other errors
            return jsonify({
                "success": False,
                "error": {
                    "code": "DELETION_ERROR",
                    "message": "Failed to delete project completely",
                    "details": report["errors"]
                }
            }), 500
        
        # Success
        return jsonify({
            "success": True,
            "message": "Project and all associated resources deleted successfully",
            "deleted": report["deleted"]
        })
    
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to delete project"}
        }), 500


@reel_bp.route('/projects/<project_id>/generate', methods=['POST'])
@csrf_protect
@login_required
def generate_project(project_id):
    """Trigger video generation for a reel project."""
    try:
        user = get_current_user()
        user_id = user['user_id']

        if not user_id:
            return jsonify({
                "success": False,
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401

        data = request.get_json() or {}
        prompt_list = data.get('promptList')

        if prompt_list is not None and not isinstance(prompt_list, list):
            return jsonify({
                "success": False,
                "error": {"code": "VALIDATION_ERROR", "message": "promptList must be an array"}
            }), 400

        prompts = None
        if prompt_list is not None:
            prompts = [str(item) for item in prompt_list]

        result = reel_generation_service.start_generation(
            project_id=project_id,
            user_id=user_id,
            user_email=user['user_email'] or '',
            prompts=prompts,
        )

        return jsonify({
            "success": True,
            "jobId": result.get('jobId'),
            "promptCount": result.get('promptCount')
        }), 202

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": str(e)}
        }), 400
    except RuntimeError as e:
        logger.error("Failed to start reel generation for project %s: %s", project_id, e)
        return jsonify({
            "success": False,
            "error": {"code": "CONFIG_ERROR", "message": str(e)}
        }), 500
    except Exception as e:  # noqa: BLE001 - capture unexpected errors
        logger.exception("Unexpected error while starting reel generation for project %s", project_id)
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to start generation"}
        }), 500


@reel_bp.route('/projects/<project_id>/jobs/<job_id>', methods=['GET'])
@login_required
def get_generation_job(project_id, job_id):
    """Fetch job summary for a reel generation request."""
    try:
        user = get_current_user()
        user_id = user['user_id']

        if not user_id:
            return jsonify({
                "success": False,
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401

        project = reel_project_service.get_project(project_id, user_id)
        if not project:
            return jsonify({
                "success": False,
                "error": {"code": "NOT_FOUND", "message": "Project not found"}
            }), 404

        job = reel_generation_service.get_job(job_id, user_id, project_id)
        if not job:
            return jsonify({
                "success": False,
                "error": {"code": "NOT_FOUND", "message": "Job not found"}
            }), 404

        # Serialize timestamps for JSON output
        for ts_field in ["createdAt", "updatedAt", "completedAt", "startedAt"]:
            if ts_field in job:
                job[ts_field] = serialize_timestamp(job[ts_field])

        return jsonify({"success": True, "job": job})

    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to fetch reel job %s for project %s", job_id, project_id)
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to retrieve job"}
        }), 500


@reel_bp.route('/projects/<project_id>/jobs/<job_id>/progress', methods=['GET'])
@login_required
def get_job_progress_logs(project_id, job_id):
    """
    Get progress logs for a job.
    Returns real-time progress updates from Cloud Run Job execution.
    
    Query params:
    - since: Only return logs after this log number (for polling)
    - limit: Maximum number of logs to return (default: 50)
    """
    try:
        user = get_current_user()
        user_id = user['user_id']

        if not user_id:
            return jsonify({
                "success": False,
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401

        # Verify project ownership
        project = reel_project_service.get_project(project_id, user_id)
        if not project:
            return jsonify({
                "success": False,
                "error": {"code": "NOT_FOUND", "message": "Project not found"}
            }), 404

        # Get query parameters
        since_log_number = request.args.get('since', type=int, default=0)
        limit = request.args.get('limit', type=int, default=50)
        
        # Fetch progress logs from Firestore
        from firebase_admin import firestore
        db = firestore.client()
        
        progress_ref = (
            db.collection('reel_jobs')
            .document(job_id)
            .collection('progress_logs')
            .where('log_number', '>', since_log_number)
            .order_by('log_number')
            .limit(limit)
        )
        
        logs = []
        for doc in progress_ref.stream():
            log_data = doc.to_dict()
            # Serialize timestamp
            if 'timestamp' in log_data:
                log_data['timestamp'] = serialize_timestamp(log_data['timestamp'])
            logs.append(log_data)
        
        # Also get current job status
        job_ref = db.collection('reel_jobs').document(job_id)
        job_doc = job_ref.get()
        
        job_status = {}
        if job_doc.exists:
            job_data = job_doc.to_dict()
            job_status = {
                'status': job_data.get('status'),
                'progress_percent': job_data.get('progress_percent', 0),
                'current_stage': job_data.get('current_stage', ''),
                'last_progress_message': job_data.get('last_progress_message', ''),
                'last_progress_update': serialize_timestamp(job_data.get('last_progress_update'))
            }

        return jsonify({
            "success": True,
            "logs": logs,
            "job_status": job_status,
            "has_more": len(logs) >= limit
        })

    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to fetch progress logs for job %s", job_id)
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to retrieve progress logs"}
        }), 500


@reel_bp.route('/projects/<project_id>/events', methods=['GET'])
@login_required
def stream_project_events(project_id):
    """Server-sent events stream for a specific reel project."""
    user = get_current_user()
    user_id = user['user_id']

    if not user_id:
        return jsonify({
            "success": False,
            "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
        }), 401

    project = reel_project_service.get_project(project_id, user_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "NOT_FOUND", "message": "Project not found"}
        }), 404

    topic = reel_generation_service.topic_for_project(project_id)

    def event_stream():
        queue = []

        def callback(event: str, payload):
            queue.append((event, payload))

        realtime_event_bus.subscribe(topic, callback)

        try:
            yield "event: init\ndata: {}\n\n"
            while True:
                while queue:
                    event, payload = queue.pop(0)
                    try:
                        data_str = json.dumps(payload)
                    except (TypeError, ValueError):
                        data_str = json.dumps({"message": "Unable to serialize payload"})
                    yield f"event: {event}\ndata: {data_str}\n\n"
                time.sleep(0.4)
        finally:
            realtime_event_bus.unsubscribe(topic, callback)

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')


@reel_bp.route('/projects/<project_id>/stitch', methods=['POST'])
@csrf_protect
@login_required
def stitch_clips(project_id):
    """Start video stitching job using Cloud Run Jobs to combine all clips into a single reel."""
    try:
        from services.job_orchestrator import get_job_orchestrator
        from jobs.shared.schemas import JobAlreadyRunningError, InsufficientResourcesError, JobError
        JOB_ORCHESTRATOR_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Job orchestrator not available: {e}")
        JOB_ORCHESTRATOR_AVAILABLE = False

    user = get_current_user()
    user_id = user['user_id']

    if not user_id:
        return jsonify({
            "success": False,
            "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
        }), 401

    # Verify project ownership and get project data
    project = reel_project_service.get_project(project_id, user_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "NOT_FOUND", "message": "Project not found or access denied"}
        }), 404

    # Validate we have clips to stitch
    if not project.clip_filenames or len(project.clip_filenames) < 2:
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_REQUEST", "message": "Need at least 2 clips to stitch"}
        }), 400

    # Check if already stitching
    if project.status == "stitching":
        return jsonify({
            "success": False,
            "error": {"code": "ALREADY_PROCESSING", "message": "Stitching already in progress"}
        }), 409

    try:
        if not JOB_ORCHESTRATOR_AVAILABLE:
            # Fallback to local processing for development
            import threading
            from services.video_stitching_service import video_stitching_service
            from datetime import datetime

            logger.warning("Using local video stitching service - Cloud Run Jobs not available")

            # Generate job ID for progress tracking
            job_id = f"stitch_{project_id}_{int(datetime.utcnow().timestamp())}"

            # Update project status
            reel_project_service.update_project_status(project_id, user_id, "stitching")

            # Start stitching in background thread
            def stitch_worker():
                try:
                    logger.info(f"Starting local stitch job {job_id} for project {project_id}")

                    stitched_path = video_stitching_service.stitch_clips(
                        user_id=user_id,
                        project_id=project_id,
                        clip_paths=project.clip_filenames,
                        job_id=job_id
                    )

                    if stitched_path:
                        # Update project with stitched filename
                        reel_project_service.update_project_stitched_file(
                            project_id,
                            user_id,
                            stitched_path
                        )
                        reel_project_service.update_project_status(project_id, user_id, "ready")
                        logger.info(f"Local stitch job {job_id} completed successfully")
                    else:
                        reel_project_service.update_project_status(project_id, user_id, "error")
                        logger.error(f"Local stitch job {job_id} failed")

                except Exception as e:
                    logger.exception(f"Local stitch worker failed for job {job_id}: {e}")
                    reel_project_service.update_project_status(project_id, user_id, "error")

            thread = threading.Thread(target=stitch_worker, daemon=True)
            thread.start()

            return jsonify({
                "success": True,
                "message": "Stitching started (local mode)",
                "jobId": job_id,
                "clipCount": len(project.clip_filenames),
                "mode": "local"
            })

        # Use Cloud Run Jobs
        logger.info(f"Using Cloud Run Jobs for stitching project {project_id}")

        # Build output path using the naming convention from video_stitching_service
        output_path = f"reel-maker/{user_id}/{project_id}/stitched/stitched_{project_id}.mp4"

        # Update project status to stitching
        reel_project_service.update_project_status(project_id, user_id, "stitching")

        # Trigger Cloud Run Jobs stitching
        job_orchestrator = get_job_orchestrator()
        job_execution = job_orchestrator.trigger_stitching_job(
            project_id=project_id,
            user_id=user_id,
            clip_paths=project.clip_filenames,
            output_path=output_path,
            orientation="portrait",  # Default to portrait
            compression="optimized",  # Default to optimized
            force_restart=False
        )

        logger.info(f"Cloud Run Job triggered: {job_execution.job_id}")
        
        # Publish SSE event to notify frontend of stitching start
        from services.realtime_event_bus import realtime_event_bus
        topic = reel_generation_service.topic_for_project(project_id)
        realtime_event_bus.publish(
            topic,
            "stitching.started",
            {
                "projectId": project_id,
                "jobId": job_execution.job_id,
                "jobType": job_execution.job_type,
                "clipCount": len(project.clip_filenames),
                "status": "stitching"
            }
        )

        return jsonify({
            "success": True,
            "message": "Stitching started via Cloud Run Jobs",
            "jobId": job_execution.job_id,
            "clipCount": len(project.clip_filenames),
            "mode": "cloud_run_jobs",
            "job": {
                "job_id": job_execution.job_id,
                "job_type": job_execution.job_type,
                "status": job_execution.status,
                "created_at": job_execution.created_at.isoformat()
            }
        })

    except JobAlreadyRunningError as e:
        # Revert project status
        reel_project_service.update_project_status(project_id, user_id, "ready")
        return jsonify({
            "success": False,
            "error": {"code": "ALREADY_PROCESSING", "message": str(e)}
        }), 409

    except InsufficientResourcesError as e:
        # Revert project status
        reel_project_service.update_project_status(project_id, user_id, "ready")
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_REQUEST", "message": str(e)}
        }), 400

    except JobError as e:
        # Revert project status
        reel_project_service.update_project_status(project_id, user_id, "error")
        return jsonify({
            "success": False,
            "error": {"code": "JOB_ERROR", "message": str(e)}
        }), 500

    except Exception as e:
        logger.exception(f"Failed to start stitching for project {project_id}: {e}")
        # Revert project status
        reel_project_service.update_project_status(project_id, user_id, "error")
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to start stitching"}
        }), 500


@reel_bp.route('/projects/<project_id>/clips/<path:clip_path>', methods=['GET'])
@login_required
def stream_clip(project_id, clip_path):
    """Stream a video clip from GCS with efficient chunked streaming."""
    from services.reel_storage_service import reel_storage_service
    from flask import Response
    import io
    
    user = get_current_user()
    user_id = user['user_id']

    if not user_id:
        return jsonify({
            "success": False,
            "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
        }), 401

    # Verify project ownership
    project = reel_project_service.get_project(project_id, user_id)
    if not project:
        return jsonify({
            "success": False,
            "error": {"code": "NOT_FOUND", "message": "Project not found or access denied"}
        }), 404

    # Verify clip belongs to this project (either a raw clip or the stitched video)
    is_stitched = project.stitched_filename == clip_path
    is_raw_clip = clip_path in project.clip_filenames
    
    if not (is_stitched or is_raw_clip):
        return jsonify({
            "success": False,
            "error": {"code": "NOT_FOUND", "message": "Video not found in project"}
        }), 404

    try:
        # Get blob from GCS
        bucket = reel_storage_service._ensure_bucket()
        blob = bucket.blob(clip_path)
        
        if not blob.exists():
            logger.error(f"Clip not found in GCS: {clip_path}")
            return jsonify({
                "success": False,
                "error": {"code": "NOT_FOUND", "message": "Video file not found"}
            }), 404

        # Get blob size for Content-Length header
        blob.reload()
        file_size = blob.size
        
        # Check for range request
        range_header = request.headers.get('Range')
        
        if range_header:
            # Parse range header (e.g., "bytes=0-1023")
            byte_range = range_header.replace('bytes=', '').split('-')
            start = int(byte_range[0]) if byte_range[0] else 0
            end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
            
            # Ensure end doesn't exceed file size
            end = min(end, file_size - 1)
            length = end - start + 1
            
            # Stream the requested range from GCS
            def generate_range():
                # Download only the requested byte range
                chunk_size = 256 * 1024  # 256KB chunks
                downloaded = 0
                
                with blob.open('rb') as f:
                    f.seek(start)
                    remaining = length
                    
                    while remaining > 0:
                        chunk_to_read = min(chunk_size, remaining)
                        chunk = f.read(chunk_to_read)
                        if not chunk:
                            break
                        yield chunk
                        remaining -= len(chunk)
            
            response = Response(generate_range(), 206, mimetype='video/mp4')
            response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response.headers['Content-Length'] = str(length)
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response
        else:
            # Stream entire file
            def generate_full():
                chunk_size = 512 * 1024  # 512KB chunks
                with blob.open('rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            
            response = Response(generate_full(), 200, mimetype='video/mp4')
            response.headers['Content-Length'] = str(file_size)
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response
    
    except Exception as e:
        logger.exception(f"Failed to stream clip {clip_path} for project {project_id}")
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to stream video"}
        }), 500


@reel_bp.route('/projects/<project_id>/stitch', methods=['POST'])
@csrf_protect
@login_required
def stitch_project_clips(project_id):
    """
    Trigger video stitching job for a project using Cloud Run Jobs.

    This endpoint triggers a separate Cloud Run Job to handle video stitching,
    providing better resource isolation and cost optimization.
    """
    try:
        user = get_current_user()
        user_id = user['user_id']

        if not user_id:
            return jsonify({
                "success": False,
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401

        # Get project details
        try:
            project = reel_project_service.get_project(project_id, user_id)
        except Exception as e:
            return jsonify({
                "success": False,
                "error": {"code": "NOT_FOUND", "message": f"Project not found: {str(e)}"}
            }), 404

        # Validate project has clips for stitching
        if not project.clip_filenames or len(project.clip_filenames) < 2:
            return jsonify({
                "success": False,
                "error": {"code": "INSUFFICIENT_CLIPS", "message": "Project needs at least 2 clips for stitching"}
            }), 400

        # Check if already stitched
        if project.stitched_filename and not request.json.get('force_restart', False):
            return jsonify({
                "success": False,
                "error": {"code": "ALREADY_STITCHED", "message": "Project already has a stitched video"}
            }), 409

        # Import job orchestrator
        try:
            from services.job_orchestrator import get_job_orchestrator
            job_orchestrator = get_job_orchestrator()
        except ImportError:
            return jsonify({
                "success": False,
                "error": {"code": "SERVICE_UNAVAILABLE", "message": "Job orchestrator service not available"}
            }), 503
        from services.reel_storage_service import reel_storage_service

        # Prepare clip paths (full GCS paths)
        bucket_name = reel_storage_service.bucket_name
        clip_paths = [f"gs://{bucket_name}/{clip}" for clip in project.clip_filenames]

        # Generate output path
        import uuid
        output_filename = f"reel_stitched_{uuid.uuid4().hex[:8]}.mp4"
        output_path = f"gs://{bucket_name}/reel-maker/{user_id}/{project_id}/stitched/{output_filename}"

        # Trigger stitching job
        job_execution = job_orchestrator.trigger_stitching_job(
            project_id=project_id,
            user_id=user_id,
            clip_paths=clip_paths,
            output_path=output_path,
            orientation=project.orientation,
            compression=project.compression,
            force_restart=request.json.get('force_restart', False)
        )

        # Update project status to indicate stitching in progress
        reel_project_service.update_project_status(project_id, "stitching")

        return jsonify({
            "success": True,
            "job": {
                "jobId": job_execution.job_id,
                "projectId": project_id,
                "status": job_execution.status,
                "clipCount": len(clip_paths),
                "estimatedDuration": "5-10 minutes"
            }
        })

    except Exception as e:
        logger.error(f"Failed to trigger stitching job for project {project_id}: {e}", exc_info=True)

        # Handle specific job errors
        if "JobAlreadyRunningError" in str(type(e)):
            return jsonify({
                "success": False,
                "error": {"code": "JOB_RUNNING", "message": "Stitching job already running for this project"}
            }), 409
        elif "InsufficientResourcesError" in str(type(e)):
            return jsonify({
                "success": False,
                "error": {"code": "INSUFFICIENT_RESOURCES", "message": str(e)}
            }), 400
        else:
            return jsonify({
                "success": False,
                "error": {"code": "SERVER_ERROR", "message": "Failed to start stitching job"}
            }), 500


# Health check endpoint for testing
@reel_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({
        "success": True,
        "service": "reel-maker-api",
        "status": "healthy"
    })