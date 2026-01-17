"""
GitHub Issue Creator for Cloud Monitoring Alerts
=================================================

This Cloud Function receives alerts via Pub/Sub and creates GitHub issues
for CRITICAL alerts that require immediate attention.

Triggered by: Pub/Sub topic 'phoenix-alerts'
Creates: GitHub issues in the configured repository

Environment Variables:
- GITHUB_TOKEN: GitHub Personal Access Token with 'repo' scope
- GITHUB_REPO: Repository in format 'owner/repo' (e.g., 'friedmomo/phoenix')

Deployment:
-----------
gcloud functions deploy github-alert-handler \
    --gen2 \
    --runtime=python311 \
    --region=us-central1 \
    --source=functions/github-alert \
    --entry-point=handle_alert \
    --trigger-topic=phoenix-alerts \
    --set-env-vars=GITHUB_REPO=friedmomo/phoenix \
    --set-secrets=GITHUB_TOKEN=github-token:latest

Author: Friedmomo Engineering
"""

import base64
import json
import logging
import os
from datetime import datetime

import functions_framework
import requests

logger = logging.getLogger(__name__)

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'friedmomo/phoenix')
GITHUB_API_URL = f'https://api.github.com/repos/{GITHUB_REPO}/issues'

# Only create issues for these severity levels
ISSUE_WORTHY_SEVERITIES = ['CRITICAL']


@functions_framework.cloud_event
def handle_alert(cloud_event):
    """
    Handle incoming Cloud Monitoring alert via Pub/Sub.

    Args:
        cloud_event: CloudEvent containing the alert data
    """
    try:
        # Decode the Pub/Sub message
        message_data = base64.b64decode(cloud_event.data['message']['data']).decode('utf-8')
        alert_data = json.loads(message_data)

        logger.info(f"Received alert: {json.dumps(alert_data, indent=2)}")

        # Extract relevant information
        incident = alert_data.get('incident', {})
        policy_name = incident.get('policy_name', 'Unknown Policy')
        condition_name = incident.get('condition_name', 'Unknown Condition')
        state = incident.get('state', 'unknown')
        summary = incident.get('summary', 'No summary available')
        url = incident.get('url', '')

        # Only create issues for OPENED incidents with CRITICAL in the name
        if state != 'open':
            logger.info(f"Skipping alert - state is '{state}', not 'open'")
            return {'status': 'skipped', 'reason': f'state is {state}'}

        if 'CRITICAL' not in policy_name.upper():
            logger.info(f"Skipping alert - not CRITICAL severity")
            return {'status': 'skipped', 'reason': 'not critical'}

        # Create GitHub issue
        issue = create_github_issue(
            policy_name=policy_name,
            condition_name=condition_name,
            summary=summary,
            incident_url=url,
            raw_data=alert_data
        )

        if issue:
            logger.info(f"Created GitHub issue: {issue.get('html_url')}")
            return {'status': 'created', 'issue_url': issue.get('html_url')}
        else:
            logger.error("Failed to create GitHub issue")
            return {'status': 'error', 'reason': 'github_api_failed'}

    except Exception as e:
        logger.error(f"Error processing alert: {e}", exc_info=True)
        return {'status': 'error', 'reason': str(e)}


def create_github_issue(policy_name, condition_name, summary, incident_url, raw_data):
    """
    Create a GitHub issue for the alert.

    Args:
        policy_name: Name of the alerting policy
        condition_name: Name of the condition that triggered
        summary: Alert summary text
        incident_url: Link to the GCP incident
        raw_data: Full alert payload for debugging

    Returns:
        GitHub API response or None on failure
    """
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN not configured")
        return None

    # Format issue title
    title = f"[ALERT] {policy_name}"

    # Format issue body
    body = f"""## Cloud Monitoring Alert

**Policy:** {policy_name}
**Condition:** {condition_name}
**Triggered At:** {datetime.utcnow().isoformat()}Z

### Summary
{summary}

### Actions Required
1. Check the GCP logs for detailed error information
2. Investigate and resolve the root cause
3. Close this issue once resolved

### Links
- [View Incident in GCP]({incident_url})
- [View Logs](https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%20textPayload%3D~%22DELETION_ALERT%22?project=phoenix-project-386)

### Debug Information
<details>
<summary>Raw Alert Data</summary>

```json
{json.dumps(raw_data, indent=2)}
```

</details>

---
*This issue was automatically created by the phoenix-alerts system.*
"""

    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Phoenix-Alert-Bot'
    }

    payload = {
        'title': title,
        'body': body,
        'labels': ['alert', 'critical', 'automated']
    }

    try:
        response = requests.post(GITHUB_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        return None
