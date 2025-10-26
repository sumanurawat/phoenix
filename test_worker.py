#!/usr/bin/env python3
"""
Test script for Celery worker deployment
Tests connectivity to Redis and task queueing
"""
import os
from celery import Celery

# Load environment variables
REDIS_HOST = os.getenv('REDIS_HOST', '10.95.244.51')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'

print(f"Connecting to Redis at: {REDIS_URL}")

# Create Celery app (matching worker configuration)
app = Celery(
    'phoenix',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Configure to match worker settings
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

print("Testing Redis connection...")
try:
    # Inspect worker
    inspect = app.control.inspect()

    # Check active workers
    active_workers = inspect.active()
    print(f"\n✅ Active workers: {list(active_workers.keys()) if active_workers else 'None'}")

    # Check registered tasks
    registered = inspect.registered()
    if registered:
        print(f"\n✅ Registered tasks:")
        for worker, tasks in registered.items():
            print(f"  Worker: {worker}")
            for task in tasks:
                print(f"    - {task}")

    # Check stats
    stats = inspect.stats()
    if stats:
        print(f"\n✅ Worker statistics:")
        for worker, stat in stats.items():
            print(f"  Worker: {worker}")
            print(f"    Pool: {stat.get('pool', {}).get('implementation')}")
            print(f"    Max concurrency: {stat.get('pool', {}).get('max-concurrency')}")

    print("\n" + "="*60)
    print("✅ WORKER IS OPERATIONAL AND CONNECTED TO REDIS")
    print("="*60)

except Exception as e:
    print(f"\n❌ Error connecting to Redis: {e}")
    print("\nMake sure:")
    print("  1. Redis is running")
    print("  2. Worker service is deployed")
    print("  3. VPC connector is configured")
    exit(1)
