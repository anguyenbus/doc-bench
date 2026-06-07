# OmniDocBench Fixtures

## Version

Selected from the English-filtered OmniDocBench dataset (opendatalab/OmniDocBench),
sourced from the local evaluation snapshot at
`evaluation/data/parsing/omnidocbench_english/` (downloaded 2026-05-17).

Previous fixture set (16 pages, v1.5 — annotation errors present) was replaced on
2026-06-06. **Scores computed on this 12-page fixture set are not directly comparable
to scores computed on the old 16-page set.**

## Page Count and Distribution

Total: **11 pages**

| Doc type             | Count | Notes                                    |
|----------------------|-------|------------------------------------------|
| academic_literature  | 3     | Diverse layouts (single, double, other)  |
| exam_paper           | 1     | Single column                            |
| colorful_textbook    | 2     | Single and other layout                  |
| book                 | 2     | Single column                            |
| PPT2PDF              | 2     | Single column                            |
| research_report      | 1     | Only 1 English page available in dataset |

All pages are clean (no fuzzy_scan, no watermark).

## Selection Criteria

Pages were selected using layout-diverse round-robin sampling per doc type:

1. Grouped available pages by `(doc_type, layout)`.
2. Excluded the previous 16 fixture pages (known annotation errors).
3. Round-robin across layout groups until target count reached.
4. All images verified present before committing.

## Baseline Results

`../omnidocbench_results.json` must be regenerated against this fixture set:

```bash
uv run docling-baseline --dataset omnidocbench --data-dir src/doc_bench/fixtures/omnidocbench
```
