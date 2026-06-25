# doc-bench

Deterministic, CPU-only, secret-free evaluation framework for document-parsing systems.

doc-bench grades pre-computed parser predictions against public benchmarks (DP-Bench, OmniDocBench, ATO-Bench) using **NED + TEDS** deterministic metrics -- with no LLM judge, no GPU, and no API keys. Same input, same score, every machine. NED scores are directly comparable to the [OmniDocBench leaderboard](https://arxiv.org/abs/2412.07626).

> Full documentation lives in [docs/README.md](docs/README.md). This page is the quickstart.

## Quick Start

```bash
# Install from the wheel (bundled fixtures + schema, no download needed)
pip install dist/doc_bench-0.1.0-py3-none-any.whl

# Validate the install against the 11 bundled fixtures
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

The smoke test and bundled baselines cover **11 documents** (the stratified set in
`doc_bench/fixtures/manifest.json`), so the smoke test and examples need no downloads:

| Dataset | Bundled docs | Notes |
|---------|-------------:|-------|
| DP-Bench | 5 | Paragraph (4), Chart (1). |
| OmniDocBench | 5 | Stratified one-per-doc_type subset: academic_literature, book, colorful_textbook, exam_paper, PPT2PDF (1 each). |
| ATO-Bench | 1 | `1371-6.1997`, a 2-page individual income tax return. |

> The OmniDocBench fixture directory ships 11 page images on disk; `doc-bench --dataset
> omnidocbench` grades all 11, while the smoke test and bundled baselines use the 5-page
> stratified subset above.

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

| Metric | Measures | Implementation |
|--------|----------|----------------|
| NED | Whole-page text similarity (character-level Normalized Edit Distance, OmniDocBench-compatible) | [`metrics/parsing/ned.py`](src/doc_bench/metrics/parsing/ned.py) |
| TEDS | Table structure **and** cell content (tree edit distance) | [`metrics/parsing/table_teds.py`](src/doc_bench/metrics/parsing/table_teds.py) |
| TEDS-S | Table structure only (cells emptied before comparison) | [`metrics/parsing/table_teds.py`](src/doc_bench/metrics/parsing/table_teds.py) |

All three scores are in `[0.0, 1.0]`, where `1.0` is a perfect match. Every metric is a pure
function of `(ground_truth, prediction)` strings — no randomness, no model calls — so the same
inputs always produce the same score. Full derivations and caveats live in
[docs/doc-bench/metrics.md](docs/doc-bench/metrics.md); the essentials follow.

### NED (text)

NED scores the full page text and is the metric directly comparable to the
[OmniDocBench leaderboard](https://arxiv.org/abs/2412.07626). Computation, per document:

1. **Strip equations from the prediction first.** LaTeX spans — `$$…$$`, `$…$`, `\[…\]`,
   `\(…\)` — are removed before scoring. OmniDocBench gold carries no equation text, so a parser
   that emits LaTeX (MinerU, Nougat, …) would otherwise look 2–6× too long and tank its NED even
   when the surrounding text is correct. See `_strip_equations` in
   [`runners/run_parsing_eval.py`](src/doc_bench/runners/run_parsing_eval.py).
2. **Normalize both strings identically** — Unicode NFC, then collapse every whitespace run
   (`\s+`) to a single space and strip ends. This stops paragraph-break vs. single-space
   differences from inflating the distance.
3. **Score** with character-level Levenshtein distance:

   ```
   NED        = Levenshtein.distance(gt, pred) / max(len(gt), len(pred))
   ned_score  = 1 - NED                              # reported value, in [0, 1]
   ```

   The `python-Levenshtein` package is used (not `rapidfuzz`) to match the OmniDocBench canonical
   source byte-for-byte. Empty-string rule: both empty → `1.0`; exactly one empty → `0.0`.

### TEDS / TEDS-S (tables)

TEDS compares the **table tree** rather than flat text. Per document:

1. **Extract** GFM pipe tables from the prediction markdown (and the gold markdown, when the gold
   carries no pre-built HTML table), skipping the `|---|` separator row.
2. **Convert** each table to HTML and wrap it in `<html><body>…</body></html>`. `<th>` is
   rewritten to `<td>` so header placement alone does not penalize the score.
3. **Tree-edit-distance** the two table trees with `APTED`, then normalize by the larger node
   count:

   ```
   TEDS = 1 - APTED_edit_distance(pred_tree, gt_tree) / max(n_nodes_pred, n_nodes_gt)
   ```

   - **TEDS** (`structure_only=False`) — node rename cost is `1.0` when `tag`, `colspan`, or
     `rowspan` differ; for matching `<td>` cells the cost is the normalized Levenshtein distance
     of the (HTML-unescaped, `<br>`→newline, whitespace-collapsed) cell text. So structure **and**
     content both count.
   - **TEDS-S** (`structure_only=True`) — cell text is dropped before comparison, isolating
     structural fidelity (rows, columns, spans).

   Empty-table rules, in order: gold has **no** table → metric is `None` and the runner records
   `0.0`; gold has a table but the prediction has none → `0.0`; either rendered tree is empty →
   `0.0`. This is why a page can post a high NED yet `TEDS = 0.0` — it simply has no scorable
   table on one side (the bundled OmniDocBench baseline shows exactly this on its no-table pages).

### Per-document output and averaging

Each graded document is one row in the results CSV with columns
`query_id, error, ned_similarity, teds, teds_s` (values rounded to 4 decimals). The summary
`*.json` averages are the **unweighted means over rows with no `error`** — rejected or errored
documents are excluded from the means and counted separately under the rejection reason codes.

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
│   ├── fixtures/                 # 11 bundled baseline docs + schema + baselines (bundled in wheel)
│   ├── datasets/  adapters/  metrics/  runners/  cli/
│   └── __init__.py               # get_bundled_schema_path()
├── src/docling_baseline/         # vendored generator (DEV-ONLY, never in the wheel)
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
