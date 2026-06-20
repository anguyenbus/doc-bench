"""
Tests for module deletion validation.

Verifies that deleted RAG/observability modules and deleted parsing metrics
are no longer importable, and that kept parsing modules still work correctly.
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
    """Test that deleted CLI 'check' submodule cannot be imported."""
    with pytest.raises(ImportError):
        from doc_bench.cli import check  # noqa: F401


# ---------------------------------------------------------------------------
# Deleted parsing metric modules — must now raise ModuleNotFoundError.
# ---------------------------------------------------------------------------


def test_deleted_nid_module_not_importable() -> None:
    """nid.py was deleted; importing it must raise ModuleNotFoundError."""
    with pytest.raises(ModuleNotFoundError):
        import doc_bench.metrics.parsing.nid  # noqa: F401


def test_deleted_mhs_module_not_importable() -> None:
    """mhs.py was deleted; importing it must raise ModuleNotFoundError."""
    with pytest.raises(ModuleNotFoundError):
        import doc_bench.metrics.parsing.mhs  # noqa: F401


def test_deleted_text_similarity_module_not_importable() -> None:
    """text_similarity.py was deleted; importing it must raise ModuleNotFoundError."""
    with pytest.raises(ModuleNotFoundError):
        import doc_bench.metrics.parsing.text_similarity  # noqa: F401


def test_deleted_text_fidelity_module_not_importable() -> None:
    """text_fidelity.py was deleted; importing it must raise ModuleNotFoundError."""
    with pytest.raises(ModuleNotFoundError):
        import doc_bench.metrics.parsing.text_fidelity  # noqa: F401


def test_deleted_reading_order_module_not_importable() -> None:
    """reading_order.py was deleted; importing it must raise ModuleNotFoundError."""
    with pytest.raises(ModuleNotFoundError):
        import doc_bench.metrics.parsing.reading_order  # noqa: F401


def test_deleted_structure_recall_module_not_importable() -> None:
    """structure_recall.py was deleted; importing it must raise ModuleNotFoundError."""
    with pytest.raises(ModuleNotFoundError):
        import doc_bench.metrics.parsing.structure_recall  # noqa: F401


def test_deleted_layout_map_module_not_importable() -> None:
    """layout_map.py was deleted; importing it must raise ModuleNotFoundError."""
    with pytest.raises(ModuleNotFoundError):
        import doc_bench.metrics.parsing.layout_map  # noqa: F401


# ---------------------------------------------------------------------------
# Kept modules — must still be importable.
# ---------------------------------------------------------------------------


def test_kept_ned_importable() -> None:
    """ned.py (new module) must be importable."""
    from doc_bench.metrics.parsing import ned_score

    assert ned_score is not None
    assert callable(ned_score)


def test_kept_table_teds_importable() -> None:
    """table_teds.py must still be importable."""
    from doc_bench.metrics.parsing import table_teds

    assert table_teds is not None


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


def test_kept_datasets_importable() -> None:
    """Test that dataset loaders are still importable."""
    from doc_bench.datasets import load_dp_bench, load_omnidocbench

    assert load_dp_bench is not None
    assert load_omnidocbench is not None
