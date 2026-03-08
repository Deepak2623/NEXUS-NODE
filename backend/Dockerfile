# Use a high-performance Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Enable bytecode compilation and use copy mode for uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies using uv.lock and pyproject.toml
# Using mounts to cache the uv cache directory between builds
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Add the rest of the application code
ADD . /app

# Final sync to install the project itself
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

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
