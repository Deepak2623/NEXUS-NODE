# Production Dockerfile for FastAPI Backend
FROM python:3.12-slim-bookworm

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (frozen for consistency)
RUN uv sync --frozen

# Copy source code
COPY . .

# Exposure
EXPOSE 8000

# Environment variables
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Start FastAPI via uvicorn
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
