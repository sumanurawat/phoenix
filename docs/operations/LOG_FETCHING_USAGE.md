# Phoenix Log Fetching Script - Usage Guide

## ✅ Setup Complete

Your Google Cloud CLI is installed and authenticated. The log fetching script is working perfectly!

## 🚀 Quick Start

```bash
# Basic usage - get last 2 hours of ERROR and WARNING logs
python scripts/fetch_logs.py

# Get last 6 hours of logs
python scripts/fetch_logs.py --hours 6

# Get only ERROR logs
python scripts/fetch_logs.py --severity ERROR

# Search for specific keywords
python scripts/fetch_logs.py --search "auth_bp.login"

# Save logs in both text and JSON format
python scripts/fetch_logs.py --save-json

# Get more logs (up to 1000)
python scripts/fetch_logs.py --limit 1000
```

## 📊 Current Issues Found

The script has identified a critical issue in your Phoenix app:

**Blueprint URL Building Error**: 
- **File**: `/app/api/deeplink_routes.py` (line 25)
- **Issue**: Using `'auth_bp.login'` instead of `'auth.login'`
- **Error**: `werkzeug.routing.exceptions.BuildError: Could not build url for endpoint 'auth_bp.login'`
- **Fix**: Change `auth_bp.login` to `auth.login` in the redirect call

## 📁 Log Storage

Logs are saved in: `/Users/sumanurawat/Documents/GitHub/phoenix/temp_logs/`

## 🔧 Available Options

| Option | Description | Example |
|--------|-------------|---------|
| `--hours` | Hours to look back (default: 2) | `--hours 24` |
| `--severity` | Log severity (ERROR, WARNING, INFO, DEBUG) | `--severity ERROR` |
| `--search` | Keyword search | `--search "auth_bp"` |
| `--limit` | Max entries (default: 500) | `--limit 1000` |
| `--save-json` | Also save JSON format | `--save-json` |
| `--no-analysis` | Skip analysis, raw logs only | `--no-analysis` |

## 📈 Features

- ✅ **Authentication Check**: Verifies gcloud is authenticated
- ✅ **Smart Filtering**: Filters by severity, time range, and keywords
- ✅ **Log Analysis**: Identifies error patterns and provides recommendations
- ✅ **Multiple Formats**: Saves in both human-readable text and JSON
- ✅ **Project Configuration**: Pre-configured for your Phoenix project
- ✅ **Error Categorization**: Groups similar errors for easier debugging

## 🐛 Next Steps

1. Fix the blueprint reference issue in `deeplink_routes.py`
2. Run the script regularly to monitor for new issues
3. Use the search feature to investigate specific problems
