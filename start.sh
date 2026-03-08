#!/bin/bash
# Root-level entrypoint for Railpack/PaaS monorepo detection.
# 
# To use this: 
# 1. Set the environment variable SERVICE_TYPE="backend" or "frontend" in your PaaS settings.
# 2. Alternatively (Recommended), set the 'rootDirectory' in your PaaS settings to 'backend' or 'frontend'.

set -e

if [ "$SERVICE_TYPE" == "frontend" ]; then
    echo "Starting frontend..."
    cd frontend
    exec npm run start
else
    # Default to backend if SERVICE_TYPE is "backend" or unset
    echo "Starting backend (default)..."
    cd backend
    if command -v uv &> /dev/null; then
        exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
    else
        exec uvicorn main:app --host 0.0.0.0 --port 8000
    fi
fi
