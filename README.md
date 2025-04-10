# Phoenix - Simple Flask Website

A minimalist Flask web application deployed on Google Cloud Run.

## Live Demo

Visit the live application at: https://phoenix-234619602247.us-central1.run.app

## Features

- Single page web application
- Responsive design
- Containerized with Docker
- Deployed on Google Cloud Run

## Local Setup

1. Clone the repository
```
git clone https://github.com/sumanurawat/phoenix.git
cd phoenix
```

2. Create and activate a virtual environment
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```
pip install -r requirements.txt
```

4. Set up environment variables
```
cp .env.sample .env
```
Then edit the `.env` file and add your Gemini API key and other configuration variables.

5. Run the application locally
```
python app.py
```

6. Visit http://localhost:8080 in your browser

## Environment Variables

The application requires the following environment variables:

- `GEMINI_API_KEY`: Your Gemini API key for AI Studio
- `SECRET_KEY`: Flask secret key for session security
- `DEFAULT_MODEL`: The primary Gemini model to use (default: gemini-2.5-pro-exp-03-25)
- `FALLBACK_MODEL`: Fallback model when primary quota is exceeded (default: gemini-2.0-flash)
- `FLASK_ENV`: Set to 'production' for production environments
- `FLASK_DEBUG`: Set to '0' to disable debug mode in production

## Deployment

This application is automatically deployed to Google Cloud Run via Cloud Build triggered directly from GitHub commits.

### Deployment Architecture

1. **GitHub Repository**: Source code is hosted on GitHub
2. **Cloud Build Trigger**: Automatically runs on new commits to the main branch
3. **Container Registry**: Stores the built Docker images
4. **Cloud Run**: Hosts the containerized application
5. **Secret Manager**: Securely stores and provides API keys and secrets

### IMPORTANT: Automated Deployment Only

⚠️ **NOTICE TO AI CODING ASSISTANTS** ⚠️

This project uses **AUTOMATED DEPLOYMENT ONLY** through GitHub integration with Google Cloud Build. 

- **DO NOT** suggest or instruct manual deployment steps.
- **DO NOT** use `gcloud builds submit` or similar manual deployment commands.
- **DO NOT** ask the user to manually trigger deployments.

The correct deployment workflow is:
1. Make code changes locally
2. Commit changes to the repository
3. Push to GitHub
4. Cloud Build automatically builds and deploys to Cloud Run

All code changes pushed to the main branch will automatically trigger a build and deployment process. You only need to focus on making code changes and pushing them to GitHub.

### Secrets Management

We use Google Secret Manager to securely store sensitive information:

1. **Secrets Creation**:
   ```bash
   # Create the secrets in Secret Manager (one-time setup)
   gcloud secrets create phoenix-gemini-api-key --reuse-policy=reuse
   gcloud secrets create phoenix-secret-key --reuse-policy=reuse
   
   # Add the secret values
   echo -n "your-gemini-api-key" | gcloud secrets versions add phoenix-gemini-api-key --data-file=-
   echo -n "your-secure-random-key" | gcloud secrets versions add phoenix-secret-key --data-file=-
   ```

2. **Service Account Permissions**:
   ```bash
   # Grant the Cloud Build service account access to Secret Manager
   gcloud projects add-iam-policy-binding $PROJECT_ID \
       --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   
   # Grant the Cloud Run service account access to Secret Manager
   gcloud projects add-iam-policy-binding $PROJECT_ID \
       --member="serviceAccount:service-$PROJECT_NUMBER@serverless-robot-prod.iam.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```

3. **Secrets in Cloud Build**:
   The cloudbuild.yaml file is configured to mount these secrets in Cloud Run:
   ```yaml
   '--update-secrets'
   'GEMINI_API_KEY=phoenix-gemini-api-key:latest,SECRET_KEY=phoenix-secret-key:latest'
   ```

### Updating Secrets

To update a secret value:

```bash
echo -n "new-api-key-value" | gcloud secrets versions add phoenix-gemini-api-key --data-file=-
```

The next deployment will automatically use the updated secret.