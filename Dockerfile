# Production-grade multi-stage Dockerfile for Next.js Standalone
FROM node:20.12-alpine AS base

# Phase 1: Install dependencies
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install dependencies based on the preferred package manager
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Phase 2: Rebuild the source code
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .

# Disable telemetry during build
ENV NEXT_TELEMETRY_DISABLED 1

RUN npm run build

# Phase 3: Production image, copy all the files and run next
FROM node:20.12-bookworm-slim AS runner
# Install uv and system dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Automatically leverage output traces to reduce image size
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Copy backend files
COPY backend ./backend
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Install Python 3.12 and sync dependencies using uv
WORKDIR /app/backend
RUN uv python install 3.12
RUN uv sync --frozen --no-dev

WORKDIR /app

EXPOSE 3000
EXPOSE 8000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# Use the unified start script
CMD ["./start.sh"]
