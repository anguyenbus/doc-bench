"""
Evaluation metrics for document parsing.

This module provides standardized metrics for evaluating document parsers:
- NED: Normalized Edit Distance (OmniDocBench-compatible, character-level)
- TEDS: Tree Edit Distance Similarity (table structure)
"""

from docling_baseline.metrics.ned import ned_score
from docling_baseline.metrics.table_teds import teds_score, teds_s_score

__all__ = [
    "ned_score",
    "teds_score",
    "teds_s_score",
]
