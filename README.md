# Phoenix - Simple Flask Website

A minimalist Flask web application deployed on Google Cloud Run.

## Live Demo

Visit the live application at: https://phoenix-234619602247.us-central1.run.app

## Development Workflow

### Local Testing

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/phoenix.git
   cd phoenix
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create an `.env` file with necessary API keys (see `.env.example` for required variables)

4. Run the application locally:
   ```
   ./start_local.sh
   ```
   This script will free up port 8080 if needed and start the application.

5. Visit `http://localhost:8080` in your browser to test the application.

### Deployment

Deployment happens automatically through GitHub integration with Google Cloud Build. Simply push your changes to the main branch:

```
git add .
git commit -m "Your commit message"
git push origin main
```

The application will be automatically built and deployed to Google Cloud Run.

## Notes for AI Assistants

- Use `./start_local.sh` to test the application locally (runs on port 8080)
- Local testing workflow: run local script → verify at localhost:8080 → then deploy
- This project is automatically deployed through GitHub integration with Google Cloud Build
- DO NOT suggest manual deployment steps - all deployments happen automatically on GitHub push
- The project uses Google Secret Manager for API keys and secrets
- Secrets are mounted through Cloud Run's `--update-secrets` flag in cloudbuild.yaml