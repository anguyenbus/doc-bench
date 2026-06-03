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

## Development

### Regenerating Baseline Fixtures

The DP-Bench and OmniDocBench baseline-score fixtures under
`src/doc_bench/fixtures/` are produced by a vendored copy of the
`docling-baseline` generator (`src/docling_baseline/`). That generator pulls
heavy dependencies (`docling` brings a full torch tree), so they are confined to
a dev-only `generator` dependency-group and are **not** shipped in the doc-bench
wheel and **not** part of the runtime dependencies. A plain `uv sync` never
installs them.

Regenerate all in-scope baselines in-place:

```bash
make regen-fixtures
```

Regenerate a single dataset:

```bash
make regen-fixtures DATASET=dp_bench
```

Both targets run the generator under the dev `generator` group on Python 3.13
(`uv` auto-provisions the interpreter; doc-bench core stays `requires-python
>=3.12`):

```bash
uv run --python 3.13 --group generator python scripts/regenerate_fixtures.py
```

The generator is invoked as a module (`python -m docling_baseline.cli ...`); it
is not registered as a doc-bench console script. ATO-Bench is out of scope for
this target.

### Vendoring Guards

Because the generator is vendored verbatim, it keeps a second copy of the metric
implementations (NID / TEDS / MHS) and the parser-output schema. Two CI guards
protect against that duplication causing trouble:

- **Byte-equality drift guard** (`tests/test_metric_drift_guard.py`) -- runs in
  the fast suite (`make test`). It asserts each vendored metric/schema file is
  byte-identical to its doc-bench counterpart, modulo a documented, pinned
  allow-list (exactly the legacy-alias functions appended to `nid.py` and
  `table_teds.py`). Any unreviewed divergence fails the build.
- **Wheel-leak guard** (`tests/test_wheel_no_generator_leak.py`) -- marked
  `build` and deselected from the default fast loop. Run it explicitly:

  ```bash
  uv run pytest -m build
  ```

  It builds the wheel and asserts zero `docling_baseline` paths leak into the
  artifact while doc-bench paths are present.

The `make ci` target runs lint, typecheck, the fast suite (which includes the
drift guard) and `make test-build` (the wheel-leak guard), so both guards are
enforced in CI. See `docs/runbook.md` for provenance, the isolation guarantee,
and what to do when a guard fires.

## Smoke Test

Validate installation with bundled fixtures (26 documents, no download required):

```bash
doc-bench-smoke-test
```

**Tests:**
- 16 DP-Bench documents (Paragraph, Caption, Chart, Heading1, Index categories)
  - Includes 4 problematic PDFs known to challenge docling: 172, 018, 141, 121
- 10 OmniDocBench documents (academic_literature, exam_paper, colorful_textbook, book, PPT2PDF)
- Schema validation (bundled `parser_output.schema.json`)

**Output:**
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
| DP-Bench | 16 docs | Paragraph (10), Caption (2), Chart (1), Heading1 (2), Index (1) |
| OmniDocBench | 10 docs | academic_literature (2), exam_paper (2), colorful_textbook (2), book (2), PPT2PDF (2) |

**Problematic PDFs included** (known docling challenges):
- `01030000000172.pdf` (Index)
- `01030000000018.pdf` (Heading1)
- `01030000000141.pdf` (Paragraph, 29 elements)
- `01030000000121.pdf` (Paragraph, 16 elements)

Included in wheel - no download required for smoke testing.

#### Baseline Scores

Bundled reference scores for comparison (from bundled fixture evaluation):

| Dataset | Docs | NID | TEDS | MHS | ARD | BLEU | METEOR |
|---------|------|-----|------|-----|-----|------|--------|
| DP-Bench | 12 | 0.9587 | 0.0 | 0.1115 | 0.5868 | 0.8744 | 0.9413 |
| OmniDocBench | 10 | 0.8230 | 0.0 | 0.0 | 0.75 | 0.7352 | 0.7941 |

**Note:** Baseline scores cover the original stratified sample (12 DP-Bench + 10 OmniDocBench).
The 4 additional problematic DP-Bench PDFs (172/018/141/121) are included for parser robustness
testing but not part of the baseline averages.

Located at:
- `doc_bench/fixtures/dpbench_results.json`
- `doc_bench/fixtures/omnidocbench_results.json`

#### Custom Data Evaluation

Evaluate on your own datasets with ground truth annotations.

**DP-Bench Format:**
```bash
my_data/
├── reference.json          # Ground truth (required)
└── pdfs/                   # Source PDFs (required for reference)
    ├── doc1.pdf
    └── doc2.pdf
```

**reference.json format (DP-Bench):**
```json
{
  "doc1.pdf": {
    "elements": [
      {
        "page": 1,
        "coordinates": [{"x": 100, "y": 200}],
        "category": "Paragraph",
        "content": {"text": "Your document text"}
      }
    ]
  }
}
```

**Required element fields:**
- `page` - Page number (int)
- `coordinates` - Array of `[{"x": num, "y": num}]` for position
- `category` - Element type (Paragraph, Table, List, Figure, Caption, Header, etc.)
- `content.text` - Text content (string)

**OmniDocBench Format:**
```bash
my_data/
├── OmniDocBench.json       # Ground truth (required)
└── images/                 # Source images (optional for evaluation)
    ├── page1.png
    └── page2.png
```

**Run evaluation:**
```bash
doc-bench --dataset dp_bench --data-dir /path/to/my_data --predictions ./predictions
```

**Output:**
- `results/dp_bench_predictions_results_TIMESTAMP.csv` - Per-document metrics
- `results/dp_bench_predictions_rejected_TIMESTAMP.csv` - Rejection details
- `results/dp_bench_predictions_results_TIMESTAMP.json` - Summary with averages

**Prediction file naming:**
- Files must be named `<doc_id>.json` (without `.pdf` extension)
- Example: For `doc1.pdf` in reference.json, prediction must be `doc1.json`
- Use `doc-bench-dump-dataset` to see expected doc_id values

#### Full Benchmarks

| Dataset | Description | Documents | Source |
|---------|-------------|-----------|--------|
| `dp_bench` | Digital PDF benchmark | 1,052 docs | Contact authors |
| `omnidocbench` | English-only sample | 593 pages | [HuggingFace](https://huggingface.co/datasets/jianxiao-o0/omnidocbench) |

**Dataset versions** tracked in `MANIFEST.yaml` (bundled with package).

### ⚠️ Benchmark Limitations

#### DP-Bench: Single-Page Documents Only

**Important:** DP-Bench gold annotations are **single-page only**. Each `doc_id` in `reference.json` represents exactly one page of content, not a multi-page document.

**Implications:**
- Cross-page elements (tables, figures spanning pages) are NOT represented in gold
- Multi-page reading order is NOT evaluated
- Metrics reflect page-level extraction quality, NOT document-level parsing

**For production evaluation:** Use DP-Bench for page-level component extraction quality. Complement with multi-page benchmarks for complete document parsing assessment.

#### OmniDocBench: Multi-Page but Sparse Annotations

**Structure:** OmniDocBench provides page-level annotations (593 pages across multiple documents). Each page is evaluated independently.

**Annotation density:** Sparse. Layout detections (`layout_dets`) cover key elements but not all content on each page. Text extraction is evaluated only on annotated regions.

**Implications:**
- Metrics reflect quality on annotated elements only, not full-page OCR
- Unannotated content (background text, marginalia) is not evaluated
- Page-level scores aggregate sparse detections, not complete document coverage

**For parser evaluation:** Use OmniDocBench for layout detection quality on annotated elements. Complement with dense-annotation benchmarks for full-page extraction assessment.

#### Table Metrics: Gold Rendering

**Current state:** DP-Bench gold renders tables from `content.html` → Markdown pipe-tables (matching prediction format).

**Table rendering behavior:**
- Gold: `content.html` table grid → `| cell1 | cell2 |` pipe-table format
- Prediction: `content.cells` → same pipe-table format
- Empty `content.text` no longer drops tables (fixed)

**Impact on metrics:**
- NID/BLEU: Table cells now comparable between gold and prediction
- TEDS: Requires markdown tables in both gold and prediction — now supported
- Table-heavy documents: Scores reflect extraction quality, not format mismatch

**Prior bug (fixed):** Tables with empty `content.text` were silently dropped from gold, penalizing faithful extraction. Fix: `build_gold_markdown` renders from `content.html` first.

### Commands

```bash
# Smoke test (bundled fixtures)
doc-bench-smoke-test

# Grade pre-computed predictions (uses eval_config.yaml path)
doc-bench --dataset dp_bench --predictions ./predictions --output-dir ./results

# Grade with custom data directory
doc-bench --dataset dp_bench --data-dir /path/to/my_data --predictions ./predictions

# Limit processing (for testing)
doc-bench --dataset dp_bench --predictions ./predictions --limit 10

# Dump dataset for external processing
doc-bench-dump-dataset --dataset dp_bench --output ./pdfs --limit 10
```

### Complete Workflow Example

**Step 1: Prepare your data**
```bash
# Create data directory structure
mkdir -p my_evaluation_data/{reference,pdfs,predictions}

# Add your PDFs
cp doc1.pdf doc2.pdf my_evaluation_data/pdfs/

# Create reference.json with ground truth
cat > my_evaluation_data/reference.json << 'EOF'
{
  "doc1.pdf": {
    "elements": [
      {"page": 1, "coordinates": [{"x": 100, "y": 200}], "category": "Paragraph", "content": {"text": "..."}}
    ]
  },
  "doc2.pdf": {
    "elements": [...]
  }
}
EOF
```

**Step 2: Generate predictions**
```bash
# Run your parser, output to predictions/
your_parser my_evaluation_data/pdfs/doc1.pdf > my_evaluation_data/predictions/doc1.json

# Prediction format must match parser_output.schema.json
```

**Step 3: Evaluate**
```bash
doc-bench --dataset dp_bench \
  --data-dir my_evaluation_data \
  --predictions my_evaluation_data/predictions \
  --output-dir results
```

**Step 4: Check results**
```bash
cat results/dp_bench_predictions_results_*.csv
# CSV with NID, TEDS, MHS, ARD, BLEU, METEOR per document

cat results/dp_bench_predictions_results_*.json
# Summary with averages
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
| Fixtures | `doc_bench/fixtures/` | 22 bundled test documents |
| Schema | `doc_bench/fixtures/parser_output.schema.json` | Parser output validation |
| Baselines | `doc_bench/fixtures/*_results.json` | Reference scores for comparison |
| Manifest | `doc_bench/MANIFEST.yaml` | Dataset version tracking |

**Schema resolution** (automatic, no CWD `contracts/` needed):
1. Bundled fixtures (installed package)
2. Fallback to `contracts/parser_output.schema.json` (dev)

### Accessing Baseline Scores

```python
from importlib.resources import files
import json

# Load DP-Bench baseline
dp_baseline = json.loads(
    (files("doc_bench") / "fixtures" / "dpbench_results.json").read_text()
)
print(f"DP-Bench NID: {dp_baseline['averages']['nid']}")

# Load OmniDocBench baseline
omni_baseline = json.loads(
    (files("doc_bench") / "fixtures" / "omnidocbench_results.json").read_text()
)
print(f"OmniDocBench NID: {omni_baseline['averages']['nid']}")
```

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
