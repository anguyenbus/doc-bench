"""
Docling Baseline - Standalone evaluation tool for Docling document parser.

This package provides baseline evaluation scores for Docling across three datasets:
- DP-Bench: 16 PDF documents
- OmniDocBench: 16 document images
- ATO-Bench: 5 multi-page PDF forms (23 pages)
"""

__version__ = "0.1.0"

from docling_baseline.metrics import (
    nid_score,
    bleu_score,
    meteor_score,
    teds_score,
    mhs_score,
    ard_score,
)

__all__ = [
    "__version__",
    "nid_score",
    "bleu_score",
    "meteor_score",
    "teds_score",
    "mhs_score",
    "ard_score",
]
