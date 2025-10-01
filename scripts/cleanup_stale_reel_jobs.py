#!/usr/bin/env python3
"""
Cleanup script for stale reel generation jobs.
Run periodically (e.g., via cron) to detect and fix stuck jobs.

Usage:
    python scripts/cleanup_stale_reel_jobs.py [--timeout MINUTES]
    
Example:
    # Check for jobs stuck longer than 30 minutes (default)
    python scripts/cleanup_stale_reel_jobs.py
    
    # Check for jobs stuck longer than 60 minutes
    python scripts/cleanup_stale_reel_jobs.py --timeout 60
"""
import sys
import os
import argparse

# Add parent directory to path to import services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.reel_generation_service import reel_generation_service


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup stale reel generation jobs stuck in processing state"
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Timeout in minutes (default: 30)'
    )
    args = parser.parse_args()
    
    print(f"Checking for reel generation jobs stuck longer than {args.timeout} minutes...")
    
    try:
        stale_projects = reel_generation_service.check_stale_jobs(timeout_minutes=args.timeout)
        
        if stale_projects:
            print(f"✓ Cleaned up {len(stale_projects)} stale project(s):")
            for project_id in stale_projects:
                print(f"  - {project_id}")
        else:
            print("✓ No stale jobs found")
        
        return 0
    
    except Exception as e:
        print(f"✗ Error checking stale jobs: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
