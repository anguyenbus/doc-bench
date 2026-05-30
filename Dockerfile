# Multi-stage Dockerfile for doc-bench
# Minimal image with baked-in datasets (DP-Bench + OmniDocBench large slice)

# ============================================================================
# BUILDER STAGE - Install dependencies
# ============================================================================
FROM python:3.13-slim AS builder

# Build-time environment
ENV UV_COMPILE_BYTECODE=1 \
    PYTHONOPTIMIZE=2 \
    PYTHONUNBUFFERED=1

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /build

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY README.md ./
COPY src ./src

# Install dependencies
RUN uv sync --frozen --no-dev
# Move venv to /opt/venv for consistent copying
RUN mv .venv /opt/venv

# ============================================================================
# DATASETS STAGE - Download datasets
# ============================================================================
FROM python:3.13-slim AS datasets

WORKDIR /opt/doc-bench

# Copy uv binary from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy source and scripts
COPY --chown=root:root src /opt/doc-bench/src
COPY --chown=root:root scripts /opt/doc-bench/scripts

# Download datasets: OmniDocBench sample (10 files for testing)
WORKDIR /opt/doc-bench
ENV PYTHONPATH=/opt/doc-bench/src
RUN /opt/venv/bin/python scripts/download_datasets.py \
    --datasets omnidocbench dp_bench \
    --omnidocbench-slices large \
    --output-dir /opt/doc-bench/data

# Prune OmniDocBench to minimal size for testing
RUN /opt/venv/bin/python scripts/prune_omnidocbench.py

# Prune DP-Bench to representative set (12 docs for testing)
RUN /opt/venv/bin/python scripts/prune_dp_bench.py

# Verify datasets
RUN test -d /opt/doc-bench/data/parsing/omnidocbench_english_large && \
    test -f /opt/doc-bench/data/MANIFEST.yaml || \
    (echo "ERROR: Dataset download failed" && exit 1)

# ============================================================================
# RUNTIME STAGE - Minimal final image
# ============================================================================
FROM python:3.13-slim AS runtime

# Runtime environment
ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/opt/doc-bench/src" \
    NLTK_DATA="/opt/nltk_data" \
    DOC_BENCH_LOG_LEVEL=INFO \
    DOC_BENCH_OUTPUT_FORMAT=csv

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r docbench && \
    useradd -r -u 1000 -g docbench -s /bin/bash -d /home/docbench docbench && \
    mkdir -p /home/docbench

# Create directories
RUN mkdir -p /opt/doc-bench /work/parsers /work/results

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
# Fix entrypoint scripts: regenerate with correct python path
RUN /opt/venv/bin/python -m sysconfig && \
    for script in /opt/venv/bin/*; do \
        if head -1 "$script" | grep -q "^#!/build/.venv/bin/python"; then \
            sed -i '1s|#!/build/.venv/bin/python|#!/opt/venv/bin/python|' "$script"; \
        fi; \
    done
# Download NLTK data for METEOR metric (to shared location)
RUN mkdir -p /opt/nltk_data && \
    /opt/venv/bin/python -c "import nltk; nltk.download('wordnet', download_dir='/opt/nltk_data'); nltk.download('punkt', download_dir='/opt/nltk_data'); nltk.download('omw-1.4', download_dir='/opt/nltk_data')" && \
    chown -R docbench:docbench /opt/nltk_data

# Copy baked datasets from datasets stage
COPY --from=datasets --chown=docbench:docbench /opt/doc-bench/data /opt/doc-bench/data

# Copy source code
COPY --chown=docbench:docbench src /opt/doc-bench/src
COPY --chown=docbench:docbench scripts /opt/doc-bench/scripts
COPY --chown=docbench:docbench contracts /opt/doc-bench/contracts
COPY --chown=docbench:docbench eval_config.yaml /opt/doc-bench/eval_config.yaml
COPY --chown=docbench:docbench baseline /opt/doc-bench/baseline

# Set ownership
RUN chown -R docbench:docbench /opt/doc-bench /work

WORKDIR /opt/doc-bench
USER docbench

# Default entry point
ENTRYPOINT ["doc-bench"]
CMD ["--help"]
