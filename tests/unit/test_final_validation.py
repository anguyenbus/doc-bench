"""
Tests for final integration validation.

Verifies end-to-end functionality after all restructuring changes.
"""

from pathlib import Path
import subprocess
import sys


def test_doc_bench_package_importable() -> None:
    """Test that doc_bench package can be imported."""
    import doc_bench

    assert doc_bench is not None
    assert hasattr(doc_bench, "__version__")


def test_all_parsing_metrics_importable() -> None:
    """Test that all parsing metrics are importable."""
    from doc_bench.metrics.parsing import (
        nid,
        table_teds,
        text_similarity,
        reading_order,
        mhs,
        structure_recall,
        text_fidelity,
        layout_map,
    )

    assert nid is not None
    assert table_teds is not None
    assert text_similarity is not None
    assert reading_order is not None
    assert mhs is not None
    assert structure_recall is not None
    assert text_fidelity is not None
    assert layout_map is not None


def test_all_datasets_importable() -> None:
    """Test that all dataset loaders are importable."""
    from doc_bench.datasets import load_dp_bench, load_omnidocbench

    assert load_dp_bench is not None
    assert load_omnidocbench is not None


def test_eval_parsing_command_works() -> None:
    """Test that eval-parsing CLI command is available."""
    result = subprocess.run(
        [sys.executable, "-m", "doc_bench.runners.run_parsing_eval", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0 or "usage" in result.stderr.lower()


def test_no_rag_modules_importable() -> None:
    """Test that RAG modules cannot be imported."""
    modules_to_test = [
        ("doc_bench.adapters.rag_adapter", "RAG adapter"),
        ("doc_bench.adapters.deepeval_adapter", "DeepEval adapter"),
        ("doc_bench.adapters.phoenix_eval_adapter", "Phoenix adapter"),
        ("doc_bench.adapters.embeddings", "Embeddings module"),
        ("doc_bench.experiments", "Experiments module"),
        ("doc_bench.cli.check", "CLI check module"),
    ]

    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            assert False, f"{description} ({module_name}) should not be importable"
        except ImportError:
            pass  # Expected


def test_schemas_exist() -> None:
    """Test that required schemas exist."""
    contracts_dir = Path(__file__).parent.parent.parent / "contracts"

    # Kept schemas
    parser_output = contracts_dir / "parser_output.schema.json"
    results_v1 = contracts_dir / "results_v1.schema.json"

    assert parser_output.exists(), "parser_output.schema.json should exist"
    assert results_v1.exists(), "results_v1.schema.json should exist"

    # Deleted schemas
    deleted_schemas = [
        "rag_query_output.schema.json",
        "eval_questions.schema.json",
        "legal_rag_bench_query_output.schema.json",
    ]

    for schema_name in deleted_schemas:
        schema_path = contracts_dir / schema_name
        assert not schema_path.exists(), f"{schema_name} should be deleted"


def test_config_required_sections_correct() -> None:
    """Test that config REQUIRED_SECTIONS is parsing-only."""
    from doc_bench.config import REQUIRED_SECTIONS

    expected = {"datasets", "metrics", "models"}
    assert REQUIRED_SECTIONS == expected, \
        f"REQUIRED_SECTIONS should be {expected}, got {REQUIRED_SECTIONS}"


def test_no_phoenix_dependencies() -> None:
    """Test that Phoenix dependencies are not installed."""
    try:
        import phoenix
        assert False, "Phoenix should not be installed"
    except ImportError:
        pass  # Expected

    try:
        import arize
        assert False, "Arize Phoenix should not be installed"
    except ImportError:
        pass  # Expected


def test_no_rag_dependencies() -> None:
    """Test that RAG dependencies are not installed."""
    try:
        import chromadb
        assert False, "ChromaDB should not be installed"
    except ImportError:
        pass  # Expected

    try:
        import deepeval
        assert False, "DeepEval should not be installed"
    except ImportError:
        pass  # Expected

    try:
        import openai
        assert False, "OpenAI should not be installed"
    except ImportError:
        pass  # Expected


def test_parsing_dependencies_installed() -> None:
    """Test that parsing dependencies are installed."""
    import torch
    import torchmetrics
    import polars
    import docling
    import jsonschema
    import pydantic

    assert torch is not None
    assert torchmetrics is not None
    assert polars is not None
    assert docling is not None
    assert jsonschema is not None
    assert pydantic is not None
