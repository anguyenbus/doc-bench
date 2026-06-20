# Datasets

## Table of Contents

- [Overview](#overview)
- [Bundled Fixture Composition](#bundled-fixture-composition)
- [DP-Bench](#dp-bench)
- [OmniDocBench](#omnidocbench)
- [ATO-Bench](#ato-bench)
- [Bundled Baseline Scores](#bundled-baseline-scores)
- [Manifest Structure](#manifest-structure)
- [Related Documentation](#related-documentation)

## Overview

`doc-bench` ships with three datasets as bundled fixtures inside the wheel,
under `src/doc_bench/fixtures/`. All three — DP-Bench, OmniDocBench, and
ATO-Bench — are gradable through the main `doc-bench` evaluation CLI
(`--dataset dp_bench | omnidocbench | ato_bench`). For `ato_bench`, the ground
truth defaults to the bundled fixtures, so no `--data-dir` is required (see the
[ATO-Bench](#ato-bench) section below).

The total bundled corpus is **33 documents**. The smoke test
(`doc-bench-smoke-test`) processes all 33 with zero rejections, which is what
verifies the fixtures are intact after install.

## Bundled Fixture Composition

| Dataset      | Bundled docs | Breakdown                                                                                      |
| ------------ | ------------ | ---------------------------------------------------------------------------------------------- |
| DP-Bench     | 16           | Paragraph (10), Caption (2), Chart (1), Heading1 (2), Index (1)                                |
| OmniDocBench | 16           | academic_literature (8), book (2), colorful_textbook (2), exam_paper (2), PPT2PDF (2)          |
| ATO-Bench    | 1            | individual_income_tax_return (1)                                                               |
| **Total**    | **33**       |                                                                                                |

## DP-Bench

**What it is.** A digital-PDF document-parsing benchmark. The bundled subset
contains 16 documents spanning the categories listed above.

**Bundled subset.** 16 documents: Paragraph (10), Caption (2), Chart (1),
Heading1 (2), Index (1). Four of these are **deliberately problematic** PDFs,
included so parser robustness can be exercised:

| doc_id           | Category  |
| ---------------- | --------- |
| `01030000000172` | Index     |
| `01030000000018` | Heading1  |
| `01030000000141` | Paragraph |
| `01030000000121` | Paragraph |

**Full dataset.** The complete DP-Bench dataset is approximately 1,052
documents; contact the original authors for access to the full set.

**Limitation.** DP-Bench gold annotations are **single-page only** — each
`doc_id` corresponds to exactly one page of content. Metrics therefore reflect
page-level extraction quality, not multi-page document parsing.

## OmniDocBench

**What it is.** A document-parsing benchmark derived from multi-page sources but
annotated at the page level. The bundled subset contains 16 documents across the
document types listed below.

**Bundled subset.** 16 documents: academic_literature (8), book (2),
colorful_textbook (2), exam_paper (2), PPT2PDF (2).

**Full dataset.** The English-only sample is approximately 593 pages.

**Limitation.** OmniDocBench annotations are **sparse**: the `layout_dets`
cover key page elements rather than all page content, and text is evaluated only
on the annotated regions. Scores reflect annotated-region extraction, not
exhaustive page coverage.

## ATO-Bench

**What it is.** Australian Tax Office forms — multi-page PDFs with per-page
ground truth in OmniDocBench format (`layout_dets`). The bundled subset is a
single document, `doc_id` `1371-6.1997`
(`doc_type` `individual_income_tax_return`): a 2-page PDF accompanied by two
per-page ground-truth JSON files.

**Limitation — gold-builder caveat.** The gold-text builder ignores table
`.cells`, so on this format the table-oriented metrics `TEDS`, `MHS`, and `ARD`
are typically `0.0`. This is a known limitation of the gold builder, documented
under [../docling-baseline/adding-a-dataset.md](../docling-baseline/adding-a-dataset.md).

**Gradable via the main CLI.** ATO-Bench is gradable with
`doc-bench --dataset ato_bench --predictions <dir>`. Its ground truth is loaded
from the bundled fixture layout (`manifest.json` + `ato_bench/`), and a
document's per-page gold is combined into one document-level gold string before
scoring — mirroring how the generator's ATO-Bench runner scores it. Because the
gold is concatenated text, the table-oriented metrics behave as noted in the
caveat above.

## Bundled Baseline Scores

Reference baseline scores are bundled alongside the fixtures in
`src/doc_bench/fixtures/`:

- `dpbench_results.json`
- `omnidocbench_results.json`
- `ato_bench_results.json`

The ATO-Bench baseline (2-page document) is:

| Metric | Value  |
| ------ | ------ |
| NID    | 0.2168 |
| BLEU   | 0.0603 |
| METEOR | 0.4207 |
| TEDS   | 0.0    |
| MHS    | 0.0    |
| ARD    | 0.0    |

The `TEDS`/`MHS`/`ARD` zeros are expected given the gold-builder caveat above.

Load the bundled baselines programmatically via `importlib.resources`:

```python
import json
from importlib.resources import files

baseline_path = files("doc_bench") / "fixtures" / "dpbench_results.json"
baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

# The same pattern applies to omnidocbench_results.json and ato_bench_results.json.
```

## Manifest Structure

The fixture inventory lives in `src/doc_bench/fixtures/manifest.json`. Its
top-level keys are:

- `name` — manifest name.
- `description` — human-readable description.
- `dp_bench` — list of DP-Bench entries.
- `omnidocbench` — list of OmniDocBench entries.
- `ato_bench` — list of ATO-Bench entries.
- `total` — total document count, `33`.

Each dataset list holds entries shaped per dataset. One example entry per
dataset:

**DP-Bench** entry (`doc_id`, `category`, `pdf`, `gold`):

```json
{
  "doc_id": "01030000000001",
  "category": "Paragraph",
  "pdf": "dp_bench/01030000000001.pdf",
  "gold": "dp_bench/01030000000001.json"
}
```

**OmniDocBench** entry (`doc_id`, `doc_type`, `page`, `image`):

```json
{
  "doc_id": "page-48687e49-b9db-4251-96cf-124144aa4d08",
  "doc_type": "PPT2PDF",
  "page": "omnidocbench/page-48687e49-b9db-4251-96cf-124144aa4d08.json",
  "image": "omnidocbench/page-48687e49-b9db-4251-96cf-124144aa4d08.png"
}
```

**ATO-Bench** entry (`doc_id`, `doc_type`, `pdf`, `pages[]`):

```json
{
  "doc_id": "1371-6.1997",
  "doc_type": "individual_income_tax_return",
  "pdf": "ato_bench/1371-6.1997.pdf",
  "pages": [
    "ato_bench/1371-6.1997_p1.json",
    "ato_bench/1371-6.1997_p2.json"
  ]
}
```

## Related Documentation

- [overview.md](overview.md) — what doc-bench is and the grading workflow.
- [cli-reference.md](cli-reference.md) — full flag reference for every entry point.
- [metrics.md](metrics.md) — definitions of the six deterministic metrics.
- [parser-output.md](parser-output.md) — the `ParserOutput` prediction schema.
- [../document-identity.md](../document-identity.md) — how `doc_id`s are derived.
- [../docling-baseline/overview.md](../docling-baseline/overview.md) — the baseline generator.
- [../docling-baseline/adding-a-dataset.md](../docling-baseline/adding-a-dataset.md) — ATO gold-builder details.
