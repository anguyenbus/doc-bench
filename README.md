# doc-bench

Evaluation framework for document parsing systems. Supports deterministic metrics on public benchmarks (OmniDocBench, DP-Bench).

## Quick Start

```bash
# Install dependencies
uv sync

# Run parsing evaluation with stub parser (for testing)
uv run doc-bench evaluate --dataset dp_bench --parser stub --limit 10

# Run with fast digital PDF parser
uv run doc-bench evaluate --dataset dp_bench --parser fast

# Run with OmniDocBench medium slice (100 docs)
uv run doc-bench evaluate --dataset omnidocbench_english_medium --parser docling
```

## Installation

```bash
# Core dependencies
uv sync

# Optional: AWS Bedrock support
uv sync --extra bedrock
```

## Parsing Evaluation

Evaluate document parsers on layout-aware benchmarks.

### Datasets

| Dataset | Description | Documents |
|---------|-------------|-----------|
| `omnidocbench_english_nano` | Nano slice for quick testing | 3 pages |
| `omnidocbench_english_mini` | Mini slice for development | 10 pages |
| `omnidocbench_english_medium` | Medium slice for evaluation | 100 pages |
| `omnidocbench_english_large` | Full English dataset | 593 pages |
| `dp_bench` | Digital PDF benchmark | 1,052 docs |

### Parsers

| Parser | Description |
|--------|-------------|
| `stub` | Stub implementation for testing |
| `fast` | pypdf - fast digital PDF parsing |
| `docling` | Full OCR pipeline with layout analysis |

### Commands

```bash
# Evaluate on OmniDocBench with fast parser
uv run doc-bench evaluate --dataset omnidocbench --parser fast

# Evaluate on DP-Bench with stub parser (limited samples)
uv run doc-bench evaluate --dataset dp_bench --parser stub --limit 10

# Custom output directory
uv run doc-bench evaluate --dataset omnidocbench --parser docling --output-dir ./my_results
```

### Metrics

- **NID/NID-S** - Normalized Indel Distance (text similarity, with/without tables)
- **TEDS/TEDS-S** - Tree Edit Distance Similarity (table structure)
- **MHS/MHS-S** - Markdown Hierarchical Similarity (heading structure)
- **ARD** - Average Rank Distance (reading order)
- **BLEU** - Token-level n-gram overlap
- **METEOR** - Harmonic mean of precision/recall with stemming

### Results

Results written to `results/` with timestamp:
- `{dataset}_{parser}_results_{timestamp}.csv` - Per-document metrics
- `{dataset}_{parser}_results_{timestamp}.json` - Summary with averages

Example CSV output:
```csv
query_id,error,nid,nid_s,teds,teds_s,mhs,mhs_s,ard,bleu,meteor
omnidocbench_0,,0.85,0.87,0.92,0.94,0.88,0.90,0.12,0.75,0.68
omnidocbench_1,,0.78,0.80,0.85,0.87,0.82,0.84,0.15,0.70,0.62
```

## Configuration

Edit `eval_config.yaml` for dataset paths and metric settings:

```yaml
datasets:
  omnidocbench:
    path: /path/to/omnidocbench
  dp_bench:
    path: /path/to/dp_bench

metrics:
  parsing:
    enabled:
      - nid
      - teds
      - mhs
      - ard
      - bleu
      - meteor

models:
  parser: stub
```

## Project Structure

```
.
├── pyproject.toml          # Package configuration
├── eval_config.yaml        # Dataset paths and settings
├── README.md
│
├── contracts/              # JSON Schema contracts
│   ├── parser_output.schema.json  # Input contract for parsers
│   └── results_v1.schema.json      # Output contract for evaluation
│
├── scripts/                # Dataset utilities
│   └── download_datasets.py
│
├── src/doc_bench/
│   ├── __init__.py
│   ├── config.py           # Config loader
│   ├── adapters/           # Parser adapter pattern
│   │   ├── parser_adapter.py
│   │   └── schema_validator.py
│   ├── datasets/           # Benchmark loaders
│   │   ├── omnidocbench.py
│   │   └── dp_bench.py
│   ├── metrics/            # Parsing evaluation metrics
│   │   └── parsing/        # NID, TEDS, MHS, BLEU, METEOR
│   ├── runners/            # CLI entry points
│   │   └── run_parsing_eval.py
│   └── stubs/              # Reference parsers (stub, fast, docling)
│
├── tests/                  # Unit and integration tests
│
├── data/                   # Benchmark datasets (gitignored)
│   └── parsing/
│       ├── omnidocbench/
│       └── dp_bench/
│
└── results/                # CSV outputs (gitignored)
```

## Dependencies

**Parsing:**
- `pypdf` - Fast digital PDF parsing
- `docling` - OCR and layout analysis
- `sacrebleu` - BLEU score
- `nltk` - METEOR score
- `torch` + `torchmetrics[detection]` - Layout mAP calculation

**Core:**
- `pydantic` - Data validation
- `jsonschema` - Schema validation
- `polars` - Data processing

## Using Your Own Parser

doc-bench evaluates **your** document parser. The stub parsers in `stubs/` are for demonstration only.

### Integration Pattern

1. Implement a parse function with signature:
   ```python
   def parse(pdf_path: Path) -> dict:
       # Your parsing logic here
       return {
           "schema_version": "1.0.0",
           "parser_version": "my-parser-1.0.0",
           "source": {...},
           "pages": [...],
           "elements": [...],
       }
   ```

2. Wrap with `ParserAdapter`:
   ```python
   from doc_bench.adapters.parser_adapter import ParserAdapter

   adapter = ParserAdapter(parse_callable=parse)
   output = adapter.parse(pdf_path)
   ```

See `contracts/parser_output.schema.json` for the complete output schema.

## Docker

doc-bench provides a containerized image with **baked-in datasets** for reproducible benchmarking.

### Build

```bash
# Datasets downloaded during build (nano, mini, medium, large slices + dp_bench)
docker build -t doc-bench .
```

### Run

```bash
# Evaluate with OmniDocBench nano slice (baked in image)
docker run -v ./parsers:/work/parsers:ro -v ./results:/work/results:rw \
    doc-bench doc-bench evaluate --dataset omnidocbench_english_nano --parser stub

# With OmniDocBench medium slice (100 docs, baked in)
docker run -v ./parsers:/work/parsers:ro -v ./results:/work/results:rw \
    doc-bench doc-bench evaluate --dataset omnidocbench_english_medium --parser fast

# With DP-Bench (baked in)
docker run -v ./parsers:/work/parsers:ro -v ./results:/work/results:rw \
    doc-bench doc-bench evaluate --dataset dp_bench --parser docling

# View available commands
docker run doc-bench --help
```

### Volume Mounts

| Mount | Description | Permissions |
|-------|-------------|-------------|
| `./parsers:/work/parsers` | Your parser module | Read-only (ro) |
| `./results:/work/results` | Evaluation output | Read-write (rw) |

**Note:** Datasets are baked into the image (`/opt/doc-bench/data`), not mounted.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOC_BENCH_LOG_LEVEL` | INFO | Logging verbosity |
| `DOC_BENCH_OUTPUT_FORMAT` | csv | Output format (csv/json) |

### Docker Compose

```bash
# Start evaluation with Compose
docker compose run doc-bench doc-bench evaluate --dataset omnidocbench_english_mini --parser fast

# Development mode (source hot-reload)
docker compose -f docker-compose.yml -f docker-compose.dev.yml run doc-bench doc-bench evaluate --dataset omnidocbench_english_nano --parser stub
```

## Contracts

See [contracts/README.md](contracts/README.md) for schema documentation.
