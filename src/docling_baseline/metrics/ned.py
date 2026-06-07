"""
Normalized Edit Distance (NED) metric for document text evaluation.

OmniDocBench-compatible NED: character-level Levenshtein distance normalized
by the longer string's length, reported as similarity (1 - NED).

Formula:
    NED(gt, pred) = Levenshtein.distance(gt, pred) / max(len(gt), len(pred))
    ned_score     = 1 - NED

Normalization applied before comparison (matches OmniDocBench behavior):
  1. NFC unicode normalization
  2. Whitespace collapse: runs of whitespace -> single space, stripped
"""

import re
import unicodedata
from typing import Final

import Levenshtein

_WHITESPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\s+")


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    return _WHITESPACE_PATTERN.sub(" ", normalized).strip()


def ned_score(gt: str, pred: str) -> float:
    """
    Compute OmniDocBench-compatible NED similarity.

    Args:
        gt: Ground-truth text string.
        pred: Predicted text string.

    Returns:
        Similarity in [0.0, 1.0]. 1.0 is perfect; 0.0 is completely dissimilar.

    """
    gt_norm = _normalize(gt)
    pred_norm = _normalize(pred)

    if not gt_norm and not pred_norm:
        return 1.0

    if not gt_norm or not pred_norm:
        return 0.0

    max_len = max(len(gt_norm), len(pred_norm))
    ned = Levenshtein.distance(gt_norm, pred_norm) / max_len
    return 1.0 - ned
