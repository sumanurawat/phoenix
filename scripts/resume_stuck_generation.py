#!/usr/bin/env python3
"""
Resume stuck video generation for projects.
Detects projects stuck in 'generating' status and restarts generation for missing clips.
"""
import sys
import os
from datetime import datetime, timezone, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.reel_project_service import reel_project_service
from services.reel_generation_service import reel_generation_service
from firebase_admin import firestore

def find_stuck_projects(max_age_minutes=30):
    """
    Find projects stuck in 'generating' status for longer than max_age_minutes.
    
    Args:
        max_age_minutes: Consider projects stuck if no update for this long
    
    Returns:
        List of (project_id, user_id, project_data) tuples
    """
    db = firestore.client()
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    
    # Query projects in generating status
    projects_ref = db.collection('reel_projects')
    query = projects_ref.where(filter=firestore.FieldFilter('status', '==', 'generating'))
    
    stuck_projects = []
    
    for doc in query.stream():
        project_data = doc.to_dict()
        updated_at = project_data.get('updatedAt')
        
        # Convert Firestore timestamp to datetime
        if hasattr(updated_at, 'timestamp'):
            updated_dt = datetime.fromtimestamp(updated_at.timestamp(), tz=timezone.utc)
        else:
            continue
        
        # Check if project hasn't been updated recently
        if updated_dt < cutoff_time:
            user_id = project_data.get('userId')
            prompt_count = len(project_data.get('promptList', []))
            clip_count = len([c for c in (project_data.get('clipFilenames') or []) if c])
            
            print(f"Found stuck project: {doc.id}")
            print(f"  User: {user_id}")
            print(f"  Title: {project_data.get('title', 'Untitled')}")
            print(f"  Last updated: {updated_dt}")
            print(f"  Progress: {clip_count}/{prompt_count} clips")
            print(f"  Age: {(datetime.now(timezone.utc) - updated_dt).total_seconds() / 60:.1f} minutes")
            print()
            
            stuck_projects.append((doc.id, user_id, project_data))
    
    return stuck_projects


def resume_generation(project_id, user_id, project_data):
    """
    Resume generation for a stuck project.
    
    Args:
        project_id: Project ID
        user_id: User ID
        project_data: Current project data from Firestore
    
    Returns:
        Result dict from generation service
    """
    print(f"Resuming generation for project {project_id}...")
    
    user_email = project_data.get('userEmail', '')
    prompt_list = project_data.get('promptList', [])
    
    # The generation service will automatically skip clips that already exist
    result = reel_generation_service.start_generation(
        project_id=project_id,
        user_id=user_id,
        user_email=user_email,
        prompts=prompt_list,
    )
    
    print(f"✓ Resumed generation with job ID: {result.get('jobId')}")
    print(f"  Will generate {result.get('promptCount')} prompts")
    print()
    
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Resume stuck video generation')
    parser.add_argument('--project-id', help='Resume specific project by ID')
    parser.add_argument('--user-id', help='User ID (required with --project-id)')
    parser.add_argument('--max-age-minutes', type=int, default=30, 
                       help='Consider projects stuck after this many minutes (default: 30)')
    parser.add_argument('--auto-resume', action='store_true',
                       help='Automatically resume all stuck projects without prompting')
    
    args = parser.parse_args()
    
    # Resume specific project
    if args.project_id:
        if not args.user_id:
            print("Error: --user-id required when using --project-id")
            sys.exit(1)
        
        project = reel_project_service.get_project(args.project_id, args.user_id)
        if not project:
            print(f"Error: Project {args.project_id} not found")
            sys.exit(1)
        
        project_data = {
            'userId': args.user_id,
            'userEmail': project.user_email,
            'promptList': project.prompt_list,
            'title': project.title,
        }
        
        resume_generation(args.project_id, args.user_id, project_data)
        print("✓ Done!")
        return
    
    # Find and resume stuck projects
    print(f"Searching for projects stuck in 'generating' status...")
    print(f"Cutoff: {args.max_age_minutes} minutes\n")
    
    stuck_projects = find_stuck_projects(args.max_age_minutes)
    
    if not stuck_projects:
        print("No stuck projects found.")
        return
    
    print(f"Found {len(stuck_projects)} stuck project(s).\n")
    
    # Resume each stuck project
    for project_id, user_id, project_data in stuck_projects:
        if args.auto_resume:
            resume_generation(project_id, user_id, project_data)
        else:
            response = input(f"Resume generation for project {project_id}? (y/n): ")
            if response.lower() == 'y':
                resume_generation(project_id, user_id, project_data)
            else:
                print(f"Skipped project {project_id}\n")
    
    print("✓ All done!")


if __name__ == '__main__':
    main()
