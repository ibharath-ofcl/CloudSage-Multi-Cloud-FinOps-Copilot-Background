# syntax=docker/dockerfile:1.4
# ==============================================================================
# CloudSage Backend Multi-Stage Production Dockerfile
# Stage 1: Build dependency wheels and virtual environment
# Stage 2: Hardened, minimal, non-root production runtime container
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder
# ------------------------------------------------------------------------------
FROM python:3.13-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build-time system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv and install Python dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.13-slim AS production

LABEL maintainer="CloudSage FinOps Team <devops@cloudsage.internal>" \
      description="CloudSage Multi-Cloud FinOps Copilot Backend Service" \
      version="0.15.0"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    ENVIRONMENT=production \
    PORT=8000

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user and group (UID 10001)
RUN groupadd -g 10001 cloudsage && \
    useradd -u 10001 -g cloudsage -s /bin/bash -m cloudsage

WORKDIR /app

# Copy isolated virtualenv from builder stage
COPY --from=builder --chown=cloudsage:cloudsage /opt/venv /opt/venv

# Prepare directory structure with correct ownership
RUN mkdir -p /app/backend /backups && \
    chown -R cloudsage:cloudsage /app /backups

# Copy application source code
COPY --chown=cloudsage:cloudsage . /app/backend/

# Ensure entrypoint and maintenance scripts are executable and symlinked
RUN chmod +x /app/backend/scripts/*.sh && \
    ln -s /app/backend/scripts /app/scripts && \
    ln -s /app/backend/alembic.ini /app/alembic.ini

# Switch to unprivileged non-root user
USER cloudsage:cloudsage

EXPOSE 8000

# Health check using liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/liveness || exit 1

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "120", "backend.app.main:app"]
