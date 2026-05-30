"""
Document identity convention for doc-bench.

This module provides the canonical way to derive document identifiers
across all datasets. The doc_id_for() helper is the ONLY way identifiers
should be derived in the codebase.

Per-dataset conventions:
  - DP-Bench: doc_id is the PDF filename without extension (e.g., "01030000000001")
  - OmniDocBench: doc_id is the image filename without extension (e.g., "page-d1561665-5359-42fe-920c-d6e3bff81953")

Prediction files MUST be named <doc_id>.json where <doc_id> is exactly
the stem of the corresponding <doc_id>.<ext> file produced by dump-dataset.
"""

import re
from pathlib import Path

# Sanitization pattern for filesystem-hostile characters
# Matches characters that are problematic on most filesystems
_FS_UNSAFE_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def doc_id_for(dataset_name: str, item: tuple | dict) -> str:
    """
    Derive the canonical document identifier for a dataset item.

    This is the ONLY way identifiers should be derived across the codebase.
    No inline string manipulation or direct field access for identifiers.

    Args:
        dataset_name: Name of the dataset ('dp_bench' or 'omnidocbench').
        item: Dataset item. For DP-Bench: (pdf_filename, gold_elements) tuple.
              For OmniDocBench: page dict.

    Returns:
        Filesystem-safe document identifier (filename stem without extension).

    Raises:
        ValueError: If dataset_name is unknown or item structure is invalid.

    Examples:
        >>> doc_id_for('dp_bench', ('01030000000001.pdf', {'elements': []}))
        '01030000000001'
        >>> page = {'page_info': {'image_path': 'page-abc123.png'}}
        >>> doc_id_for('omnidocbench', page)
        'page-abc123'

    """
    if dataset_name == "dp_bench":
        return _doc_id_for_dp_bench(item)
    elif dataset_name == "omnidocbench":
        return _doc_id_for_omnidocbench(item)
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")


def _doc_id_for_dp_bench(item: tuple) -> str:
    """
    Derive doc_id for DP-Bench item.

    Args:
        item: (pdf_filename, gold_elements) tuple from reference.json.

    Returns:
        PDF filename without extension (e.g., "01030000000001").

    """
    if not isinstance(item, tuple) or len(item) < 2:
        raise ValueError(
            f"DP-Bench item must be (pdf_filename, gold_elements) tuple, got: {type(item)}"
        )

    pdf_filename = item[0]
    if not isinstance(pdf_filename, str):
        raise ValueError(f"PDF filename must be string, got: {type(pdf_filename)}")

    # Remove .pdf extension to get doc_id
    doc_id = pdf_filename.replace(".pdf", "")

    # Sanity check: should not contain filesystem-hostile characters
    if _FS_UNSAFE_PATTERN.search(doc_id):
        raise ValueError(f"DP-Bench doc_id contains unsafe characters: {doc_id}")

    return doc_id


def _doc_id_for_omnidocbench(item: dict) -> str:
    """
    Derive doc_id for OmniDocBench page.

    Investigation findings:
      - OmniDocBench pages use page_info.image_path for file lookup
      - In the English subset, image_path uses UUID-based filenames
        (e.g., "page-d1561665-5359-42fe-920c-d6e3bff81953.png")
      - These UUID-based filenames are filesystem-safe
      - If original OmniDocBench uses Chinese characters or other
        filesystem-hostile names, sanitization would be needed here

    Args:
        item: OmniDocBench page dict with page_info structure.

    Returns:
        Image filename without extension (e.g., "page-d1561665-5359-42fe-920c-d6e3bff81953").

    """
    if not isinstance(item, dict):
        raise ValueError(f"OmniDocBench item must be dict, got: {type(item)}")

    page_info = item.get("page_info", {})
    if not isinstance(page_info, dict):
        raise ValueError("OmniDocBench page.page_info must be dict")

    image_path = page_info.get("image_path", "")
    if not isinstance(image_path, str) or not image_path:
        raise ValueError("OmniDocBench page_info.image_path must be non-empty string")

    # Remove extension to get doc_id
    # Support both .png and other image formats
    doc_id = Path(image_path).stem

    # If native identifier contains filesystem-hostile characters,
    # we would need sanitization here with bidirectional mapping.
    # Current OmniDocBench English subset uses UUID-based names which are safe.
    # Original OmniDocBench may have Chinese characters like '搬书匠#375'
    # which would require sanitization - to be implemented if needed.

    return doc_id
