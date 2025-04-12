#!/bin/bash

# Script to clean port 8080 and start the Phoenix AI Platform
echo "=== Phoenix AI Platform Startup ==="

# Check if .env file exists, warn if not
if [ ! -f .env ]; then
    echo "WARNING: .env file not found. Make sure your API keys are set."
fi

echo "Checking if port 8080 is in use..."

# Find processes using port 8080
PIDS=$(lsof -ti tcp:8080)

if [ -n "$PIDS" ]; then
    echo "Port 8080 is in use by process(es): $PIDS"
    echo "Killing process(es)..."
    # Process each PID separately
    for PID in $PIDS; do
        echo "Killing process $PID"
        kill -9 $PID
    done
    echo "Process(es) killed."
else
    echo "Port 8080 is not in use."
fi

echo "Creating session directory if it doesn't exist..."
mkdir -p ./flask_session

echo "Starting Phoenix AI Platform..."
python app.py