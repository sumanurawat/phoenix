# Phoenix - Simple Flask Website

A minimalist Flask web application deployed on Google Cloud Run.

## Live Demo

Visit the live application at: https://phoenix-234619602247.us-central1.run.app

## Notes for AI Assistants

- This project is automatically deployed through GitHub integration with Google Cloud Build
- DO NOT suggest manual deployment steps - all deployments happen automatically on GitHub push
- The project uses Google Secret Manager for API keys and secrets
- Secrets are mounted through Cloud Run's `--update-secrets` flag in cloudbuild.yaml