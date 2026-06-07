"""
Tests for package rename validation.

Verifies that the package has been renamed from eval_harness to doc_bench.
"""

import pytest


def test_doc_bench_importable() -> None:
    """Test that doc_bench package is importable."""
    import doc_bench

    assert doc_bench is not None
    assert hasattr(doc_bench, "__version__")


def test_eval_harness_not_importable() -> None:
    """Test that old eval_harness package name is not available."""
    with pytest.raises(ImportError, match="No module named.*eval_harness"):
        import eval_harness  # noqa: F401


def test_doc_bench_datasets_importable() -> None:
    """Test that datasets are importable under new name."""
    from doc_bench.datasets import load_dp_bench, load_omnidocbench

    assert load_dp_bench is not None
    assert load_omnidocbench is not None


def test_doc_bench_metrics_importable() -> None:
    """Test that current metrics are importable under new name.

    NOTE: After the 2026-06-07 NED/metrics simplification spec, only ned_score
    (NED) and table_teds (TEDS) remain.  nid, text_similarity, and other old
    metrics were deleted.
    """
    from doc_bench.metrics.parsing import ned_score, table_teds

    assert ned_score is not None
    assert table_teds is not None


def test_doc_bench_adapters_importable() -> None:
    """Test that adapters are importable under new name."""
    from doc_bench.adapters import parser_adapter, schema_validator

    assert parser_adapter is not None
    assert schema_validator is not None
