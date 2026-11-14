# ==============================================================================
# Multi-stage Dockerfile for PII Detection & Secure Redaction Backend
# Reproducible build with security hardening (non-root user, minimal layers)
# ==============================================================================

# Stage 1: Build & wheels preparation
FROM python:3.11-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /install

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install/prefix -r requirements.txt

# Stage 2: Final runtime container
FROM python:3.11-slim AS runner

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_PORT=8000 \
    PATH="/usr/local/bin:${PATH}"

# Install minimal system libraries for PDF rendering and OCR tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    tesseract-ocr-vie \
    tesseract-ocr-eng \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user (appuser:appgroup, uid 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Copy python packages from builder
COPY --from=builder /install/prefix /usr/local

# Setup persistent directory structure with restricted permissions
RUN mkdir -p /app/storage/private /app/storage/temp /app/logs /app/checkpoints && \
    chown -R appuser:appgroup /app && \
    chmod -R 750 /app/storage

# Copy codebase
COPY --chown=appuser:appgroup . /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "config.health"]
