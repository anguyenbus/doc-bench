# doc-bench CLI Reference

Complete reference for every `doc-bench-*` console command shipped by the wheel.

## Table of Contents

- [Command summary](#command-summary)
- [`doc-bench` — grade predictions](#doc-bench--grade-predictions)
- [`doc-bench-smoke-test` — validate the install](#doc-bench-smoke-test--validate-the-install)
- [`doc-bench-dump-dataset` — export documents](#doc-bench-dump-dataset--export-documents)
- [`doc-bench-download` — fetch full datasets](#doc-bench-download--fetch-full-datasets)
- [`doc-bench-list-datasets` — list datasets and cache](#doc-bench-list-datasets--list-datasets-and-cache)
- [`doc-bench-setup` — provision NLTK data](#doc-bench-setup--provision-nltk-data)
- [Environment variables](#environment-variables)

## Command summary

All commands are registered as console scripts in [`pyproject.toml`](../../pyproject.toml) under `[project.scripts]`.

| Command | Purpose | Entry point |
|---------|---------|-------------|
| `doc-bench` | Grade pre-computed predictions against a benchmark | `doc_bench.runners.run_parsing_eval:main` |
| `doc-bench-smoke-test` | Validate the install against bundled fixtures | `doc_bench.cli.smoke_test:main` |
| `doc-bench-dump-dataset` | Export benchmark documents as `<doc_id>.pdf` + manifest | `doc_bench.cli.dump_dataset:main` |
| `doc-bench-download` | Download a version-pinned full dataset to cache | `doc_bench.cli.download:main` |
| `doc-bench-list-datasets` | List available datasets and local cache status | `doc_bench.cli.list_datasets:main` |
| `doc-bench-setup` | Provision NLTK corpora required by METEOR | `doc_bench.cli.setup:main` |

When running from source rather than an installed wheel, prefix any command with `uv run` (for example `uv run doc-bench-smoke-test`).

## `doc-bench` — grade predictions

Grades a directory of pre-computed prediction files against a benchmark's ground truth. This is the primary evaluation entry point and runs in **file-based mode**: your parser runs separately and writes `<doc_id>.json` files; `doc-bench` only scores them.

```bash
doc-bench --dataset dp_bench --predictions ./predictions --output-dir ./results
```

ATO-Bench grades against the bundled fixtures by default, so no ground-truth path is needed:

```bash
doc-bench --dataset ato_bench --predictions ./predictions --output-dir ./results
```

### Options

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--dataset` | yes | — | Benchmark to grade against. Choices: `omnidocbench`, `dp_bench`, `ato_bench`. For `ato_bench` the ground truth defaults to the bundled fixtures (no `--data-dir` needed). |
| `--predictions <dir>` | yes | — | Directory of prediction JSON files named `<doc_id>.json`, each conforming to [`parser_output.schema.json`](parser-output.md). |
| `--output-dir <dir>` | no | `results` | Directory for the CSV/JSON result files (created if missing). |
| `--data-dir <dir>` | no | from `eval_config.yaml` | Override the ground-truth dataset location. Expected structure — DP-Bench: `reference.json` + `pdfs/`; OmniDocBench: `OmniDocBench.json` + `images/`. |
| `--limit <int>` | no | all | Process only the first N items (for quick iteration). |
| `--max-rejection-rate <float>` | no | `0.5` | Acceptable rejection rate in `[0.0, 1.0]`. Exceeding it prints a warning. `0` means never warn. Also settable via `DOC_BENCH_MAX_REJECTION_RATE`. |

### Behavior notes

- The predictions directory must exist or the command exits non-zero.
- Ground-truth location comes from [`eval_config.yaml`](../../eval_config.yaml) unless `--data-dir` overrides it.
- Predictions that are missing, malformed, or schema-invalid become **rejections** rather than crashing the run. See [Rejection handling](overview.md#rejection-handling) and the metrics doc.

### Outputs

Written to `--output-dir` with a timestamp:

- `<dataset>_predictions_results_<ts>.csv` — per-document metrics
- `<dataset>_predictions_results_<ts>.json` — summary with averages and counts
- `<dataset>_predictions_rejected_<ts>.csv` — one row per rejected document with a reason code

## `doc-bench-smoke-test` — validate the install

Runs the evaluation pipeline against the bundled fixtures (33 documents) and reports a clean pass/fail. Designed to finish in seconds and to be wired into CI. It validates that fixtures load, predictions (if provided) schema-validate, and the rejection rate stays under threshold — it does **not** assert quality thresholds.

```bash
doc-bench-smoke-test
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--data <dir>` | bundled `doc_bench/fixtures/` | Fixtures directory to test against. |
| `--predictions <dir>` | none | Optional predictions directory to grade during the smoke test. |
| `--schema <file>` | bundled schema | Override the parser-output schema used for validation. |
| `--threshold <float>` | `10.0` | Rejection-rate percentage above which the smoke test fails. |

Exit code is `0` on pass, non-zero on fail. Output includes a per-document-type breakdown (for example `individual_income_tax_return: 0/1 (0.0%)`).

## `doc-bench-dump-dataset` — export documents

Exports a benchmark's source documents as `<doc_id>.pdf` files plus a `manifest.json`, so an external parser can consume them and you know exactly which `<doc_id>.json` filenames to write back.

```bash
doc-bench-dump-dataset --dataset dp_bench --output ./pdfs --limit 10
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--dataset` | — | Dataset to export. |
| `--output <dir>` | — | Destination directory for the exported PDFs and manifest. |
| `--config <file>` | `eval_config.yaml` | Config file resolving the dataset location. |
| `--limit <int>` | all | Export only the first N documents. |

The exported file stems define the document identity contract: a prediction for `01030000000001.pdf` must be named `01030000000001.json`. See [document-identity.md](../document-identity.md).

## `doc-bench-download` — fetch full datasets

Downloads a version-pinned full dataset into a version-keyed cache. All downloads are explicitly versioned; there is no "latest".

```bash
doc-bench-download --dataset omnidocbench --version <version>
```

### Options

| Flag | Description |
|------|-------------|
| `--dataset` | Dataset to download. |
| `--version` | Explicit dataset version (required; no implicit "latest"). |
| `--cache-dir <dir>` | Override the cache root (default `~/.cache/doc-bench`, or `$DOC_BENCH_CACHE`). |

Re-running with an already-cached version skips the download. Use `doc-bench-list-datasets` to inspect what is cached.

## `doc-bench-list-datasets` — list datasets and cache

Lists available datasets/versions and which are present in the local cache.

```bash
doc-bench-list-datasets
```

### Options

| Flag | Description |
|------|-------------|
| `--manifest <file>` | Override the dataset manifest used to enumerate datasets. |
| `--cache-dir <dir>` | Override the cache directory inspected for downloaded sets. |

## `doc-bench-setup` — provision NLTK data

Provisions the NLTK corpora that the METEOR metric requires (for example `wordnet`/`omw-1.4`). Run once after install if METEOR returns 0.

```bash
doc-bench-setup
```

### Options

| Flag | Description |
|------|-------------|
| `--nltk-data-dir <dir>` | Target directory for the downloaded NLTK data. |
| `--force` | Re-download even if the corpora are already present. |

## Environment variables

| Variable | Used by | Effect |
|----------|---------|--------|
| `DOC_BENCH_MAX_REJECTION_RATE` | `doc-bench` | Default rejection-rate threshold when `--max-rejection-rate` is omitted. |
| `DOC_BENCH_CACHE` | `doc-bench-download`, `doc-bench-list-datasets` | Overrides the dataset cache root. |
