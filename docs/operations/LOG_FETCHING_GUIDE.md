# GCP Log Fetching Script

## Overview
This script fetches ERROR and WARNING logs from the Phoenix Cloud Run service for local analysis.

## Project Details
- **Project ID**: phoenix-project-386
- **Project Number**: 234619602247  
- **Service**: phoenix
- **Region**: us-central1
- **URL**: https://phoenix-234619602247.us-central1.run.app

## Auto-Deployment
The project uses **automatic deployment via GitHub sync** to Google Cloud Platform. No manual deployment commands needed - changes are automatically deployed when pushed to the repository.

## Prerequisites
1. Install Google Cloud CLI: https://cloud.google.com/sdk/docs/install
2. Authenticate: `gcloud auth login`
3. Install dependencies: `pip install -r requirements.txt`

## Usage

### Basic Commands
```bash
# Fetch last 2 hours of ERROR and WARNING logs
python scripts/fetch_logs.py

# Fetch last 6 hours of logs
python scripts/fetch_logs.py --hours 6

# Fetch only ERROR logs
python scripts/fetch_logs.py --severity ERROR

# Search for specific keyword
python scripts/fetch_logs.py --search "my-links"

# Save logs in both text and JSON format
python scripts/fetch_logs.py --save-json

# Fetch more logs (default limit is 500)
python scripts/fetch_logs.py --limit 1000
```

### Advanced Examples
```bash
# Debug the "My Shortened Links" page issue
python scripts/fetch_logs.py --search "my-links" --hours 4

# Get all error logs from last day
python scripts/fetch_logs.py --severity ERROR --hours 24

# Search for authentication issues
python scripts/fetch_logs.py --search "auth" --hours 6
```

## Output
Logs are saved to `temp_logs/` directory with the following format:
- **Text file**: `logs_YYYY-MM-DD_HH-MM-SS.txt` - Human readable format
- **JSON file**: `logs_YYYY-MM-DD_HH-MM-SS.json` - Machine readable format (when `--save-json` is used)

## Log Analysis
The script automatically analyzes logs and provides:
- Severity breakdown (ERROR, WARNING counts)
- Error pattern recognition (Blueprint errors, Firebase errors, etc.)
- Recent error summaries
- Specific recommendations for common issues

## Files Structure
```
temp_logs/                    # Log files (gitignored)
├── .gitkeep                 # Keeps directory in repo
├── logs_2025-06-14_15-30-45.txt
└── logs_2025-06-14_15-30-45.json

scripts/
├── __init__.py
└── fetch_logs.py            # Main log fetching script
```

## Troubleshooting

### gcloud not found
```bash
# Install Google Cloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

### Authentication issues
```bash
gcloud auth login
gcloud config set project phoenix-project-386
```

### No logs found
- Check if the time range is correct (try increasing `--hours`)
- Verify the service is receiving traffic
- Check if you have the correct project permissions
