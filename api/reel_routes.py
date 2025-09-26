"""Reel Maker API routes for video project management"""
from __future__ import annotations
import json
import logging
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, Response, stream_with_context, session
from firebase_admin import firestore

from api.auth_routes import login_required
from middleware.csrf_protection import csrf_protect
from services.reel_project_service import ReelProjectService
from services.realtime_event_bus import realtime_event_bus

logger = logging.getLogger(__name__)

reel_bp = Blueprint('reel', __name__, url_prefix='/api/reel')
reel_project_service = ReelProjectService()

@reel_bp.route('/projects', methods=['GET'])
@login_required
def list_projects():
    """List all reel projects for the current user"""
    try:
        user_id = session.get('user_id')
        projects = reel_project_service.list_user_projects(user_id)
        return jsonify({
            "success": True,
            "projects": projects
        })
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@reel_bp.route('/projects', methods=['POST'])
@csrf_protect
@login_required
def create_project():
    """Create a new reel project"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        
        if not title:
            return jsonify({
                "success": False,
                "error": "Project title is required"
            }), 400
            
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        
        project = reel_project_service.create_project(
            user_id=user_id,
            user_email=user_email,
            title=title
        )
        
        return jsonify({
            "success": True,
            "project": project
        })
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@reel_bp.route('/projects/<project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    """Get project details with computed asset URLs"""
    try:
        user_id = session.get('user_id')
        project = reel_project_service.get_project(project_id, user_id)
        
        if not project:
            return jsonify({
                "success": False,
                "error": "Project not found"
            }), 404
            
        return jsonify({
            "success": True,
            "project": project
        })
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@reel_bp.route('/projects/<project_id>', methods=['PUT'])
@csrf_protect
@login_required
def update_project(project_id):
    """Update project title and configuration"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        updates = {}
        if 'title' in data:
            updates['title'] = data['title'].strip()
        if 'orientation' in data:
            if data['orientation'] in ['portrait', 'landscape']:
                updates['orientation'] = data['orientation']
        if 'audioEnabled' in data:
            updates['audioEnabled'] = bool(data['audioEnabled'])
            
        project = reel_project_service.update_project(project_id, user_id, updates)
        
        if not project:
            return jsonify({
                "success": False,
                "error": "Project not found"
            }), 404
            
        return jsonify({
            "success": True,
            "project": project
        })
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@reel_bp.route('/projects/<project_id>', methods=['DELETE'])
@csrf_protect
@login_required
def delete_project(project_id):
    """Delete a project (soft delete by marking as archived)"""
    try:
        user_id = session.get('user_id')
        success = reel_project_service.delete_project(project_id, user_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "Project not found"
            }), 404
            
        return jsonify({
            "success": True,
            "message": "Project deleted successfully"
        })
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@reel_bp.route('/projects/<project_id>/generate', methods=['POST'])
@csrf_protect
@login_required
def generate_videos(project_id):
    """Trigger video generation for the project prompts"""
    try:
        data = request.get_json()
        prompts = data.get('prompts', [])
        
        if not isinstance(prompts, list) or not prompts:
            return jsonify({
                "success": False,
                "error": "prompts must be a non-empty list"
            }), 400
            
        if len(prompts) > 50:
            return jsonify({
                "success": False,
                "error": "Too many prompts. Limit to 50."
            }), 400
            
        user_id = session.get('user_id')
        
        # Start generation job
        job_result = reel_project_service.start_generation(project_id, user_id, prompts)
        
        if not job_result['success']:
            return jsonify(job_result), 404 if 'not found' in job_result['error'] else 500
            
        return jsonify(job_result)
    except Exception as e:
        logger.error(f"Error starting generation: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@reel_bp.route('/projects/<project_id>/stitch', methods=['POST'])
@csrf_protect
@login_required
def stitch_videos(project_id):
    """Start video stitching job for existing clips"""
    try:
        user_id = session.get('user_id')
        
        job_result = reel_project_service.start_stitching(project_id, user_id)
        
        if not job_result['success']:
            return jsonify(job_result), 404 if 'not found' in job_result['error'] else 500
            
        return jsonify(job_result)
    except Exception as e:
        logger.error(f"Error starting stitching: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@reel_bp.route('/projects/<project_id>/clips/<filename>')
@login_required
def stream_clip(project_id, filename):
    """Stream a video clip after ownership verification"""
    try:
        user_id = session.get('user_id')
        
        # Verify project ownership and get clip
        clip_response = reel_project_service.get_clip_stream(project_id, user_id, filename)
        
        if not clip_response:
            return jsonify({
                "success": False,
                "error": "Clip not found or access denied"
            }), 404
            
        return clip_response
    except Exception as e:
        logger.error(f"Error streaming clip: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@reel_bp.route('/projects/<project_id>/status/stream')
@login_required
def stream_status(project_id):
    """SSE channel for job status updates"""
    def event_stream():
        user_id = session.get('user_id')
        
        # Verify project ownership
        project = reel_project_service.get_project(project_id, user_id)
        if not project:
            yield f"event: error\ndata: {json.dumps({'error': 'Project not found'})}\n\n"
            return
            
        # Subscribe to events for this project
        topic = f"reel_{project_id}"
        queue = []
        
        def callback(event, data):
            queue.append((event, data))
            
        realtime_event_bus.subscribe(topic, callback)
        
        try:
            yield f"event: init\ndata: {json.dumps({'project_id': project_id})}\n\n"
            
            while True:
                while queue:
                    event, data = queue.pop(0)
                    yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
                    
                import time
                time.sleep(0.5)
        finally:
            realtime_event_bus.unsubscribe(topic, callback)
    
    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )