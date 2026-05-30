# File-Based Evaluation Mode

This guide explains how to use doc-bench's file-based evaluation mode, which allows you to grade pre-computed predictions without running parsers in-process.

## Overview

File-based evaluation mode decouples prediction execution from grading, enabling:

- **Rapid iteration**: Run predictions once, grade multiple times while debugging evaluation logic
- **Cost efficiency**: Avoid re-running expensive parsers when only evaluation parameters change
- **External parser support**: Evaluate any parser that outputs JSON, even if it cannot be integrated directly
- **Debugging**: Inspect individual prediction failures by examining saved JSON files

## Quick Start

### 1. Export Dataset Documents

First, export the dataset documents with canonical identifiers:

```bash
# Export DP-Bench documents (limit to 10 for testing)
uv run doc-bench dump-dataset --dataset dp_bench --output ./dataset_export --limit 10

# Export OmniDocBench documents
uv run doc-bench dump-dataset --dataset omnidocbench --output ./dataset_export --limit 10
```

This creates:
- `<doc_id>.pdf` or `<doc_id>.png` files for each document
- `manifest.json` with reproducibility metadata (hashes, versions, timestamps)

### 2. Generate Predictions

Run your external parser and save predictions as `<doc_id>.json` files:

```bash
# Example: Generate predictions in a directory
mkdir ./predictions
# Your parser would produce files like:
# predictions/01030000000001.json
# predictions/01030000000002.json
# ...
```

**Important**: Prediction filenames must exactly match the document IDs from `dump-dataset` (without extensions).

### 3. Evaluate Predictions

Grade the pre-computed predictions:

```bash
uv run eval-parsing --dataset dp_bench --predictions ./predictions
```

This produces:
- `results/dp_bench_predictions_results_<timestamp>.csv` - Per-document metrics
- `results/dp_bench_predictions_rejected_<timestamp>.csv` - Rejected predictions with reasons
- `results/dp_bench_predictions_results_<timestamp>.json` - Summary with evaluated/rejected counts

## Prediction File Format

Prediction files must conform to `contracts/parser_output.schema.json`. Example:

```json
{
  "schema_version": "1.0.0",
  "parser_version": "1.0.0",
  "source": {
    "doc_id": "01030000000001",
    "filename": "01030000000001.pdf",
    "mime_type": "application/pdf",
    "sha256": "a1b2c3..."
  },
  "pages": [
    {
      "page_index": 0,
      "width": 612,
      "height": 792
    }
  ],
  "elements": [
    {
      "element_id": "elem_0",
      "type": "paragraph",
      "page_index": 0,
      "char_span": [0, 50],
      "text": "Sample text content",
      "content": {"kind": "text"}
    }
  ]
}
```

## Document Identity Convention

doc-bench uses a canonical document identifier convention:

- **DP-Bench**: PDF filename without extension (e.g., `01030000000001`)
- **OmniDocBench**: Image filename without extension (e.g., `page-d1561665-5359-42fe-920c-d6e3bff81953`)

The `doc_id_for()` helper in `src/doc_bench/identity.py` is the **ONLY** way identifiers should be derived.

See `docs/document-identity.md` for full details.

## CLI Reference

### dump-dataset Command

```bash
uv run doc-bench dump-dataset --dataset <dataset> --output <dir> [--limit <n>]
```

**Arguments:**
- `--dataset`: Dataset to export (`dp_bench` or `omnidocbench`)
- `--output`: Output directory for exported documents
- `--limit`: Optional limit on number of documents to export

**Output:**
- Documents named `<doc_id>.<ext>` in the output directory
- `manifest.json` with reproducibility metadata

### evaluate Command (File-Based Mode)

```bash
uv run eval-parsing --dataset <dataset> --predictions <dir> [options]
```

**Arguments:**
- `--dataset`: Dataset to evaluate on (`dp_bench` or `omnidocbench`)
- `--predictions`: Directory containing `<doc_id>.json` prediction files
- `--max-rejection-rate`: Optional threshold (0.0-1.0, default: 0.5)
- `--config`: Path to `eval_config.yaml` (default: `eval_config.yaml`)
- `--output-dir`: Output directory (default: `results`)
- `--limit`: Optional limit on number of documents to process

**Note**: `--predictions` and `--parser` flags are mutually exclusive. Specify exactly one.

## Rejection Tracking

File-based evaluation tracks rejected predictions with detailed reasons:

### Rejection Reasons

| Reason Code | Description | Detail Content |
|-------------|-------------|----------------|
| `MISSING_PREDICTION` | Prediction file not found | Empty string |
| `INVALID_JSON` | File contains invalid JSON | JSON parse error message |
| `INVALID_SCHEMA` | Valid JSON fails schema validation | Field path and validation error |
| `EVALUATION_ERROR` | Error during metric computation | Exception message |

### rejected.csv Format

```csv
doc_id,reason,source_file,detail
01030000000001,MISSING_PREDICTION,01030000000001.json,
01030000000002,INVALID_SCHEMA,01030000000002.json,elements[0].bbox: Missing required property 'x0'
01030000000003,INVALID_JSON,01030000000003.json,JSON parse error: Expecting property name
```

### End-of-Run Summary

The evaluation prints a summary showing evaluated vs rejected counts:

```
Evaluated: 95 / Total documents
Rejected: 5 (2 missing, 1 bad schema, 2 bad json, 0 eval errors)
→ see results/dp_bench_predictions_rejected_20240129_120000.csv for the full list
```

### Threshold Warning

If rejection rate exceeds `--max-rejection-rate` (default: 0.5):

```
WARNING: Rejection rate (50.0%) exceeds threshold (50.0%). Results may be unreliable.
```

Set threshold to 0 to disable warnings.

## scores.json Output Format

File-based evaluation produces enhanced scores.json with rejection counts:

```json
{
  "dataset": "dp_bench",
  "parser": "predictions",
  "timestamp": "20240129_120000",
  "csv_file": "dp_bench_predictions_results_20240129_120000.csv",
  "metrics_avg": {
    "nid": 0.85,
    "nid_s": 0.80,
    "teds": 0.90,
    "teds_s": 0.88,
    "mhs": 0.75,
    "mhs_s": 0.70,
    "ard": 0.60,
    "bleu": 0.65,
    "meteor": 0.68
  },
  "evaluated_samples": 95,
  "rejected_samples": {
    "MISSING_PREDICTION": 2,
    "INVALID_JSON": 2,
    "INVALID_SCHEMA": 1,
    "EVALUATION_ERROR": 0
  }
}
```

**Note**: Parser mode (with `--parser`) uses legacy fields (`total_processed`, `errors`) for backward compatibility.

## Equivalence Verification

To verify that file-based evaluation produces identical results to parser mode, use the equivalence verification script:

```bash
# Run parser mode
uv run eval-parsing --dataset dp_bench --parser stub --output-dir results/parser
# Generates: results/parser/dp_bench_stub_results_*.json

# Run predictions mode (after dumping predictions from same parser)
uv run eval-parsing --dataset dp_bench --predictions ./predictions --output-dir results/predictions
# Generates: results/predictions/dp_bench_predictions_results_*.json

# Verify equivalence
python scripts/verify_equivalence.py \
  results/parser/dp_bench_stub_results_<timestamp>.json \
  results/predictions/dp_bench_predictions_results_<timestamp>.json
```

**Exit codes:**
- `0`: Metrics are equivalent
- `1`: Metrics differ
- `2`: Error (missing file, invalid JSON)

## Troubleshooting

### Common Issues

**Issue**: `MISSING_PREDICTION` rejections for all files

**Solution**: Verify prediction filenames match document IDs from `dump-dataset`. Check `manifest.json` for the expected doc_id values.

**Issue**: `INVALID_SCHEMA` rejections

**Solution**: Validate prediction files against the schema:

```bash
# Use jsonschema-cli to validate
jsonschema -i predictions/01030000000001.json contracts/parser_output.schema.json
```

**Issue**: Rejection rate warning

**Solution**: Check `rejected.csv` for details. Common causes:
- Mismatched document IDs
- Incomplete prediction generation
- Schema version mismatch

### Debug Tips

1. **Check manifest.json**: Verify document IDs and file hashes
2. **Inspect rejected.csv**: Look for patterns in rejection reasons
3. **Validate schema**: Use jsonschema CLI on individual prediction files
4. **Limit scope**: Use `--limit` to test with a small subset first

## Examples

### Example 1: Basic File-Based Evaluation

```bash
# Export 100 DP-Bench documents
uv run doc-bench dump-dataset --dataset dp_bench --output ./dataset --limit 100

# Generate predictions (assuming external parser)
# my_parser --input ./dataset --output ./predictions

# Evaluate predictions
uv run eval-parsing --dataset dp_bench --predictions ./predictions
```

### Example 2: OmniDocBench Evaluation

```bash
# Export OmniDocBench pages
uv run doc-bench dump-dataset --dataset omnidocbench --output ./omnidoc_export

# Generate predictions
# my_parser --input ./omnidoc_export --output ./predictions

# Evaluate with custom threshold
uv run eval-parsing --dataset omnidocbench --predictions ./predictions --max-rejection-rate 0.3
```

### Example 3: Equivalence Verification

```bash
# Run same evaluation via both modes
uv run eval-parsing --dataset dp_bench --parser stub --limit 10 --output-dir results/parser
uv run eval-parsing --dataset dp_bench --predictions ./predictions --limit 10 --output-dir results/predictions

# Compare results
python scripts/verify_equivalence.py \
  results/parser/dp_bench_stub_results_*.json \
  results/predictions/dp_bench_predictions_results_*.json
```

## Environment Variables

- `DOC_BENCH_MAX_REJECTION_RATE`: Default rejection threshold (if `--max-rejection-rate` not provided)

## Related Documentation

- `docs/document-identity.md` - Document identifier convention
- `contracts/parser_output.schema.json` - Prediction file schema
- `contracts/results_v1.schema.json` - Results JSON schema
