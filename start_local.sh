#!/bin/bash

# Script to clean port 8080 and start the Phoenix AI Platform
echo "=== Phoenix AI Platform Startup ==="

# Check if .env file exists, warn if not
if [ ! -f .env ]; then
    echo "WARNING: .env file not found. Make sure your API keys are set."
fi

echo "Checking if port 8080 is in use..."

# Find processes using port 8080
PID=$(lsof -ti tcp:8080)

if [ -n "$PID" ]; then
    echo "Port 8080 is in use by process(es): $PID"
    echo "Killing process(es)..."
    kill -9 $PID
    echo "Process(es) killed."
else
    echo "Port 8080 is not in use."
fi

echo "Creating session directory if it doesn't exist..."
mkdir -p ./flask_session

echo "Starting Phoenix AI Platform..."
python app.py