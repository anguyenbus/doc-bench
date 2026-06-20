# doc-bench Documentation

This is the documentation "book" for the doc-bench project. It covers two things that live in one repository but ship very differently:

- **doc-bench** — the deterministic document-parser evaluation framework, distributed as a pip wheel.
- **docling-baseline** — the vendored generator that *produces* the baseline-score fixtures doc-bench ships. It is dev-only and never enters the wheel.

If you are new, read [doc-bench/overview.md](doc-bench/overview.md) first, then run the [smoke test](doc-bench/cli-reference.md#doc-bench-smoke-test--validate-the-install).

## Table of Contents

### doc-bench (the evaluation framework)

| Doc | What it covers |
|-----|----------------|
| [doc-bench/overview.md](doc-bench/overview.md) | What doc-bench is, the file-based grading concept, architecture, workflow. |
| [doc-bench/cli-reference.md](doc-bench/cli-reference.md) | Every `doc-bench-*` command and its flags. |
| [doc-bench/metrics.md](doc-bench/metrics.md) | The six deterministic metrics (NID, TEDS, MHS, ARD, BLEU, METEOR). |
| [doc-bench/datasets.md](doc-bench/datasets.md) | DP-Bench, OmniDocBench, ATO-Bench; bundled fixtures and baselines. |
| [doc-bench/parser-output.md](doc-bench/parser-output.md) | The prediction contract (`ParserOutput` schema). |
| [file-based-evaluation.md](file-based-evaluation.md) | The dump → predict → grade workflow in depth. |
| [document-identity.md](document-identity.md) | The `<doc_id>.json` naming rule for predictions. |

### docling-baseline (the fixture generator)

| Doc | What it covers |
|-----|----------------|
| [docling-baseline/overview.md](docling-baseline/overview.md) | What the generator is, why it is vendored, the never-in-the-wheel rule. |
| [docling-baseline/regenerating-fixtures.md](docling-baseline/regenerating-fixtures.md) | The `make regen-fixtures` workflow. |
| [docling-baseline/architecture.md](docling-baseline/architecture.md) | Module layout, runner pipeline, I/O contracts, CLI. |
| [docling-baseline/guards.md](docling-baseline/guards.md) | The drift guard and wheel-leak guard, and what to do when they fire. |
| [docling-baseline/adding-a-dataset.md](docling-baseline/adding-a-dataset.md) | How to add a new benchmark document (ATO case study). |

### Hands-on

| Resource | What it is |
|----------|------------|
| [../examples/README.md](../examples/README.md) | Runnable scripts: grade predictions, build a valid prediction, read baselines. |
| [../notebooks/README.md](../notebooks/README.md) | Jupyter notebooks: explore fixtures, understand metrics, grade-and-compare. |
| [runbook.md](runbook.md) | Operational runbook: provenance, isolation guarantee, guard remediation. |

## Two-package mental model

```
                 docling-baseline  (dev-only, Python 3.13, heavy: docling + torch)
                 produces baseline-score fixtures
                          │
                          ▼
   src/doc_bench/fixtures/*_results.json , manifest.json , PDFs/images, ground truth
                          │  (bundled into the wheel)
                          ▼
                 doc-bench  (the shipped wheel, Python >=3.12, light)
                 grades your predictions against these fixtures
```

The arrow only points one way. doc-bench never imports docling-baseline, and the wheel never contains it — enforced by the [guards](docling-baseline/guards.md).

## Conventions in this book

- All shell snippets are copy-pasteable. From a source checkout, prefix commands with `uv run`.
- Repo files are linked by relative path; sibling docs by relative Markdown links.
- Numbers (document counts, baseline scores) reflect the bundled fixture set: **33 documents** = 16 DP-Bench + 16 OmniDocBench + 1 ATO-Bench.
