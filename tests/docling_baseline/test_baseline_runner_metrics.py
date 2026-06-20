"""Metric-key naming contract for the docling_baseline generator.

The project standardises on ``ned_similarity`` (the 1 - NED *similarity* form,
higher = better) for the text metric, matching the ``doc_bench`` consumer CLI
(:mod:`doc_bench.runners.run_parsing_eval`), the bundled ``*_results.json``
fixtures, and the existing result-metadata tests. The generator must emit the
same key — never a bare ``ned`` — so a single results schema holds across both
the producer and the consumer.
"""

from pathlib import Path

from docling_baseline.runners.base import BaseRunner


class _DummyRunner(BaseRunner):
    """Minimal concrete runner exercising the shared metric helpers."""

    def get_dataset_name(self) -> str:
        """Return the dataset name."""
        return "dummy"

    def evaluate(self) -> dict:
        """Unused in these tests."""
        return {}


def _runner() -> _DummyRunner:
    return _DummyRunner(fixtures_dir=Path("."), manifest={})


def test_calculate_metrics_uses_ned_similarity() -> None:
    """calculate_metrics returns ``ned_similarity``, never a bare ``ned``."""
    metrics = _runner().calculate_metrics("hello world", "hello world")
    assert "ned_similarity" in metrics
    assert "ned" not in metrics
    assert metrics["ned_similarity"] == 1.0


def test_calculate_metrics_empty_input_uses_ned_similarity() -> None:
    """The empty/short-circuit branch also uses ``ned_similarity``."""
    metrics = _runner().calculate_metrics("", "anything")
    assert "ned_similarity" in metrics
    assert "ned" not in metrics


def test_compute_averages_uses_ned_similarity() -> None:
    """compute_averages aggregates the ``ned_similarity`` key."""
    averages = _runner().compute_averages(
        [
            {"ned_similarity": 1.0, "teds": 0.5, "teds_s": 0.5},
            {"ned_similarity": 0.0, "teds": 0.5, "teds_s": 0.5},
        ]
    )
    assert "ned_similarity" in averages
    assert "ned" not in averages
    assert averages["ned_similarity"] == 0.5
