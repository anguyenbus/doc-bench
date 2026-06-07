"""Parsing metrics for document quality evaluation."""

# NED (Normalized Edit Distance) — OmniDocBench-compatible text similarity
from doc_bench.metrics.parsing.ned import ned_score

__all__ = [
    # NED metric (replaces NID, MHS, BLEU, METEOR, ARD, text_f1, structure_recall, layout_map)
    "ned_score",
]
