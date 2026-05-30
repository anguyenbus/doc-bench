# doc-bench

Evaluation framework for document parsing systems. Supports deterministic metrics on public benchmarks (OmniDocBench, DP-Bench).

## Quick Start

```bash
# Install from wheel
pip install doc-bench-0.1.0-py3-none-any.whl

# Run smoke test (bundled fixtures, no data download needed)
doc-bench-smoke-test

# Grade pre-computed predictions
doc-bench --dataset dp_bench --predictions ./predictions
```

## Installation

### From Wheel (Recommended)

```bash
# Install wheel with bundled fixtures and schema
pip install doc-bench-0.1.0-py3-none-any.whl

# Verify installation
doc-bench-smoke-test
```

### From Source

```bash
# Clone and install
git clone <repo>
cd doc-bench
uv sync

# Build wheel
uv build --wheel
pip install dist/doc_bench-0.1.0-py3-none-any.whl
```

### Optional Dependencies

```bash
# AWS Bedrock support
uv sync --extra bedrock

# Docling OCR support
uv sync --extra docling
```

## Smoke Test

Validate installation with bundled fixtures (22 documents, no download required):

```bash
doc-bench-smoke-test
```

Tests:
- 4 DP-Bench documents (Paragraph, Caption categories)
- 10 OmniDocBench documents (academic_literature, exam_paper, colorful_textbook, book, PPT2PDF)
- Schema validation (bundled parser_output.schema.json)

Output:
```
Smoke Test Results
========================================
Total documents: 22
Rejected: 0 (0.0%)

PASS: Rejection rate (0.0%) < threshold (10%)
```

## Parsing Evaluation

File-based evaluation of pre-computed parser predictions.

### Workflow

**File-Based Evaluation** — Grade pre-computed predictions
```bash
# 1. Export dataset documents
doc-bench-dump-dataset --dataset dp_bench --output ./pdfs --limit 10

# 2. Run your parser, write predictions as ./predictions/<doc_id>.json

# 3. Grade predictions
doc-bench --dataset dp_bench --predictions ./predictions --output-dir ./results
```

### Datasets

#### Bundled Fixtures (Smoke Test)

| Dataset | Documents | Categories |
|---------|-----------|------------|
| DP-Bench | 12 docs | Paragraph (8), Caption (2), Chart (1), Heading1 (1) |
| OmniDocBench | 10 docs | academic_literature (2), exam_paper (2), colorful_textbook (2), book (2), PPT2PDF (2) |

Included in wheel - no download required for smoke testing.

#### Full Benchmarks

| Dataset | Description | Documents | Source |
|---------|-------------|-----------|--------|
| `dp_bench` | Digital PDF benchmark | 1,052 docs | Contact authors |
| `omnidocbench` | English-only sample | 593 pages | [HuggingFace](https://huggingface.co/datasets/jianxiao-o0/omnidocbench) |

**Dataset versions** tracked in `MANIFEST.yaml` (bundled with package).

### Commands

```bash
# Smoke test (bundled fixtures)
doc-bench-smoke-test

# Grade pre-computed predictions
doc-bench --dataset dp_bench --predictions ./predictions --output-dir ./results

# Limit processing (for testing)
doc-bench --dataset dp_bench --predictions ./predictions --limit 10

# Dump dataset for external processing
doc-bench-dump-dataset --dataset dp_bench --output ./pdfs --limit 10
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

Dataset locations specified via `eval_config.yaml`:

```bash
doc-bench --dataset dp_bench --predictions ./predictions
```

For OmniDocBench, supports both layouts:
- `root/images/{filename}.png` (standard HuggingFace layout)
- `root/{filename}.png` (flat baseline layout)

## Project Structure

```
.
├── pyproject.toml          # Package configuration
├── README.md
│
├── contracts/              # JSON Schema contracts (dev)
│   ├── parser_output.schema.json  # Input contract (bundled in fixtures)
│   └── results_v1.schema.json      # Output contract
│
├── scripts/                # Dataset utilities
│   └── generate_fixtures.py
│
├── src/doc_bench/
│   ├── __init__.py         # get_bundled_schema_path()
│   ├── MANIFEST.yaml       # Dataset versions (bundled)
│   ├── fixtures/           # Bundled test data (22 docs)
│   │   ├── manifest.json
│   │   ├── parser_output.schema.json
│   │   ├── dp_bench/
│   │   └── omnidocbench/
│   ├── adapters/           # Parser adapter pattern
│   ├── datasets/           # Benchmark loaders
│   ├── metrics/            # NID, TEDS, MHS, BLEU, METEOR
│   ├── runners/            # CLI entry points
│   └── cli/                # CLI commands
│
├── tests/                  # Unit and integration tests
│
├── data/                   # Local benchmark datasets (gitignored)
│
└── results/                # CSV outputs (gitignored)
```

## Dependencies

**Core:**
- `pydantic` - Data validation
- `jsonschema` - Schema validation
- `polars` - Data processing
- `pandas` - CSV output handling

**Metrics:**
- `sacrebleu` - BLEU score
- `nltk` - METEOR score
- `rapidfuzz` - NID calculation
- `apted` - TEDS calculation
- `beautifulsoup4` + `lxml` - HTML parsing

## Using Your Own Parser

doc-bench evaluates **your** document parser via file-based predictions.

### Integration Pattern

1. Run your parser and output predictions following `parser_output.schema.json`:
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

2. Save predictions as `<doc_id>.json`:
   ```bash
   parse(input.pdf) > predictions/01030000000001.json
   ```

3. Grade predictions:
   ```bash
   doc-bench --dataset dp_bench --predictions ./predictions
   ```

See `contracts/parser_output.schema.json` for the complete output schema.

## Wheel Distribution

The wheel package includes:

| Component | Location | Purpose |
|-----------|----------|---------|
| Fixtures | `doc_bench/fixtures/` | 14 bundled test documents |
| Schema | `doc_bench/fixtures/parser_output.schema.json` | Parser output validation |
| Manifest | `doc_bench/MANIFEST.yaml` | Dataset version tracking |

**Schema resolution** (automatic, no CWD `contracts/` needed):
1. Bundled fixtures (installed package)
2. Fallback to `contracts/parser_output.schema.json` (dev)

## Docker

Alternative: Containerized image with baked-in datasets for reproducible benchmarking.

### Build

```bash
# Build minimal image with 10-file OmniDocBench sample
docker build -t doc-bench .
```

**Image size:** 649MB (includes 10 OmniDocBench English pages)

### Included Datasets

| Dataset | Documents | Purpose |
|---------|-----------|---------|
| `omnidocbench` | 10 pages | Minimal test sample (pruned from 593) |

**Note:** DP-Bench is not included in the minimal Docker image. Use local datasets or mount data for DP-Bench evaluation.

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
# File-based evaluation (grade pre-computed predictions)
docker run --rm -v ./predictions:/work/predictions -v ./results:/work/results \
  doc-bench doc-bench --dataset dp_bench --predictions /work/predictions

# View available commands
docker run --rm doc-bench doc-bench --help
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
# Grade predictions with Compose
docker compose run doc-bench doc-bench --dataset omnidocbench --predictions /work/predictions
```

## Contracts

See [contracts/README.md](contracts/README.md) for schema documentation.

## Documentation

- [Smoke Test Guide](#smoke-test) - Quick validation with bundled fixtures
- [File-Based Evaluation Guide](docs/file-based-evaluation.md) - Dump, predict, grade workflow
- [Document Identity Convention](docs/document-identity.md) - Naming rules for prediction files
- [contracts/README.md](contracts/README.md) - Parser output schema
