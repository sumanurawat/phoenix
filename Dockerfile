FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default environment variables
ENV PORT=8080
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV DEFAULT_MODEL=gemini-2.5-pro-exp-03-25
ENV FALLBACK_MODEL=gemini-2.0-flash

# The API key should be provided at runtime, not baked into the image
# GEMINI_API_KEY will be injected at runtime

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app