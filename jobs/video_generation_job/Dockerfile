# Video Generation Job - Cloud Run Job Container
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (ffmpeg for thumbnail extraction)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy main app requirements (we need all services)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy services (needed for Veo, Firestore, etc.)
COPY services/ /app/services/
COPY config/ /app/config/

# Copy job-specific code
COPY jobs/video_generation_job/ /app/jobs/video_generation_job/

# Set environment variables
ENV JOB_TYPE=video_generation
ENV MAX_MEMORY_GB=4
ENV TIMEOUT_MINUTES=10
ENV PYTHONPATH="/app"

# Create temp directory
RUN mkdir -p /tmp/jobs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Resource limits awareness
ENV MEMORY_LIMIT_GB=4
ENV CPU_LIMIT=2

# Run the job
CMD ["python", "/app/jobs/video_generation_job/main.py"]
