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
FROM node:20.12-alpine AS runner
# Install Python, pip, and build essentials
RUN apk add --no-cache python3 py3-pip curl gcc musl-dev python3-dev

WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Create a virtualenv and install backend deps
COPY backend ./backend
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir ./backend

# Automatically leverage output traces to reduce image size
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Copy remaining backend files and start script
COPY backend ./backend
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

EXPOSE 3000
EXPOSE 8000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# Use the unified start script
CMD ["./start.sh"]
