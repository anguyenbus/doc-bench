r"""
Normalized Edit Distance (NED) metric for document text evaluation.

This module implements the OmniDocBench-compatible NED metric for scoring
parsed document text against ground truth. The formula and normalization
choices are chosen to produce scores directly comparable to the
OmniDocBench leaderboard.

Normalization choices
---------------------
Two preprocessing steps are applied to both strings before comparison:

1. **NFC unicode normalization** (``unicodedata.normalize("NFC", text)``):
   Combining character sequences (e.g., "e" + U+0301 combining acute) are
   collapsed to their precomposed equivalents (e.g., U+00E9 "e with acute"),
   matching the unicode normalization behavior of the OmniDocBench evaluation
   pipeline.

2. **Whitespace collapse** (``re.sub(r"\s+", " ", text).strip()``):
   Any run of whitespace -- spaces, tabs, newlines -- is replaced by a single
   ASCII space, and leading/trailing whitespace is stripped.  This prevents
   segmentation differences (e.g., paragraph-break vs. single space) from
   inflating the edit distance, matching the whitespace normalization applied
   by OmniDocBench's ``normalized_text`` helper.

Formula
-------
The NED distance is:

    NED(gt, pred) = Levenshtein.distance(gt, pred) / max(len(gt), len(pred))

Reported as similarity (1 - NED), in [0.0, 1.0]:

    ned_score(gt, pred) = 1 - NED(gt, pred)

The ``Levenshtein`` package (PyPI: ``python-Levenshtein``) is used, NOT
``rapidfuzz``, matching the OmniDocBench canonical source exactly (see
``references/omnidocbench/cal_metric.py`` and ``match.py``).

Empty string handling
---------------------
- Both empty -> similarity 1.0 (perfect match: no content to disagree on).
- One empty -> similarity 0.0 (all content is missing or spurious).

References
----------
- OmniDocBench (CVPR 2025): https://arxiv.org/abs/2412.07626
- Reference implementation: ``references/omnidocbench/cal_metric.py``

"""

import re
import unicodedata
from typing import Final

import Levenshtein

# NOTE: The pattern used for whitespace collapse matches OmniDocBench behavior.
_WHITESPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """
    Apply NFC normalization and whitespace collapse to a string.

    Args:
        text: Raw input string.

    Returns:
        Normalized string with NFC unicode form and collapsed whitespace.

    """
    normalized = unicodedata.normalize("NFC", text)
    return _WHITESPACE_PATTERN.sub(" ", normalized).strip()


def ned_score(gt: str, pred: str) -> float:
    """
    Compute OmniDocBench-compatible NED similarity between gt and pred.

    Applies NFC normalization and whitespace collapse before computing:

        NED = Levenshtein.distance(gt, pred) / max(len(gt), len(pred))

    Returns the similarity form: ``1 - NED``.

    Args:
        gt: Ground-truth text string.
        pred: Predicted text string.

    Returns:
        Similarity score in [0.0, 1.0].  1.0 is a perfect match; 0.0 means
        the strings are completely dissimilar or one is empty and the other
        is not.

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
