"""Parsing metrics for document quality evaluation."""

# Text similarity and reading order metrics (no torch required)
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

# Layout detection metrics (torch required - optional)
try:
    from doc_bench.metrics.parsing.layout_map import (
        layout_map_score,
        normalized,
        scaled,
        to_top_left_origin,
    )

    _LAYOUT_AVAILABLE = True
except ImportError:
    _LAYOUT_AVAILABLE = False

__all__ = [
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

# Add layout metrics if available
if _LAYOUT_AVAILABLE:
    __all__.extend(
        [
            "layout_map_score",
            "normalized",
            "scaled",
            "to_top_left_origin",
        ]
    )
