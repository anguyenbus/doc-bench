# Docker Documentation for doc-bench

This guide covers building, running, and using doc-bench in Docker containers.

## Quick Start

### Using Pre-built Image

```bash
# Run with default help output
docker run doc-bench:latest

# Run parsing evaluation
docker run -v $(pwd)/parsers:/work/parsers:ro \
             -v $(pwd)/results:/work/results:rw \
             doc-bench:latest eval-parsing --dataset omnidocbench --parser fast

# Run dataset evaluation
docker run -v $(pwd)/results:/work/results:rw \
             doc-bench:latest eval-dataset --dataset omnidocbench
```

### Building from Source

```bash
# Build the image
docker build -t doc-bench:latest .

# Run with default help
docker run doc-bench:latest

# Run with custom parser
docker run -v $(pwd)/my_parser:/work/parsers:ro \
             -v $(pwd)/results:/work/results:rw \
             doc-bench:latest eval-parsing --dataset dp_bench
```

## Docker Compose

### Basic Usage

```bash
# Start the service (shows help by default)
docker-compose up

# Run parsing evaluation
docker-compose run doc-bench eval-parsing --dataset omnidocbench --parser fast

# Run with custom output format
DOC_BENCH_OUTPUT_FORMAT=json docker-compose run doc-bench eval-parsing --dataset dp_bench
```

### Development Mode

```bash
# Use development override (mounts source code for hot reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run with debug logging
docker-compose -f docker-compose.yml -f docker-compose.dev.yml run doc-bench eval-parsing --dataset omnidocbench --limit 10
```

## Volume Mounts

The container uses volume mounts for input and output:

### Input Mounts

- `/work/parsers` (read-only): Mount your custom parser modules here
  ```bash
  docker run -v /path/to/my_parser:/work/parsers:ro doc-bench:latest
  ```

### Output Mounts

- `/work/results` (read-write): Evaluation results are written here
  ```bash
  docker run -v /path/to/results:/work/results:rw doc-bench:latest
  ```

## Environment Variables

Configure container behavior via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DOC_BENCH_LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `DOC_BENCH_OUTPUT_FORMAT` | `csv` | Output format (csv, json) |

### Setting Environment Variables

```bash
# Via docker run
docker run -e DOC_BENCH_LOG_LEVEL=DEBUG \
           -e DOC_BENCH_OUTPUT_FORMAT=json \
           doc-bench:latest eval-parsing --dataset omnidocbench

# Via docker-compose
DOC_BENCH_LOG_LEVEL=DEBUG docker-compose run doc-bench eval-parsing

# Via .env file (docker-compose)
echo "DOC_BENCH_LOG_LEVEL=DEBUG" > .env
docker-compose up
```

## Dataset Locations

Benchmark datasets are baked into the image at build time:

- **OmniDocBench**: `/opt/doc-bench/data/parsing/omnidocbench_english`
- **DP-Bench**: `/opt/doc-bench/data/parsing/dp_bench`
- **Manifest**: `/opt/doc-bench/data/MANIFEST.yaml`

You can override these by mounting your own datasets:

```bash
docker run -v /path/to/my_dataset:/opt/doc-bench/data/parsing/my_dataset:ro \
           doc-bench:latest eval-parsing --dataset my_dataset
```

## CLI Commands

The container supports all eval-harness CLI commands:

### eval-parsing

Run parsing evaluation:

```bash
docker run -v $(pwd)/parsers:/work/parsers:ro \
             -v $(pwd)/results:/work/results:rw \
             doc-bench:latest eval-parsing --dataset omnidocbench --parser stub --limit 10
```

### eval-dataset

Run dataset operations:

```bash
docker run doc-bench:latest eval-dataset --dataset omnidocbench
```

### eval-harness-check

Verify configuration:

```bash
docker run doc-bench:latest eval-harness-check config
```

## Troubleshooting

### Container exits immediately

By default, the container shows help and exits. Use a subcommand:

```bash
# Wrong: shows help and exits
docker run doc-bench:latest

# Correct: runs evaluation
docker run -v $(pwd)/results:/work/results:rw \
           doc-bench:latest eval-parsing --dataset omnidocbench
```

### Permission denied errors

Ensure volume mounts are writable by the non-root user (UID 1000):

```bash
# Create results directory with correct permissions
mkdir -p results
chmod 755 results

# Or run as the same UID
docker run -u $(id -u) -v $(pwd)/results:/work/results:rw doc-bench:latest
```

### Datasets not found

If baked datasets are missing, check the manifest:

```bash
docker run doc-bench:latest cat /opt/doc-bench/data/MANIFEST.yaml
```

### Image size concerns

The target image size is < 800MB. If your image is larger:

1. Check build logs for large downloads
2. Verify apt caches are cleaned
3. Verify uv cache is cleaned

## Security Considerations

### Non-root Execution

The container runs as non-root user `docbench` (UID 1000) for security. This means:

- Volume mounts must be readable/writable by UID 1000
- Cannot install packages at runtime
- Cannot bind to privileged ports (< 1024)

### No Secrets

The container is designed for parsing-only evaluation and contains no secrets:

- No API keys required for core parsing evaluation
- No credentials baked into the image
- LLM-based evaluation requires passing API keys at runtime

### Read-only Filesystem

For enhanced security, run with read-only root filesystem:

```bash
docker run --read-only \
           --tmpfs /tmp \
           --tmpfs /work \
           -v $(pwd)/results:/work/results:rw \
           doc-bench:latest eval-parsing --dataset omnidocbench
```

## Building for Production

### Multi-architecture Builds

To build for multiple architectures (ARM64, AMD64):

```bash
# Use buildx for multi-platform builds
docker buildx build --platform linux/amd64,linux/arm64 -t doc-bench:latest .
```

### Optimized Builds

For smallest image size:

```bash
# Build with --no-cache to ensure clean build
docker build --no-cache -t doc-bench:latest .

# Check image size
docker images doc-bench:latest
```

## Advanced Usage

### Custom Parser Integration

To use your own parser:

1. Create a parser module compatible with eval-harness
2. Mount to `/work/parsers`:
   ```bash
   docker run -v /path/to/my_parser:/work/parsers:ro \
              doc-bench:latest eval-parsing --dataset omnidocbench --parser my_parser
   ```

### Custom Configuration

Mount custom configuration files:

```bash
docker run -v $(pwd)/eval_config.yaml:/opt/doc-bench/configs/eval_config.yaml:ro \
           doc-bench:latest eval-parsing --dataset omnidocbench
```

### Batch Evaluations

Run multiple evaluations with docker-compose:

```bash
# Create docker-compose.batch.yml with multiple services
# Then run:
docker-compose -f docker-compose.batch.yml up
```

## Additional Resources

- [eval-harness README](../../references/eval-harness/README.md)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
