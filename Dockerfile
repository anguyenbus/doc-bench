# Multi-stage Dockerfile for doc-bench
# Builder stage compiles dependencies, runtime stage contains minimal image

# ============================================================================
# BUILDER STAGE
# ============================================================================
FROM python:3.12-slim AS builder

# Build-time environment for optimization
ENV UV_COMPILE_BYTECODE=1 \
    PYTHONOPTIMIZE=2 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory for build
WORKDIR /build

# Copy dependency files for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (frozen lockfile for reproducibility)
RUN uv sync --frozen --no-dev

# ============================================================================
# DATASETS STAGE
# ============================================================================
FROM builder AS datasets

# Set working directory for data download
WORKDIR /opt/doc-bench

# Copy application code and scripts needed for dataset download
COPY --chown=root:root src /opt/doc-bench/src
COPY --chown=root:root scripts /opt/doc-bench/scripts

# Download DP-Bench and OmniDocBench English slices
# dp_bench: full dataset
# omnidocbench_english: nano (3), mini (10), medium (100), large (full)
RUN uv run python scripts/download_datasets.py \
    --datasets dp_bench omnidocbench \
    --omnidocbench-slices nano mini medium large \
    --output-dir /opt/doc-bench/data

# Verify datasets were downloaded successfully
RUN test -d /opt/doc-bench/data/parsing/omnidocbench_english_nano && \
    test -d /opt/doc-bench/data/parsing/omnidocbench_english_mini && \
    test -d /opt/doc-bench/data/parsing/omnidocbench_english_medium && \
    test -d /opt/doc-bench/data/parsing/omnidocbench_english_large && \
    test -d /opt/doc-bench/data/parsing/dp_bench && \
    test -f /opt/doc-bench/data/MANIFEST.yaml || \
    (echo "ERROR: Dataset download failed" && exit 1)

# Clean up uv cache to minimize layer size
RUN uv cache clean

# ============================================================================
# RUNTIME STAGE
# ============================================================================
FROM python:3.12-slim AS runtime

# Runtime environment
ENV PYTHONUNBUFFERED=1 \
    PATH="/.venv/bin:$PATH" \
    PYTHONPATH="/opt/doc-bench/src:/opt/doc-bench/scripts:$PYTHONPATH" \
    DOC_BENCH_LOG_LEVEL=INFO \
    DOC_BENCH_OUTPUT_FORMAT=csv

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r docbench && \
    useradd -r -u 1000 -g docbench -s /bin/bash -d /home/docbench docbench && \
    mkdir -p /home/docbench

# Create application directory structure
RUN mkdir -p /opt/doc-bench/src && \
    mkdir -p /opt/doc-bench/scripts && \
    mkdir -p /opt/doc-bench/contracts && \
    mkdir -p /opt/doc-bench/data && \
    mkdir -p /work/parsers && \
    mkdir -p /work/results

# Copy virtual environment from builder
COPY --from=builder --chown=docbench:docbench /.venv /.venv

# Copy baked datasets from datasets stage
COPY --from=datasets --chown=docbench:docbench /opt/doc-bench/data /opt/doc-bench/data

# Copy application source code
COPY --chown=docbench:docbench src /opt/doc-bench/src
COPY --chown=docbench:docbench scripts /opt/doc-bench/scripts
COPY --chown=docbench:docbench contracts /opt/doc-bench/contracts

# Set ownership of directories
RUN chown -R docbench:docbench /opt/doc-bench /work

# Set working directory
WORKDIR /opt/doc-bench

# Switch to non-root user
USER docbench

# Default entry point - show help when no arguments provided
ENTRYPOINT ["uv", "run"]
CMD ["--help"]
