#!/bin/sh
# NEXUS-NODE Emergency Unified Start Script

echo "Starting FastAPI Backend..."
export PATH="/opt/venv/bin:$PATH"
cd /app/backend
uvicorn main:app --host 0.0.0.0 --port 8000 &

echo "Starting Next.js Frontend..."
cd /app
node server.js
