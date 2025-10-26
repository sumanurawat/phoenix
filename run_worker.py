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
from flask import Flask
from werkzeug.serving import make_server

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
    print(f"Health check server listening on port {port}")
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
    print(f"Starting Celery worker: {' '.join(cmd)}")

    # Run celery and forward output
    process = subprocess.Popen(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
        text=True
    )

    # Wait for celery to exit
    return_code = process.wait()
    print(f"Celery worker exited with code {return_code}")
    sys.exit(return_code)

if __name__ == '__main__':
    print("=" * 80)
    print("Phoenix Video Worker - Starting")
    print("=" * 80)

    # Start health check server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Run Celery worker in main thread (foreground)
    run_celery_worker()
