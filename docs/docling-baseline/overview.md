# docling-baseline Overview

The `docling-baseline` fixture generator is a standalone document-parser
baseline tool that is vendored verbatim into this repository at
[`src/docling_baseline/`](../../src/docling_baseline/). It produces the
reference baseline-score fixtures that the `doc-bench` package ships in its
wheel. This document explains what the generator is, why it lives in this repo,
how it relates to `doc-bench`, and the single hard rule that governs it: it must
never enter the `doc-bench` wheel.

## Table of contents

- [What it is](#what-it-is)
- [Why it is vendored](#why-it-is-vendored)
- [Generator produces, doc-bench consumes](#generator-produces-doc-bench-consumes)
- [Data flow](#data-flow)
- [The hard rule: never in the wheel](#the-hard-rule-never-in-the-wheel)
- [Related documents](#related-documents)

## What it is

`docling-baseline` runs the [Docling](https://github.com/DS4SD/docling) document
parser over benchmark PDFs and images, converts Docling's output into the
standardized `parser_output` schema, computes six parsing-quality metrics, and
writes baseline-score JSON files. Those JSON files are the reference fixtures
consumed by `doc-bench`.

The six metrics it computes (all normalized to `[0, 1]`, where `1.0` is
perfect) are:

| Metric | Measures |
| --- | --- |
| NID | Text similarity (normalized indel distance) |
| TEDS | Table structure |
| MHS | Heading hierarchy |
| ARD | Reading order |
| BLEU | Text n-gram overlap |
| METEOR | Text alignment / overlap |

The generator is the **only** component in this repository that depends on
Docling. `doc-bench` itself has no Docling adapter; the adapter lives at
[`src/docling_baseline/adapters/docling.py`](../../src/docling_baseline/adapters/docling.py).

## Why it is vendored

The baseline fixtures that `doc-bench` ships are reference scores against which
real parser runs are compared. Those numbers must be **reproducible** and have
clear **provenance**: anyone should be able to see exactly which tool and which
inputs produced them. Vendoring the generator verbatim into
[`src/docling_baseline/`](../../src/docling_baseline/) keeps the producing code
under version control alongside the fixtures it produces, so a regeneration is
always traceable to a specific commit.

A read-only upstream reference copy is kept at
[`references/docling-baseline/`](../../references/docling-baseline/) for
comparison and provenance. Nothing in the repository imports from that reference
copy; it exists purely as the authoritative source of truth for the vendored
code and its dependency list.

## Generator produces, doc-bench consumes

The relationship is strictly one-directional:

- The **generator** (`src/docling_baseline/`) *produces* the
  `*_results.json` baseline-score files.
- **doc-bench** (`src/doc_bench/`) *consumes and ships* them. They are bundled
  in the `doc-bench` wheel under
  [`src/doc_bench/fixtures/`](../../src/doc_bench/fixtures/):
  - `dpbench_results.json`
  - `omnidocbench_results.json`
  - `ato_bench_results.json`

`doc-bench` never imports or executes the generator at runtime; it only reads
the JSON fixtures the generator left behind.

## Data flow

```
  PDFs / images + per-doc ground truth
                |
                v
        +-----------------+
        |  Docling parse  |   src/docling_baseline/adapters/docling.py
        +-----------------+
                |
                v
          parser_output           schemas/parser_output.schema.json
                |
                v
        +-----------------+
        |   6 metrics     |   metrics/ (nid, table_teds, mhs,
        | (NID, TEDS,...) |             reading_order, text_similarity)
        +-----------------+
                |
                v
         *_results.json          generator output
                |
                v
  bundled in doc-bench fixtures   src/doc_bench/fixtures/*_results.json
```

## The hard rule: never in the wheel

The `doc-bench` wheel must **never** contain `docling_baseline`. This is the
number-one hard constraint for the vendored generator. It is enforced
structurally, not by convention:

- `[tool.hatch.build.targets.wheel]` sets `packages = ["src/doc_bench"]`.
- `[tool.hatch.build]` `include` globs are scoped to `src/doc_bench/**`.
- `src/docling_baseline/` is a sibling directory that no glob ever matches, so
  it cannot be packaged.

This structural guarantee is verified end-to-end by the wheel-leak guard. See
[guards.md](./guards.md) for details.

## Related documents

- [architecture.md](./architecture.md) -- module layout, runner internals, CLI
  command table.
- [regenerating-fixtures.md](./regenerating-fixtures.md) -- the
  `make regen-fixtures` workflow and the underlying generator invocation.
- [guards.md](./guards.md) -- the drift guard and the wheel-leak guard.
- [adding-a-dataset.md](./adding-a-dataset.md) -- step-by-step guide to adding a
  new benchmark document, using the ATO `1371-6.1997` case study.
