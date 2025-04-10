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

4. Run the application locally
```
python app.py
```

5. Visit http://localhost:8080 in your browser

## Deployment

This application is deployed on Google Cloud Run, which offers:

- Serverless container execution
- Auto-scaling to zero when not in use
- Pay-per-use pricing model
- Built-in HTTPS

The deployment is done through Google Cloud Build with a Dockerfile that sets up the Python environment and runs the application with Gunicorn.