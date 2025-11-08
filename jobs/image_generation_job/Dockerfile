# Image Generation Job - Cloud Run Job Container (Small/Fast)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy main app requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy services (needed for ImageGenerationService, Firestore, etc.)
COPY services/ /app/services/
COPY config/ /app/config/

# Copy job-specific code
COPY jobs/image_generation_job/ /app/jobs/image_generation_job/

# Set environment variables
ENV JOB_TYPE=image_generation
ENV MAX_MEMORY_GB=1
ENV TIMEOUT_MINUTES=5
ENV PYTHONPATH="/app"

# Create temp directory
RUN mkdir -p /tmp/jobs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Resource limits awareness (small machine)
ENV MEMORY_LIMIT_GB=1
ENV CPU_LIMIT=1

# Run the job
CMD ["python", "/app/jobs/image_generation_job/main.py"]
