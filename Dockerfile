FROM python:3.9-slim

WORKDIR /app

# Install FFmpeg for video stitching
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default environment variables (can be overridden at runtime)
ENV PORT=8080
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV DEFAULT_MODEL=gemini-1.5-flash-8b
ENV FALLBACK_MODEL=gemini-1.5-flash

# The API key should be provided at runtime, not baked into the image
# GEMINI_API_KEY will be injected at runtime

# Timeout increased to 3600s (60 min) to handle long-running video generation
# Each video can take 60-120s, and we might generate 15+ videos sequentially
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 3600 app:app