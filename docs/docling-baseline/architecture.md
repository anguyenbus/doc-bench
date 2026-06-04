# docling-baseline Architecture

This document describes the internal structure of the vendored generator at
[`src/docling_baseline/`](../../src/docling_baseline/): its module layout, how a
runner processes a dataset, the runner I/O contracts (with the ATO-bench layout
in detail), the CLI command surface, and why the generator carries its own copy
of the metric code. For the big picture, see [overview.md](./overview.md).

## Table of contents

- [Module layout](#module-layout)
- [How a runner works](#how-a-runner-works)
- [Runner I/O contracts](#runner-io-contracts)
  - [ATO-bench layout](#ato-bench-layout)
- [CLI commands](#cli-commands)
- [Vendored metric copy and the drift guard](#vendored-metric-copy-and-the-drift-guard)

## Module layout

Under [`src/docling_baseline/`](../../src/docling_baseline/):

| Path | Responsibility |
| --- | --- |
| [`adapters/docling.py`](../../src/docling_baseline/adapters/docling.py) | The Docling adapter. `doc-bench` has no Docling adapter of its own. |
| [`converters/markdown.py`](../../src/docling_baseline/converters/markdown.py) | Converts `parser_output` into markdown for metric scoring. |
| [`metrics/nid.py`](../../src/docling_baseline/metrics/nid.py) | NID (text similarity). |
| [`metrics/mhs.py`](../../src/docling_baseline/metrics/mhs.py) | MHS (heading hierarchy). |
| [`metrics/table_teds.py`](../../src/docling_baseline/metrics/table_teds.py) | TEDS (table structure). |
| [`metrics/reading_order.py`](../../src/docling_baseline/metrics/reading_order.py) | ARD (reading order). |
| [`metrics/text_similarity.py`](../../src/docling_baseline/metrics/text_similarity.py) | BLEU and METEOR. |
| [`runners/base.py`](../../src/docling_baseline/runners/base.py) | Shared runner behavior. |
| [`runners/dp_bench.py`](../../src/docling_baseline/runners/dp_bench.py) | DP-Bench runner. |
| [`runners/omnidocbench.py`](../../src/docling_baseline/runners/omnidocbench.py) | OmniDocBench runner; hosts the shared gold-text builder. |
| [`runners/ato_bench.py`](../../src/docling_baseline/runners/ato_bench.py) | ATO-bench runner. |
| [`runners/table_utils.py`](../../src/docling_baseline/runners/table_utils.py) | Table helpers. |
| [`schemas/parser_output.schema.json`](../../src/docling_baseline/schemas/parser_output.schema.json) | The standardized `parser_output` schema. |
| [`cli.py`](../../src/docling_baseline/cli.py) | The Click command group. |

## How a runner works

Each runner follows the same pipeline:

1. **Read the manifest.** Load `manifest.json` from the fixtures directory. The
   manifest has per-dataset sections (ATO, OmniDocBench, DP-Bench) listing the
   documents to score.
2. **For each document:**
   1. Run Docling over the PDF/image
      ([`adapters/docling.py`](../../src/docling_baseline/adapters/docling.py)).
   2. Convert the parser output to markdown
      ([`converters/markdown.py`](../../src/docling_baseline/converters/markdown.py)).
   3. Compute the six metrics against the ground truth
      ([`metrics/`](../../src/docling_baseline/metrics/)).
3. **Aggregate** per-document scores into dataset-level averages and write the
   `*_results.json` output.

## Runner I/O contracts

All runners read `manifest.json` from the fixtures directory and write a
`<dataset>_results.json` file. The manifest's per-dataset section lists the docs
for that dataset.

### ATO-bench layout

The ATO-bench runner
([`runners/ato_bench.py`](../../src/docling_baseline/runners/ato_bench.py)) has
the most structured contract. Per document it expects:

- A **manifest entry** of the form:
  ```json
  { "doc_id": "...", "pdf": "...", "doc_type": "...", "pages": [ ... ] }
  ```
- The **PDF** at `<fixtures_dir>/ato_bench/<pdf>`.
- **Per-page ground-truth files** at
  `<fixtures_dir>/ato_bench/<doc_id>_p1.json`, `_p2.json`, ... -- one file per
  page. Each file is a **single page dict** in OmniDocBench `layout_dets`
  format, with keys `layout_dets`, `extra`, and `page_info`.

The runner runs Docling on the **whole PDF**, combines the per-page gold text
into one document-level gold string, and scores at the **document level** (not
per page).

## CLI commands

The CLI ([`cli.py`](../../src/docling_baseline/cli.py)) is a Click group.
Command names use **hyphens** (Click converts the underlying function names from
underscores to hyphens). Invoke the CLI as a **module**:

```bash
python -m docling_baseline.cli <command> <fixtures_dir> --output <file>
```

| Command | Purpose | Positional arg | Output option |
| --- | --- | --- | --- |
| `dp-bench` | Run the DP-Bench runner. | `fixtures_dir` | `--output` / `-o` |
| `omnidocbench` | Run the OmniDocBench runner. | `fixtures_dir` | `--output` / `-o` |
| `ato-bench` | Run the ATO-bench runner. | `fixtures_dir` | `--output` / `-o` |
| `all` | Run all runners. | `fixtures_dir` | `--output-dir` / `-o` |

Example:

```bash
python -m docling_baseline.cli ato-bench <fixtures_dir> --output <file>
```

The generator is **not** registered as a `doc-bench` console script; it is only
ever invoked as a module.

## Vendored metric copy and the drift guard

The generator carries its **own copy** of the metric code and the
`parser_output` schema. `doc-bench` ships a parallel copy under
[`src/doc_bench/metrics/parsing/`](../../src/doc_bench/metrics/parsing/) and
[`src/doc_bench/fixtures/parser_output.schema.json`](../../src/doc_bench/fixtures/parser_output.schema.json).
Keeping two copies means the two can silently diverge, which would let the
baseline fixtures be scored by different code than `doc-bench` uses at runtime.

A byte-equality **drift guard** prevents this. See [guards.md](./guards.md) for
exactly what it checks, the pinned allow-list, and remediation when it fires.
