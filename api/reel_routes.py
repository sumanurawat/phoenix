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
            project_data = {
                'projectId': project.project_id,
                'title': project.title,
                'orientation': project.orientation,
                'status': project.status,
                'clipCount': len(project.clip_filenames),
                'hasStitchedReel': bool(project.stitched_filename),
                'createdAt': serialize_timestamp(project.created_at),
                'updatedAt': serialize_timestamp(project.updated_at)
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
                'hasStitchedReel': bool(project.stitched_filename)
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}")
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "Failed to retrieve project"}
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
    """Delete a project."""
    try:
        user = get_current_user()
        user_id = user['user_id']
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": {"code": "AUTH_ERROR", "message": "User ID not found in session"}
            }), 401
        success = reel_project_service.delete_project(project_id, user_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": {"code": "NOT_FOUND", "message": "Project not found or access denied"}
            }), 404
        
        return jsonify({
            "success": True,
            "message": "Project deleted successfully"
        })
    
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}")
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
    """Start video stitching job to combine all clips into a single reel."""
    import threading
    from services.video_stitching_service import video_stitching_service
    from datetime import datetime
    
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
        # Generate job ID for progress tracking
        job_id = f"stitch_{project_id}_{int(datetime.utcnow().timestamp())}"
        
        # Update project status
        reel_project_service.update_project_status(project_id, user_id, "stitching")
        
        # Start stitching in background thread
        def stitch_worker():
            try:
                logger.info(f"Starting stitch job {job_id} for project {project_id}")
                
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
                    logger.info(f"Stitch job {job_id} completed successfully")
                else:
                    reel_project_service.update_project_status(project_id, user_id, "error")
                    logger.error(f"Stitch job {job_id} failed")
                    
            except Exception as e:
                logger.exception(f"Stitch worker failed for job {job_id}: {e}")
                reel_project_service.update_project_status(project_id, user_id, "error")
        
        thread = threading.Thread(target=stitch_worker, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "Stitching started",
            "jobId": job_id,
            "clipCount": len(project.clip_filenames)
        })
        
    except Exception as e:
        logger.exception(f"Failed to start stitching for project {project_id}: {e}")
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


# Health check endpoint for testing
@reel_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint.""" 
    return jsonify({
        "success": True,
        "service": "reel-maker-api",
        "status": "healthy"
    })