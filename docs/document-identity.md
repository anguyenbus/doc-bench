# Document Identity Convention

This document defines the canonical convention for deriving document identifiers across all datasets in doc-bench.

## Overview

All document identifiers (`doc_id`) MUST be derived using the `doc_id_for()` helper function from `src/doc_bench/identity.py`. This is the ONLY way identifiers should be derived in the codebase. No inline string manipulation or direct field access for identifiers is permitted.

## Per-Dataset Rules

### DP-Bench

For DP-Bench, the `doc_id` is the PDF filename without extension from `reference.json` keys.

**Example:**
- PDF filename: `01030000000001.pdf`
- doc_id: `01030000000001`

The loader yields `(doc_id, pdf_path, gold_elements)` tuples where `doc_id` is derived by removing the `.pdf` extension from the reference JSON key.

### OmniDocBench

For OmniDocBench, the `doc_id` is the image filename without extension from `page_info.image_path`.

**Example:**
- image_path: `page-d1561665-5359-42fe-920c-d6e3bff81953.png`
- doc_id: `page-d1561665-5359-42fe-920c-d6e3bff81953`

#### Investigation Findings

The OmniDocBench English subset uses UUID-based filenames which are filesystem-safe. The original OmniDocBench may contain Chinese characters (e.g., `搬书匠#375`) in filenames, which would require sanitization. If needed, a bidirectional mapping will be implemented in `doc_id_for()`.

## File Naming Convention

Prediction files MUST be named `<doc_id>.json` where `<doc_id>` is exactly the stem of the corresponding `<doc_id>.<ext>` file produced by `dump-dataset`.

**Examples:**
- DP-Bench: `01030000000001.pdf` → `01030000000001.json`
- OmniDocBench: `page-d1561665-5359-42fe-920c-d6e3bff81953.png` → `page-d1561665-5359-42fe-920c-d6e3bff81953.json`

## Usage in Code

```python
from doc_bench.identity import doc_id_for

# For DP-Bench
pdf_filename = "01030000000001.pdf"
gold_elements = {"elements": [...]}
doc_id = doc_id_for("dp_bench", (pdf_filename, gold_elements))

# For OmniDocBench
page = {"page_info": {"image_path": "page-abc123.png"}, ...}
doc_id = doc_id_for("omnidocbench", page)
```

## Implementation Details

The `doc_id_for()` function:
- Dispatches based on dataset name
- Validates input structure
- Returns filesystem-safe identifier stems
- Raises `ValueError` for unknown datasets or invalid input

For filesystem-hostile characters, the function will implement sanitization with bidirectional mapping stored in `manifest.json` if needed.
