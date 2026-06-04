# Adding a Benchmark Document or Dataset

This is a step-by-step guide for adding a new benchmark document to the
generator and producing its baseline fixture. It uses the real ATO
`1371-6.1997` document as the worked example. For the runner contracts these
steps satisfy, see [architecture.md](./architecture.md); for the generator
big picture, see [overview.md](./overview.md).

## Table of contents

- [Case study: ATO 1371-6.1997](#case-study-ato-1371-61997)
- [Prerequisites](#prerequisites)
- [Steps](#steps)
- [Verify](#verify)
- [Gotchas](#gotchas)

## Case study: ATO 1371-6.1997

`1371-6.1997` is a 2-page individual income tax return. It was added to the ATO
benchmark, scored by the generator, and bundled as
[`src/doc_bench/fixtures/ato_bench_results.json`](../../src/doc_bench/fixtures/ato_bench_results.json).
The steps below are exactly the process used.

## Prerequisites

- Python 3.13 and the dev-only `generator` dependency group (see
  [regenerating-fixtures.md](./regenerating-fixtures.md) for why these are
  isolated). Runs use `uv run --python 3.13 --group generator ...`.
- A source PDF (or image) and its ground truth in OmniDocBench `layout_dets`
  format.

## Steps

1. **Organize the files into the manifest layout.** Place the PDF at
   `<fixtures_dir>/ato_bench/<pdf>`. For the case study the fixtures directory is
   [`src/doc_bench/fixtures/`](../../src/doc_bench/fixtures/) and the PDF lives
   under [`src/doc_bench/fixtures/ato_bench/`](../../src/doc_bench/fixtures/ato_bench/).

2. **Align the PDF page count to the ground truth.** The `1371-6.1997` ground
   truth covered only the first 2 pages, but the source PDF had 6 pages. The PDF
   was **trimmed to its first 2 pages** so the page counts match. Page-count
   alignment matters: trimming to match the gold roughly **doubled** the text
   metrics in this case, because Docling no longer emitted text for pages that
   had no corresponding gold.

3. **Split the ground truth into per-page files.** The ATO-bench runner expects
   one ground-truth file per page. The single ground-truth JSON list was split
   into per-page files
   `<fixtures_dir>/ato_bench/<doc_id>_p1.json` and `_p2.json`, i.e.
   `1371-6.1997_p1.json` and `1371-6.1997_p2.json`. Each file is a single page
   dict in OmniDocBench `layout_dets` format with keys `layout_dets`, `extra`,
   and `page_info`.

4. **Add a manifest entry.** Add an entry to the ATO section of `manifest.json`
   in the fixtures directory:
   ```json
   { "doc_id": "1371-6.1997", "pdf": "<pdf>", "doc_type": "...", "pages": [ ... ] }
   ```

5. **Run the generator on Python 3.13.** Invoke the ATO-bench command as a
   module under the generator group:
   ```bash
   uv run --python 3.13 --group generator \
     python -m docling_baseline.cli ato-bench <fixtures_dir> --output <file>
   ```
   The runner runs Docling on the whole PDF, combines the per-page gold text,
   and scores at the document level.

6. **Bundle the results.** Place the produced results as
   [`src/doc_bench/fixtures/ato_bench_results.json`](../../src/doc_bench/fixtures/ato_bench_results.json)
   so `doc-bench` ships it.

## Verify

Run the smoke test to confirm the new bundled fixture is consumable:

```bash
uv run doc-bench-smoke-test
```

Because the metric code is duplicated between the generator and `doc-bench`,
also keep the drift guard green (`make test`); see [guards.md](./guards.md).

## Gotchas

### Gold-text builder ignores table cells

The shared gold-text builder `extract_gold_text_from_omnidocbench` in
[`src/docling_baseline/runners/omnidocbench.py`](../../src/docling_baseline/runners/omnidocbench.py)
only reads each detection's `.text` field and **ignores the `.cells` array of
table detections**. Consequences:

- Table-heavy documents contribute **no table text** to the gold string.
- For OmniDocBench-format gold, no markdown tables or headings are emitted into
  the gold, so **TEDS, MHS, and ARD score `0`** for such docs.

This is a **gold-builder limitation, not a Docling failure**: Docling may parse
the tables correctly, but the gold side has nothing to compare against. Keep
this in mind when interpreting low table/heading/reading-order scores for a new
table-heavy document.
