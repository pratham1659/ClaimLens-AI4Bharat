# backend/Dockerfile
# Multi-stage Dockerfile for ClaimLens Backend
# Supports both LOCAL (development) and PROD (production) builds
#
# Build targets:
#   local - Development with hot-reload, local embeddings (~1.5GB)
#   prod  - Production with AWS Bedrock (no local ML) (~800MB)
#
# Image sizes (optimized):
#   local: ~1.5GB (with PyTorch CPU-only + sentence-transformers)
#   prod:  ~800MB (no PyTorch, uses AWS Bedrock for embeddings)

# ============================================
# BASE STAGE - Common dependencies
# ============================================
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ============================================
# PROD-DEPS STAGE - Production dependencies only
# ============================================
FROM base AS prod-deps

# Copy only base requirements (no ML dependencies)
COPY requirements-base.txt .

# Install production dependencies (no PyTorch)
RUN pip install --no-cache-dir -r requirements-base.txt

# Install lightweight rag-system ingestion/indexing dependencies used by
# /api/v1/policies/preindexed/ingest endpoint.
RUN pip install --no-cache-dir \
    faiss-cpu>=1.7.4 \
    pandas>=2.1.0 \
    pyarrow>=14.0.0

# Install LangChain without heavy ML deps
RUN pip install --no-cache-dir \
    langchain>=0.1.0 \
    langchain-aws>=0.1.0 \
    langchain-core>=0.1.0 \
    langchain-text-splitters>=0.0.1

# ============================================
# LOCAL-DEPS STAGE - Development with ML
# ============================================
FROM base AS local-deps

# HuggingFace cache directories (for local embedding models)
ENV HF_HOME=/app/models
ENV TRANSFORMERS_CACHE=/app/models
ENV TORCH_HOME=/app/models

# Copy requirements files
COPY requirements-base.txt .
COPY requirements-ml.txt .

# Install base dependencies first (better layer caching)
RUN pip install --no-cache-dir -r requirements-base.txt

# Install PyTorch CPU-only version (much smaller than full PyTorch)
# This reduces image size from ~2.5GB to ~1.5GB
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install ML dependencies
RUN pip install --no-cache-dir -r requirements-ml.txt

# Create directories for models and indexes
RUN mkdir -p /app/models /app/logs /app/faiss_claimlens_index /app/faiss_claimlens_combined_index

# ============================================
# LOCAL STAGE - Development build (~1.5GB)
# ============================================
FROM local-deps AS local

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy application code (will be overridden by volume mount in dev)
COPY . .

# Create non-root user but keep as root for easier dev file permissions
RUN groupadd -r appuser && useradd -r -g appuser appuser || true
RUN chown -R appuser:appuser /app 2>/dev/null || true

EXPOSE 8000

# Development command with hot-reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================
# PROD STAGE - Production build (~800MB)
# ============================================
FROM prod-deps AS prod

# Copy application code
COPY . .

# Create non-root user and set permissions
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user for security
USER appuser

# Create necessary directories
RUN mkdir -p /app/logs

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command (no reload, optimized)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
