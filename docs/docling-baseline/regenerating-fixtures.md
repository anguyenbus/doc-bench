# Regenerating Baseline Fixtures

This guide describes how to regenerate the baseline-score fixtures that
`doc-bench` ships, using the vendored `docling-baseline` generator. For what the
generator is and how it fits in, start with [overview.md](./overview.md).

## Table of contents

- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [What the workflow does](#what-the-workflow-does)
- [The underlying generator invocation](#the-underlying-generator-invocation)
- [Files produced and copied](#files-produced-and-copied)
- [Verify with the smoke test](#verify-with-the-smoke-test)
- [Known caveat: dataset naming](#known-caveat-dataset-naming)

## Prerequisites

- The generator's heavy dependencies (docling, docling-core, apted, rapidfuzz,
  beautifulsoup4, lxml, nltk, sacrebleu, jsonschema, polars, click, pydantic,
  beartype) live in the dev-only `generator` dependency group in
  [`pyproject.toml`](../../pyproject.toml). They are **not** in
  `[project.dependencies]` and **not** in the `[docling]` runtime extra. A plain
  `uv sync` (no group) does **not** install them. `docling` brings a full torch
  tree, so the first run downloads a large dependency set.
- The generator runs on **Python 3.13** (its upstream requires `>=3.13`).
  `doc-bench` core stays at `requires-python >=3.12`. The Makefile provisions
  3.13 automatically via `uv`.

## Quick start

Regenerate all in-scope datasets (DP-Bench and OmniDocBench) in place against
[`src/doc_bench/fixtures/`](../../src/doc_bench/fixtures/):

```bash
make regen-fixtures
```

Regenerate a single dataset with the `DATASET=` override:

```bash
make regen-fixtures DATASET=dp_bench
```

## What the workflow does

`make regen-fixtures` is backed by
[`scripts/regenerate_fixtures.py`](../../scripts/regenerate_fixtures.py). It:

1. Runs the vendored generator as a module for each in-scope dataset.
2. Runs **in place** against the fixtures directory: inputs and outputs are
   co-located in [`src/doc_bench/fixtures/`](../../src/doc_bench/fixtures/), so
   the copy step is a self-copy in normal operation while still applying the
   rename mapping below.
3. Copies the produced `*_results.json` files into the fixtures directory,
   applying the DP-Bench rename.

The in-scope datasets for this script are DP-Bench and OmniDocBench. ATO-bench
is regenerated through the generator CLI directly (see
[adding-a-dataset.md](./adding-a-dataset.md)), not through this script.

## The underlying generator invocation

The Makefile target runs:

```bash
DATASET="$(DATASET)" uv run --python 3.13 --group generator python scripts/regenerate_fixtures.py
```

- `uv run --python 3.13` auto-provisions Python 3.13.
- `--group generator` installs the dev-only generator dependencies for this run
  only.
- The script invokes the generator **as a module**, e.g.
  `python -m docling_baseline.cli <dataset> <fixtures_dir>`, rather than via any
  registered console script. The generator is **not** registered as a
  `doc-bench` console script.

## Files produced and copied

The generator writes `<dataset>_results.json` (and refreshes `manifest.json`)
into the fixtures directory. On copy, the script applies this mapping:

| Generator output | doc-bench fixture |
| --- | --- |
| `dp_bench_results.json` | `dpbench_results.json` (renamed) |
| `omnidocbench_results.json` | `omnidocbench_results.json` (unchanged) |

DP-Bench is renamed to `doc-bench`'s canonical fixture name
`dpbench_results.json`; OmniDocBench passes through unchanged. The refreshed
`manifest.json` is also placed in the fixtures directory.

## Verify with the smoke test

After regenerating, verify the bundled fixtures load and behave correctly:

```bash
uv run doc-bench-smoke-test
```

This confirms the regenerated `*_results.json` fixtures are consumable by
`doc-bench` before you commit them.

## Known caveat: dataset naming

There is a naming mismatch to be aware of when invoking the generator directly:

- [`scripts/regenerate_fixtures.py`](../../scripts/regenerate_fixtures.py)
  currently passes dataset names with **underscores** (e.g. `dp_bench`).
- The generator CLI commands use **hyphens** (e.g. `dp-bench`,
  `omnidocbench`, `ato-bench`, `all`).

Treat this as a **known caveat to verify** before relying on a direct module
invocation. This document does not claim the mismatch is fixed; confirm the
exact command name accepted by the CLI (see the command table in
[architecture.md](./architecture.md)) for any direct invocation.
