#!/usr/bin/env python3
"""
GCP Cloud Run Log Fetching Script for Phoenix App

Fetches ERROR and WARNING logs from Cloud Run service and saves them to local files.
Requires gcloud CLI authentication.

Usage:
    python scripts/fetch_logs.py                    # Last 2 hours
    python scripts/fetch_logs.py --hours 6          # Last 6 hours  
    python scripts/fetch_logs.py --severity ERROR   # Only errors
    python scripts/fetch_logs.py --search "my-links" # Filter by keyword
    python scripts/fetch_logs.py --save-json        # Also save as JSON
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


class CloudRunLogFetcher:
    """Fetches and analyzes Cloud Run logs from GCP."""
    
    def __init__(self):
        self.project_id = "phoenix-project-386"
        self.project_number = "234619602247"
        self.service_name = "phoenix"
        self.region = "us-central1"
        self.service_url = "https://phoenix-234619602247.us-central1.run.app"
        
        # Base directory for saving logs
        self.base_dir = Path(__file__).parent.parent
        self.temp_logs_dir = self.base_dir / "temp_logs"
        
        # Ensure temp_logs directory exists
        self.temp_logs_dir.mkdir(exist_ok=True)
    
    def check_gcloud_auth(self):
        """Check if gcloud is authenticated."""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
                capture_output=True,
                text=True,
                check=True
            )
            accounts = result.stdout.strip().split('\n')
            active_accounts = [acc for acc in accounts if acc]
            
            if not active_accounts:
                print("❌ No active gcloud authentication found.")
                print("Please run: gcloud auth login")
                return False
            
            print(f"✅ Authenticated as: {active_accounts[0]}")
            return True
            
        except subprocess.CalledProcessError:
            print("❌ gcloud CLI not found or authentication failed.")
            print("Please install gcloud CLI and run: gcloud auth login")
            return False
        except FileNotFoundError:
            print("❌ gcloud CLI not found.")
            print("Please install Google Cloud CLI from: https://cloud.google.com/sdk/docs/install")
            return False
    
    def build_log_filter(self, hours, severity_levels, search_keyword=None):
        """Build the log filter query."""
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        # Base filter for Cloud Run service
        filter_parts = [
            "resource.type=cloud_run_revision",
            f"resource.labels.service_name={self.service_name}",
            f"resource.labels.location={self.region}",
        ]
        
        # Add severity filter
        if len(severity_levels) == 1:
            filter_parts.append(f"severity={severity_levels[0]}")
        elif len(severity_levels) > 1:
            severity_filter = " OR ".join([f"severity={sev}" for sev in severity_levels])
            filter_parts.append(f"({severity_filter})")
        
        # Add time range
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        filter_parts.append(f'timestamp>="{start_time_str}"')
        filter_parts.append(f'timestamp<="{end_time_str}"')
        
        # Add search keyword if provided
        if search_keyword:
            filter_parts.append(f'textPayload:"{search_keyword}"')
        
        return " AND ".join(filter_parts), start_time, end_time
    
    def fetch_logs(self, hours=2, severity_levels=None, search_keyword=None, limit=500):
        """Fetch logs from GCP Cloud Logging."""
        if severity_levels is None:
            severity_levels = ["ERROR", "WARNING"]
        
        print(f"🔍 Fetching {', '.join(severity_levels)} logs from last {hours} hour(s)...")
        
        log_filter, start_time, end_time = self.build_log_filter(hours, severity_levels, search_keyword)
        
        cmd = [
            "gcloud", "logging", "read",
            log_filter,
            f"--limit={limit}",
            "--format=json",
            f"--project={self.project_id}",
            "--freshness=1d"  # Look back up to 1 day for logs
        ]
        
        try:
            print(f"📡 Running: gcloud logs read (with {len(severity_levels)} severity filters)")
            if search_keyword:
                print(f"🔎 Searching for keyword: '{search_keyword}'")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not result.stdout.strip():
                print("📭 No logs found matching the criteria.")
                return [], start_time, end_time
            
            logs = json.loads(result.stdout)
            print(f"📦 Found {len(logs)} log entries")
            return logs, start_time, end_time
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error fetching logs: {e}")
            if e.stderr:
                print(f"Error details: {e.stderr}")
            return [], start_time, end_time
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing log response: {e}")
            return [], start_time, end_time
    
    def format_log_entry(self, log_entry):
        """Format a single log entry for display."""
        timestamp = log_entry.get('timestamp', 'N/A')
        severity = log_entry.get('severity', 'UNKNOWN')
        
        # Get the main text content
        text_payload = log_entry.get('textPayload', '')
        json_payload = log_entry.get('jsonPayload', {})
        
        # Format timestamp for display
        try:
            if timestamp != 'N/A':
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_display = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            else:
                timestamp_display = timestamp
        except ValueError:
            timestamp_display = timestamp
        
        # Get HTTP request info if available
        http_request = log_entry.get('httpRequest', {})
        request_url = http_request.get('requestUrl', '')
        status_code = http_request.get('status', '')
        
        # Format the log entry
        formatted_entry = f"[{timestamp_display}] {severity}"
        
        if status_code:
            formatted_entry += f" {status_code}"
        
        if request_url:
            formatted_entry += f" {request_url}"
        
        formatted_entry += "\n"
        
        if text_payload:
            # Clean up text payload
            text_payload = text_payload.strip()
            formatted_entry += f"  {text_payload}\n"
        elif json_payload:
            formatted_entry += f"  {json.dumps(json_payload, indent=2)}\n"
        
        return formatted_entry
    
    def analyze_logs(self, logs):
        """Analyze logs and provide summary."""
        if not logs:
            return {
                'total_count': 0,
                'severity_counts': {},
                'error_patterns': {},
                'recent_errors': []
            }
        
        severity_counts = {}
        error_patterns = {}
        recent_errors = []
        
        for log_entry in logs:
            severity = log_entry.get('severity', 'UNKNOWN')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            text_payload = log_entry.get('textPayload', '')
            
            # Analyze error patterns
            if severity in ['ERROR', 'CRITICAL']:
                if 'BuildError' in text_payload:
                    error_patterns['Blueprint URL Build Error'] = error_patterns.get('Blueprint URL Build Error', 0) + 1
                elif 'ImportError' in text_payload or 'ModuleNotFoundError' in text_payload:
                    error_patterns['Import Error'] = error_patterns.get('Import Error', 0) + 1
                elif 'Firebase' in text_payload or 'Firestore' in text_payload:
                    error_patterns['Firebase/Firestore Error'] = error_patterns.get('Firebase/Firestore Error', 0) + 1
                elif 'SystemExit' in text_payload:
                    error_patterns['System Exit'] = error_patterns.get('System Exit', 0) + 1
                elif 'my-links' in text_payload.lower():
                    error_patterns['My Links Page Error'] = error_patterns.get('My Links Page Error', 0) + 1
                else:
                    error_patterns['Other Error'] = error_patterns.get('Other Error', 0) + 1
                
                # Collect recent errors for detailed view
                if len(recent_errors) < 10:  # Keep last 10 errors
                    recent_errors.append({
                        'timestamp': log_entry.get('timestamp', 'N/A'),
                        'severity': severity,
                        'text': text_payload[:300] + '...' if len(text_payload) > 300 else text_payload
                    })
        
        return {
            'total_count': len(logs),
            'severity_counts': severity_counts,
            'error_patterns': error_patterns,
            'recent_errors': recent_errors
        }
    
    def save_logs(self, logs, start_time, end_time, severity_levels, search_keyword=None, save_json=False):
        """Save logs to file with header information."""
        timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        # Generate filename
        base_filename = f"logs_{timestamp_str}"
        if search_keyword:
            safe_keyword = "".join(c for c in search_keyword if c.isalnum() or c in ('-', '_'))
            base_filename += f"_{safe_keyword}"
        
        txt_file = self.temp_logs_dir / f"{base_filename}.txt"
        
        # Create header
        header = f"""=== CLOUD RUN LOGS ===
Project: {self.project_id} ({self.project_number})
Service: {self.service_name}
Region: {self.region}
Service URL: {self.service_url}
Time Range: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} to {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}
Severity: {', '.join(severity_levels)}
Search Keyword: {search_keyword or 'None'}
Total Entries: {len(logs)}
Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
=====================================

"""
        
        # Write text log file
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(header)
            
            if not logs:
                f.write("No logs found matching the criteria.\n")
            else:
                # Sort logs by timestamp (newest first)
                sorted_logs = sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)
                
                for log_entry in sorted_logs:
                    formatted_entry = self.format_log_entry(log_entry)
                    f.write(formatted_entry)
                    f.write("\n" + "-" * 80 + "\n\n")
        
        print(f"📝 Text logs saved to: {txt_file}")
        
        # Save JSON file if requested
        if save_json and logs:
            json_file = self.temp_logs_dir / f"{base_filename}.json"
            log_data = {
                'metadata': {
                    'project_id': self.project_id,
                    'project_number': self.project_number,
                    'service_name': self.service_name,
                    'region': self.region,
                    'service_url': self.service_url,
                    'time_range': {
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat()
                    },
                    'severity_levels': severity_levels,
                    'search_keyword': search_keyword,
                    'total_entries': len(logs),
                    'generated_at': datetime.now(timezone.utc).isoformat()
                },
                'logs': logs
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            
            print(f"📝 JSON logs saved to: {json_file}")
        
        return txt_file
    
    def print_analysis(self, analysis):
        """Print log analysis summary to console."""
        print("\n" + "=" * 60)
        print("📊 LOG ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"\n📈 Total Log Entries: {analysis['total_count']}")
        
        if analysis['severity_counts']:
            print("\n🎯 Severity Breakdown:")
            for severity, count in sorted(analysis['severity_counts'].items()):
                print(f"  {severity}: {count}")
        
        if analysis['error_patterns']:
            print("\n🚨 Error Pattern Analysis:")
            for pattern, count in sorted(analysis['error_patterns'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {pattern}: {count}")
        
        if analysis['recent_errors']:
            print(f"\n📝 Recent Errors (showing {len(analysis['recent_errors'])}):")
            for i, error in enumerate(analysis['recent_errors'][:5], 1):  # Show top 5
                timestamp = error['timestamp']
                try:
                    if timestamp != 'N/A':
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamp_display = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        timestamp_display = timestamp
                except ValueError:
                    timestamp_display = timestamp
                
                print(f"\n  {i}. [{timestamp_display}] {error['severity']}")
                print(f"     {error['text'][:150]}{'...' if len(error['text']) > 150 else ''}")
        
        # Provide specific recommendations
        print("\n💡 RECOMMENDATIONS:")
        patterns = analysis['error_patterns']
        if patterns.get('Blueprint URL Build Error', 0) > 0:
            print("  ⚠️  Fix blueprint endpoint references (auth_bp.login → auth.login)")
        if patterns.get('Firebase/Firestore Error', 0) > 0:
            print("  ⚠️  Check Firebase credentials and initialization")
        if patterns.get('Import Error', 0) > 0:
            print("  ⚠️  Check import statements and module availability")
        if patterns.get('My Links Page Error', 0) > 0:
            print("  ⚠️  Investigate My Links page specific issues")
        if not any(patterns.values()):
            print("  ✅ No common error patterns detected")


def main():
    """Main function to handle command line arguments and execute log fetching."""
    parser = argparse.ArgumentParser(
        description="Fetch GCP Cloud Run logs for Phoenix app",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/fetch_logs.py                     # Last 2 hours, ERROR + WARNING
  python scripts/fetch_logs.py --hours 6           # Last 6 hours
  python scripts/fetch_logs.py --severity ERROR    # Only ERROR logs
  python scripts/fetch_logs.py --search "my-links" # Filter by keyword
  python scripts/fetch_logs.py --save-json         # Also save as JSON
        """
    )
    
    parser.add_argument(
        '--hours', 
        type=int, 
        default=2,
        help='Number of hours to look back for logs (default: 2)'
    )
    
    parser.add_argument(
        '--severity',
        choices=['ERROR', 'WARNING', 'INFO', 'DEBUG'],
        action='append',
        help='Severity levels to include (can be used multiple times, default: ERROR and WARNING)'
    )
    
    parser.add_argument(
        '--search',
        type=str,
        help='Search for specific keyword in log messages'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=500,
        help='Maximum number of log entries to fetch (default: 500)'
    )
    
    parser.add_argument(
        '--save-json',
        action='store_true',
        help='Also save logs in JSON format'
    )
    
    parser.add_argument(
        '--no-analysis',
        action='store_true',
        help='Skip log analysis and just save raw logs'
    )
    
    args = parser.parse_args()
    
    # Default severity levels
    if not args.severity:
        args.severity = ['ERROR', 'WARNING']
    
    # Initialize log fetcher
    fetcher = CloudRunLogFetcher()
    
    # Check authentication
    if not fetcher.check_gcloud_auth():
        sys.exit(1)
    
    print(f"🚀 Phoenix GCP Log Fetcher")
    print(f"Project: {fetcher.project_id}")
    print(f"Service: {fetcher.service_name}")
    print(f"Region: {fetcher.region}")
    print()
    
    # Fetch logs
    logs, start_time, end_time = fetcher.fetch_logs(
        hours=args.hours,
        severity_levels=args.severity,
        search_keyword=args.search,
        limit=args.limit
    )
    
    if not logs:
        print("✅ No logs found. This might be good news!")
        return
    
    # Analyze logs
    if not args.no_analysis:
        analysis = fetcher.analyze_logs(logs)
        fetcher.print_analysis(analysis)
    
    # Save logs
    saved_file = fetcher.save_logs(
        logs, 
        start_time, 
        end_time, 
        args.severity,
        search_keyword=args.search,
        save_json=args.save_json
    )
    
    print(f"\n✅ Log fetching completed!")
    print(f"📁 Logs saved to: {saved_file}")
    
    if not args.no_analysis and analysis['error_patterns']:
        print(f"\n🔍 Found {analysis['total_count']} log entries with {len(analysis['error_patterns'])} error patterns")


if __name__ == "__main__":
    main()
