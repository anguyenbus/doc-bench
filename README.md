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

Evaluate document parsers on layout-aware benchmarks. Two modes available:

### Modes

**In-Process Mode** — Run parser inside doc-bench
```bash
uv run doc-bench evaluate --dataset dp_bench --parser stub --limit 10
```

**File-Based Mode** — Grade pre-computed predictions
```bash
# 1. Export dataset documents
docker run --rm --entrypoint /opt/venv/bin/doc-bench-dump-dataset \
  -v ./pdfs:/work/output doc-bench --dataset dp_bench --output /work/output --limit 10

# 2. Run your parser, write predictions as ./predictions/<doc_id>.json

# 3. Grade predictions
docker run --rm -v ./predictions:/work/predictions -v ./results:/work/results \
  doc-bench --dataset dp_bench --predictions /work/predictions
```

### Datasets

| Dataset | Description | Documents | Notes |
|---------|-------------|-----------|-------|
| `omnidocbench` | English-only sample | 10 pages | Docker baseline (pruned from 593) |
| `dp_bench` | Digital PDF benchmark | 1,052 docs | Full dataset included |

**Note:** The Docker image includes a minimal 10-page OmniDocBench sample for fast iteration. For full evaluation, use local datasets or mount additional data.

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

# File-based: grade pre-computed predictions
uv run doc-bench evaluate --dataset dp_bench --predictions ./predictions

# Custom output directory
uv run doc-bench evaluate --dataset omnidocbench --parser docling --output-dir ./my_results
```

### Document Identity Convention

Prediction files must be named `<doc_id>.json` where `<doc_id>` matches the stem of the exported PDF from `dump-dataset`. See [docs/document-identity.md](docs/document-identity.md) for details.

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
- `{dataset}_{parser}_rejected_{timestamp}.csv` - Rejected samples (file-based mode only)

Example CSV output:
```csv
query_id,error,nid,nid_s,teds,teds_s,mhs,mhs_s,ard,bleu,meteor
omnidocbench_0,,0.85,0.87,0.92,0.94,0.88,0.90,0.12,0.75,0.68
omnidocbench_1,,0.78,0.80,0.85,0.87,0.82,0.84,0.15,0.70,0.62
```

**Rejection tracking** (file-based mode):
```csv
doc_id,reason,source_file,detail
01030000000001,MISSING_PREDICTION,01030000000001.pdf,
01030000000002,INVALID_SCHEMA,01030000000002.json,"elements[0].bbox missing required field 'x1'"
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
# Build minimal image with 10-file OmniDocBench sample
docker build -t doc-bench .
```

**Image size:** 769MB (includes DP-Bench + 10 OmniDocBench English pages)

### Included Datasets

| Dataset | Documents | Purpose |
|---------|-----------|---------|
| `omnidocbench_english_large` | 10 pages | Minimal test sample (pruned from 593) |
| `dp_bench` | 1,052 docs | Full digital PDF benchmark |

### Baseline Results

Pre-computed docling baseline included at `/opt/doc-bench/baseline/docling_baseline.json`:

```json
{
  "nid": 0.9173,
  "ard": 0.7993,
  "bleu": 0.717,
  "meteor": 0.8198
}
```

Use for comparing against new parsing methods.

### Run

```bash
# In-process evaluation (stub parser)
docker run -v ./results:/work/results doc-bench --dataset omnidocbench --parser stub

# File-based evaluation (grade pre-computed predictions)
docker run --rm --entrypoint /opt/venv/bin/doc-bench-dump-dataset \
  -v ./pdfs:/work/output doc-bench --dataset dp_bench --output /work/output --limit 10
# Run your parser over ./pdfs, write predictions to ./predictions/<doc_id>.json
docker run --rm -v ./predictions:/work/predictions -v ./results:/work/results \
  doc-bench --dataset dp_bench --predictions /work/predictions

# View available commands
docker run --rm doc-bench --help
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

## Documentation

- [File-Based Evaluation Guide](docs/file-based-evaluation.md) - Dump, predict, grade workflow
- [Document Identity Convention](docs/document-identity.md) - Naming rules for prediction files
- [contracts/README.md](contracts/README.md) - Parser output schema
