"""
Evaluation metrics for document parsing.

This module provides standardized metrics for evaluating document parsers:
- NID: Normalized Indel Distance (reading order)
- BLEU: BLEU score (text similarity)
- METEOR: METEOR score (text similarity)
- TEDS: Tree Edit Distance Similarity (table structure)
- MHS: Markdown Hierarchical Similarity (heading structure)
- ARD: Average Rank Distance (reading order)
"""

from docling_baseline.metrics.nid import nid_score, nid_s_score
from docling_baseline.metrics.text_similarity import bleu_score, meteor_score
from docling_baseline.metrics.table_teds import teds_score, teds_s_score
from docling_baseline.metrics.mhs import mhs_score, mhs_s_score
from docling_baseline.metrics.reading_order import ard_score

__all__ = [
    "nid_score",
    "nid_s_score",
    "bleu_score",
    "meteor_score",
    "teds_score",
    "teds_s_score",
    "mhs_score",
    "mhs_s_score",
    "ard_score",
]
