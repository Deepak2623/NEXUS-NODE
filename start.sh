#!/bin/bash
# Root-level entrypoint for Railpack/PaaS monorepo detection.
# 
# To use this: 
# 1. Set the environment variable SERVICE_TYPE="backend" or "frontend" in your PaaS settings.
# 2. Alternatively (Recommended), set the 'rootDirectory' in your PaaS settings to 'backend' or 'frontend'.

set -e

if [ "$SERVICE_TYPE" == "backend" ]; then
    echo "Starting backend..."
    cd backend
    # Fallback to local run command if not in Docker
    if command -v uv &> /dev/null; then
        exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
    else
        exec uvicorn main:app --host 0.0.0.0 --port 8000
    fi
elif [ "$SERVICE_TYPE" == "frontend" ]; then
    echo "Starting frontend..."
    cd frontend
    exec npm run start
else
    echo "--------------- HELP ---------------"
    echo "No SERVICE_TYPE environment variable specified."
    echo ""
    echo "To deploy this monorepo:"
    echo "1. Recommend setting the Service Root Directory in your hosting provider's dashboard:"
    echo "   - Root: backend (for FastAPI)"
    echo "   - Root: frontend (for Next.js)"
    echo ""
    echo "2. Or set SERVICE_TYPE to 'backend' or 'frontend'."
    echo "------------------------------------"
    exit 1
fi
