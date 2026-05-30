# DP-Bench Baseline for Docling Evaluation

## Structure
- **pdfs/**: 12 representative PDFs (2 examples per element type)
- **reference.json**: Ground truth annotations for the 12 PDFs

## Element Type Coverage
| Element Type | PDF Examples | Total Elements |
|--------------|--------------|----------------|
| Table | 01030000000083.pdf, 01030000000127.pdf | 7 |
| Paragraph | 01030000000192.pdf, 01030000000193.pdf | 81 |
| Figure | 01030000000118.pdf, 01030000000120.pdf | 9 |
| Chart | 01030000000027.pdf, 01030000000076.pdf | 7 |
| Header | 01030000000001.pdf, 01030000000002.pdf | 10 |
| Footer | 01030000000017.pdf, 01030000000040.pdf | 11 |

## Instructions for Docling Evaluation

Run in your environment with docling installed:

```bash
cd baseline/dp_bench
# Run docling on each PDF in pdfs/ directory
# Output results to dpbench_docling_baseline.json
```

Expected output format:
```json
{
  "total": 12,
  "successful": 12,
  "averages": {
    "nid": 0.XX,
    "teds": 0.XX,
    "teds_s": 0.XX
  },
  "results": [
    {
      "pdf": "01030000000001.pdf",
      "nid": 0.XX,
      "teds": 0.XX,
      ...
    }
  ]
}
```
