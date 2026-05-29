"""
Prediction loading module for file-based evaluation.

This module provides functions for loading prediction files from disk
for use in file-based evaluation mode.
"""

import json
from pathlib import Path


def load_prediction(predictions_dir: Path, doc_id: str) -> dict | None:
    """
    Load a prediction JSON file for a given document.

    This function reads prediction files from disk for file-based evaluation.
    It handles three possible return states:
      - Returns parsed dict on successful load
      - Returns None if file does not exist (caller should record MISSING_PREDICTION)
      - Returns None if file contains invalid JSON (caller should record INVALID_JSON)

    Args:
        predictions_dir: Directory containing prediction JSON files.
        doc_id: Document identifier (used to construct filename as <doc_id>.json).

    Returns:
        Parsed prediction dictionary on success, None on any error.

    Examples:
        >>> pred = load_prediction(Path("/predictions"), "doc001")
        >>> if pred is None:
        ...     # Handle missing or invalid prediction
        ...     pass

    Notes:
        - This function does NOT perform schema validation—that happens later
          in the pipeline to distinguish between missing files and invalid schemas.
        - Caller is responsible for recording rejections with appropriate reason codes.
        - Errors are silently handled to allow evaluation to continue with other documents.

    """
    # Construct prediction file path
    prediction_path = predictions_dir / f"{doc_id}.json"

    # Try to load the file
    try:
        with open(prediction_path) as f:
            return json.load(f)
    except FileNotFoundError:
        # File does not exist - caller records MISSING_PREDICTION
        return None
    except (json.JSONDecodeError, OSError):
        # Invalid JSON or other OS error - caller records INVALID_JSON
        return None
