"""Video generation API routes (Veo)"""
from __future__ import annotations
import json
import logging
import threading
from flask import Blueprint, request, jsonify, Response, stream_with_context
from services.veo_video_generation_service import VeoGenerationParams, veo_video_service
from services.website_stats_service import WebsiteStatsService
from services.realtime_event_bus import realtime_event_bus

logger = logging.getLogger(__name__)

video_bp = Blueprint('video', __name__, url_prefix='/api/video')
website_stats_service = WebsiteStatsService()

_jobs = {}

def _run_generation(job_id: str, prompts, base_options):
	for idx, prompt in enumerate(prompts):
		evt_topic = job_id
		realtime_event_bus.publish(evt_topic, 'prompt.started', {"prompt_index": idx})
		try:
			# Extract sample count from options, default to 1
			sample_count = base_options.get('sample_count', 1)
			
			params = VeoGenerationParams(
				model=base_options.get('model', 'veo-3.0-fast-generate-001'),
				prompt=prompt,
				aspect_ratio=base_options.get('aspect_ratio', '16:9'),
				duration_seconds=base_options.get('duration_seconds', 8),
				sample_count=sample_count,
				resolution=base_options.get('resolution'),
				generate_audio=base_options.get('generate_audio'),
				enhance_prompt=base_options.get('enhance_prompt', True),
				negative_prompt=base_options.get('negative_prompt'),
				person_generation=base_options.get('person_generation'),
				seed=base_options.get('seed'),
				storage_uri=base_options.get('storage_uri'),
			)
			result = veo_video_service.start_generation(params, poll=True)
			if result.success:
				uri = (result.gcs_uris or result.local_paths or [None])[0]
				realtime_event_bus.publish(evt_topic, 'prompt.completed', {"prompt_index": idx, "video_url": uri, "gcs_uris": result.gcs_uris, "local_paths": result.local_paths})
				_jobs[job_id]['prompts'][idx]['status'] = 'completed'
				_jobs[job_id]['prompts'][idx]['video_url'] = uri
				_jobs[job_id]['prompts'][idx]['gcs_uris'] = result.gcs_uris
				_jobs[job_id]['prompts'][idx]['local_paths'] = result.local_paths
				# Increment videos generated per successful prompt
				try:
					website_stats_service.increment_videos_generated(1)
				except Exception:
					logger.exception('Failed to increment videos generated counter')
			else:
				realtime_event_bus.publish(evt_topic, 'prompt.failed', {"prompt_index": idx, "error": result.error})
				_jobs[job_id]['prompts'][idx]['status'] = 'failed'
				_jobs[job_id]['prompts'][idx]['error'] = result.error
		except Exception as e:  # noqa
			realtime_event_bus.publish(evt_topic, 'prompt.failed', {"prompt_index": idx, "error": str(e)})
			_jobs[job_id]['prompts'][idx]['status'] = 'failed'
			_jobs[job_id]['prompts'][idx]['error'] = str(e)
	realtime_event_bus.publish(job_id, 'job.completed', _jobs[job_id])
	_jobs[job_id]['status'] = 'completed'

@video_bp.route('/generate', methods=['POST'])
def start_video_batch():
	data = request.get_json(force=True, silent=True) or {}
	prompts = data.get('prompts') or []
	if not isinstance(prompts, list) or not prompts:
		return jsonify({"success": False, "error": "prompts must be non-empty list"}), 400
	base_options = data.get('options') or {}
	job_id = f"job_{len(_jobs)+1}"
	_jobs[job_id] = {
		'job_id': job_id,
		'status': 'processing',
		'prompts': [{'prompt': p, 'status': 'queued'} for p in prompts]
	}
	thread = threading.Thread(target=_run_generation, args=(job_id, prompts, base_options), daemon=True)
	thread.start()
	return jsonify({"success": True, "job_id": job_id})

@video_bp.route('/job/<job_id>', methods=['GET'])
def get_job(job_id):
	job = _jobs.get(job_id)
	if not job:
		return jsonify({"success": False, "error": "not found"}), 404
	return jsonify({"success": True, "job": job})

@video_bp.route('/stream/<job_id>')
def stream_events(job_id):
	def event_stream():
		queue = []
		def cb(event, data):
			queue.append((event, data))
		realtime_event_bus.subscribe(job_id, cb)
		try:
			yield f"event: init\ndata: {{}}\n\n"
			while True:
				while queue:
					event, data = queue.pop(0)
					yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
				import time
				time.sleep(0.5)
		finally:
			realtime_event_bus.unsubscribe(job_id, cb)
	return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

@video_bp.route('/config', methods=['GET'])
def get_video_config():
	"""Get available VEO models and configuration options."""
	from services.veo_video_generation_service import VEO_MODELS, ASPECT_RATIOS, RESOLUTIONS, PERSON_GENERATION
	
	config = {
		"models": [
			{
				"id": "veo-3.0-fast-generate-001",
				"name": "VEO 3.0 Fast",
				"description": "Fast generation with good quality",
				"supports_audio": True,
				"supports_resolution": True,
				"recommended": True
			},
			{
				"id": "veo-3.0-generate-001", 
				"name": "VEO 3.0 Standard",
				"description": "High quality generation",
				"supports_audio": True,
				"supports_resolution": True,
				"recommended": False
			},
			{
				"id": "veo-3.0-generate-preview",
				"name": "VEO 3.0 Preview",
				"description": "Preview model with latest features",
				"supports_audio": True,
				"supports_resolution": True,
				"recommended": False
			},
			{
				"id": "veo-3.0-fast-generate-preview",
				"name": "VEO 3.0 Fast Preview", 
				"description": "Fast preview model",
				"supports_audio": True,
				"supports_resolution": True,
				"recommended": False
			},
			{
				"id": "veo-2.0-generate-001",
				"name": "VEO 2.0",
				"description": "Legacy model",
				"supports_audio": False,
				"supports_resolution": False,
				"recommended": False
			}
		],
		"aspect_ratios": ASPECT_RATIOS,
		"resolutions": RESOLUTIONS,
		"person_generation": PERSON_GENERATION,
		"duration_range": {"min": 5, "max": 8},
		"sample_count_range": {"min": 1, "max": 4}
	}
	
	return jsonify({"success": True, "config": config})
