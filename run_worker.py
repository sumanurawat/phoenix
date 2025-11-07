#!/usr/bin/env python3
"""
Celery Worker with HTTP Health Check Endpoint

This wrapper runs the Celery worker in a subprocess while providing
an HTTP health endpoint on PORT (required by Cloud Run Services).
"""
import os
import sys
import subprocess
import threading
import logging
from flask import Flask
from werkzeug.serving import make_server

# Configure logging for Cloud Run (JSON format to stdout)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Force unbuffered output for Cloud Run
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# Create minimal Flask app for health checks
health_app = Flask(__name__)

@health_app.route('/')
@health_app.route('/health')
def health_check():
    """Health check endpoint for Cloud Run"""
    return {'status': 'healthy', 'service': 'phoenix-video-worker'}, 200

def run_health_server():
    """Run HTTP health check server"""
    port = int(os.getenv('PORT', 8080))
    server = make_server('0.0.0.0', port, health_app, threaded=True)
    logger.info(f"🏥 Health check server listening on port {port}")
    server.serve_forever()

def run_celery_worker():
    """Run Celery worker in foreground"""
    cmd = [
        'celery',
        '-A', 'celery_app',
        'worker',
        '--loglevel=info',
        '--concurrency=2',
        '--pool=solo'
    ]
    logger.info(f"🚀 Starting Celery worker: {' '.join(cmd)}")
    sys.stdout.flush()

    # Run celery and forward output
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Stream output line by line
    for line in iter(process.stdout.readline, ''):
        if line:
            print(line.rstrip(), flush=True)

    # Wait for celery to exit
    return_code = process.wait()
    logger.error(f"❌ Celery worker exited with code {return_code}")
    sys.exit(return_code)

if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("🎬 Phoenix Video Worker - Starting")
    logger.info("=" * 80)

    # Start health check server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Run Celery worker in main thread (foreground)
    run_celery_worker()
