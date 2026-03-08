#!/bin/zsh

# Nexus Dev Run Script
# This runs both backend and frontend simultaneously.

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "${BLUE}🧹 Cleaning up existing processes on 3000 and 8000...${NC}"
lsof -ti:3000,8000 | xargs kill -9 2>/dev/null
sleep 1

# Check for .env files
if [ ! -f "backend/.env" ]; then
    echo "${RED}❌ backend/.env is missing. Please create it from .env.example.${NC}"
    exit 1
fi

# Trap to kill all sub-processes on exit
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

echo "${GREEN}🚀 Starting Backend (uvicorn on :8000)...${NC}"
(cd backend && uv run --python 3.12 uvicorn main:app --reload --port 8000) &

echo "${GREEN}🚀 Starting Frontend (next dev on :3000)...${NC}"
(cd frontend && npm run dev) &

# Keep script running
wait
