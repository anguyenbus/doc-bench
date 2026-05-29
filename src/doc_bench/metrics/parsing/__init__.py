"""Parsing metrics for document quality evaluation."""

from doc_bench.metrics.parsing.layout_map import (
    layout_map_score,
    normalized,
    scaled,
    to_top_left_origin,
)
from doc_bench.metrics.parsing.reading_order import (
    ard_score,
    ard_weighted_score,
)
from doc_bench.metrics.parsing.text_fidelity import text_f1_score
from doc_bench.metrics.parsing.text_similarity import (
    bleu_score,
    char_edit_distance,
    meteor_score,
    word_edit_distance,
)

__all__ = [
    # Layout detection metrics (mAP)
    "layout_map_score",
    "normalized",
    "scaled",
    "to_top_left_origin",
    # Reading order metrics
    "ard_score",
    "ard_weighted_score",
    # Text similarity metrics
    "bleu_score",
    "char_edit_distance",
    "meteor_score",
    "word_edit_distance",
    # Legacy metric
    "text_f1_score",
]
