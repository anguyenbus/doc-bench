"""
Tests for module deletion validation.

Verifies that deleted RAG/observability modules are no longer importable
and that kept parsing modules still work correctly.
"""

import pytest


def test_deleted_rag_adapters_not_importable() -> None:
    """Test that deleted RAG adapter modules cannot be imported."""
    with pytest.raises(ImportError, match="cannot import name 'rag_adapter'"):
        from doc_bench.adapters import rag_adapter  # noqa: F401


def test_deleted_phoenix_adapter_not_importable() -> None:
    """Test that deleted Phoenix adapter module cannot be imported."""
    with pytest.raises(ImportError, match="cannot import name 'phoenix_eval_adapter'"):
        from doc_bench.adapters import phoenix_eval_adapter  # noqa: F401


def test_deleted_deepeval_adapter_not_importable() -> None:
    """Test that deleted DeepEval adapter module cannot be imported."""
    with pytest.raises(ImportError, match="cannot import name 'deepeval_adapter'"):
        from doc_bench.adapters import deepeval_adapter  # noqa: F401


def test_deleted_embeddings_adapter_not_importable() -> None:
    """Test that deleted embeddings module cannot be imported."""
    with pytest.raises(ImportError, match="cannot import name 'embeddings'"):
        from doc_bench.adapters import embeddings  # noqa: F401


def test_deleted_experiments_module_not_importable() -> None:
    """Test that deleted experiments module cannot be imported."""
    with pytest.raises(ImportError, match="No module named.*experiments"):
        from doc_bench.experiments import runner  # noqa: F401


def test_deleted_cli_module_not_importable() -> None:
    """Test that deleted CLI module cannot be imported."""
    with pytest.raises(ImportError, match="No module named.*cli"):
        from doc_bench.cli import check  # noqa: F401


def test_kept_parser_adapter_importable() -> None:
    """Test that parser adapter is still importable."""
    from doc_bench.adapters import parser_adapter

    assert parser_adapter is not None
    assert hasattr(parser_adapter, "ParserAdapter")


def test_kept_schema_validator_importable() -> None:
    """Test that schema validator is still importable."""
    from doc_bench.adapters import schema_validator

    assert schema_validator is not None
    assert hasattr(schema_validator, "validate")


def test_kept_parsing_metrics_importable() -> None:
    """Test that parsing metrics are still importable."""
    from doc_bench.metrics.parsing import (
        nid,
        table_teds,
        text_similarity,
        reading_order,
        mhs,
    )

    assert nid is not None
    assert table_teds is not None
    assert text_similarity is not None
    assert reading_order is not None
    assert mhs is not None


def test_kept_datasets_importable() -> None:
    """Test that dataset loaders are still importable."""
    from doc_bench.datasets import load_dp_bench, load_omnidocbench

    assert load_dp_bench is not None
    assert load_omnidocbench is not None
