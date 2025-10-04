# Video Stitching Job - Cloud Run Job Container
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (from the job-specific requirements.txt)
COPY jobs/video_stitching/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared job framework
COPY jobs/shared/ /app/jobs/shared/
COPY jobs/base/ /app/jobs/base/

# Copy job-specific code
COPY jobs/video_stitching/ /app/jobs/video_stitching/

# Set environment variables
ENV JOB_TYPE=video_stitching
ENV MAX_MEMORY_GB=4
ENV TIMEOUT_MINUTES=15
ENV PYTHONPATH="/app:/app/jobs"

# Create temp directory
RUN mkdir -p /tmp/jobs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set resource limits awareness
ENV MEMORY_LIMIT_GB=4
ENV CPU_LIMIT=2

# Run the job
CMD ["python", "/app/jobs/video_stitching/main.py"]