# doc-bench

Deterministic, CPU-only, secret-free evaluation framework for document-parsing systems.

doc-bench grades pre-computed parser predictions against public benchmarks (DP-Bench, OmniDocBench, ATO-Bench) using **NED + TEDS** deterministic metrics -- with no LLM judge, no GPU, and no API keys. Same input, same score, every machine. NED scores are directly comparable to the [OmniDocBench leaderboard](https://arxiv.org/abs/2412.07626).

> Full documentation lives in [docs/README.md](docs/README.md). This page is the quickstart.

## Quick Start

```bash
# Install from the wheel (bundled fixtures + schema, no download needed)
pip install dist/doc_bench-0.1.0-py3-none-any.whl

# Validate the install against the 33 bundled fixtures
doc-bench-smoke-test

# Grade your pre-computed predictions
doc-bench --dataset dp_bench --predictions ./predictions --output-dir ./results
```

From a source checkout, prefix commands with `uv run` (for example `uv run doc-bench-smoke-test`).

## Installation

### From source (development)

```bash
git clone <repo>
cd doc-bench
uv sync                      # core deps only; never installs the heavy generator stack

uv build --wheel             # build the distributable wheel
pip install dist/doc_bench-0.1.0-py3-none-any.whl
```

### Optional extras

```bash
uv sync --extra docling      # optional Docling runtime parser
uv sync --extra bedrock      # AWS Bedrock support
```

No first-run setup is required. The NED + TEDS metrics need no data downloads.

## How it works

doc-bench runs **file-based evaluation**: your parser runs separately and writes one
`<doc_id>.json` prediction per document; doc-bench scores those files against ground truth.
Run the parser once, re-grade for free.

```
   ground truth (benchmark)            your predictions (<doc_id>.json)
                  \                     /
                   \                   /
                    ▼                 ▼
              doc-bench deterministic metrics
                          │
                          ▼
        results/*.csv  (per-document)   results/*.json  (averages)
        results/*_rejected.csv          (missing / invalid predictions)
```

Predictions must conform to the bundled `ParserOutput` schema -- see
[docs/doc-bench/parser-output.md](docs/doc-bench/parser-output.md). Predictions that are
missing, malformed, or schema-invalid become tracked **rejections** (reason codes
`MISSING_PREDICTION`, `INVALID_JSON`, `INVALID_SCHEMA`, `EVALUATION_ERROR`) instead of
crashing the run.

### Three-step workflow

```bash
# 1. Export the benchmark documents (defines the <doc_id> filenames)
doc-bench-dump-dataset --dataset dp_bench --output ./pdfs --limit 10

# 2. Run YOUR parser over ./pdfs, writing ./predictions/<doc_id>.json
#    (each file must validate against parser_output.schema.json)

# 3. Grade the predictions
doc-bench --dataset dp_bench --predictions ./predictions --output-dir ./results
```

See [docs/file-based-evaluation.md](docs/file-based-evaluation.md) for the full workflow and
[docs/document-identity.md](docs/document-identity.md) for the `<doc_id>.json` naming rule.

## Bundled fixtures and baselines

The wheel ships **33 documents** under `doc_bench/fixtures/`, so the smoke test and examples
need no downloads:

| Dataset | Bundled docs | Notes |
|---------|-------------:|-------|
| DP-Bench | 16 | Paragraph (10), Caption (2), Chart (1), Heading1 (2), Index (1); includes 4 deliberately hard PDFs. |
| OmniDocBench | 16 | academic_literature (8), book (2), colorful_textbook (2), exam_paper (2), PPT2PDF (2). |
| ATO-Bench | 1 | `1371-6.1997`, a 2-page individual income tax return. |

All three are gradable via `doc-bench --dataset {dp_bench,omnidocbench,ato_bench}`. ATO-Bench
loads its ground truth from the bundled fixtures, so it needs no `--data-dir`:

```bash
doc-bench --dataset ato_bench --predictions ./predictions --output-dir ./results
```

Reference baseline scores ship alongside them (`doc_bench/fixtures/{dpbench,omnidocbench,ato_bench}_results.json`)
and can be loaded programmatically:

```python
from importlib.resources import files
import json

baseline = json.loads(
    (files("doc_bench") / "fixtures" / "dpbench_results.json").read_text()
)
print(baseline["averages"])
```

See [docs/doc-bench/datasets.md](docs/doc-bench/datasets.md) for composition, full-dataset
sources, and per-dataset limitations.

## Metrics

| Metric | Measures |
|--------|----------|
| NED | Text similarity (character-level Normalized Edit Distance, OmniDocBench-compatible) |
| TEDS / TEDS-S | Table structure (tree edit distance) |

All scores are in `[0.0, 1.0]`, 1.0 = perfect. NED scores are directly comparable to the
OmniDocBench leaderboard. Details and known caveats in
[docs/doc-bench/metrics.md](docs/doc-bench/metrics.md).

The output CSV contains columns `query_id, error, ned, teds, teds_s`.

## Regenerating baseline fixtures (maintainers)

The baseline-score fixtures are produced by a vendored copy of the **docling-baseline** generator
at [`src/docling_baseline/`](src/docling_baseline/). It pulls a heavy stack (`docling` brings a
full torch tree), so it is confined to a dev-only `generator` dependency-group and is **never**
shipped in the wheel and **never** a runtime dependency. A plain `uv sync` never installs it.

```bash
make regen-fixtures                  # regenerate DP-Bench + OmniDocBench in place
make regen-fixtures DATASET=dp_bench # one dataset
```

This runs the generator on Python 3.13 via `uv run --python 3.13 --group generator`; doc-bench
core stays `requires-python >=3.12`. Two CI guards protect the arrangement:

- **drift guard** (`tests/test_metric_drift_guard.py`, fast suite) -- vendored metric/schema
  copies must stay byte-identical to doc-bench's, modulo a pinned allow-list.
- **wheel-leak guard** (`tests/test_wheel_no_generator_leak.py`, `make test-build`) -- the
  built wheel must contain zero `docling_baseline` paths.

`make ci` runs both. Full details: [docs/docling-baseline/](docs/docling-baseline/overview.md)
and [docs/runbook.md](docs/runbook.md).

## Project layout

```
.
├── README.md                     # this file
├── pyproject.toml                # package + dev-only [dependency-groups] generator
├── Makefile                      # install / lint / test / ci / regen-fixtures
├── docs/                         # the documentation book (start at docs/README.md)
├── examples/                     # runnable scripts
├── notebooks/                    # Jupyter walkthroughs
├── scripts/                      # dataset + maintenance utilities
├── src/doc_bench/                # the shipped package
│   ├── fixtures/                 # 33 bundled docs + schema + baselines (bundled in wheel)
│   ├── datasets/  adapters/  metrics/  runners/  cli/
│   └── __init__.py               # get_bundled_schema_path()
├── src/docling_baseline/         # vendored generator (DEV-ONLY, never in the wheel)
├── references/                   # read-only upstream provenance (never imported)
│   ├── docling-baseline/         # docling-baseline audit trail
│   └── omnidocbench/             # OmniDocBench NED/ASM audit trail (Apache-2.0)
└── tests/                        # unit + integration + the two guards
```

## Development

```bash
make install      # uv sync
make lint         # ruff check + black --check
make typecheck    # mypy src
make test         # fast pytest suite (includes the drift guard)
make test-build   # the marked wheel-leak guard
make ci           # lint + typecheck + test + test-build
```

The vendored `src/docling_baseline/` is intentionally exempt from ruff/mypy/black/coverage
(it is verbatim third-party code). `references/omnidocbench/` is similarly exempt (audit trail).

## Documentation

Start at **[docs/README.md](docs/README.md)** for the full table of contents. Highlights:

- [doc-bench overview](docs/doc-bench/overview.md) · [CLI reference](docs/doc-bench/cli-reference.md) · [metrics](docs/doc-bench/metrics.md) · [datasets](docs/doc-bench/datasets.md) · [prediction schema](docs/doc-bench/parser-output.md)
- [docling-baseline generator](docs/docling-baseline/overview.md) · [regenerating fixtures](docs/docling-baseline/regenerating-fixtures.md) · [guards](docs/docling-baseline/guards.md) · [adding a dataset](docs/docling-baseline/adding-a-dataset.md)
- [examples](examples/README.md) · [notebooks](notebooks/README.md)
