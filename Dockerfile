# Use astral-sh uv image directly
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Enable bytecode compilation and use copy mode for uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency files only (from the backend folder)
COPY backend/uv.lock backend/pyproject.toml /app/

# Install dependencies using standard COPY (no mounts to avoid host errors)
RUN uv sync --frozen --no-install-project --no-dev

# Add the backend code
COPY backend /app/

# Final sync to install the project itself
RUN uv sync --frozen --no-dev

# Final runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the virtual environment and app from the builder
COPY --from=builder /app /app

# Ensure the virtualenv is used by default
ENV PATH="/app/.venv/bin:$PATH"

# Expose FastAPI port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
