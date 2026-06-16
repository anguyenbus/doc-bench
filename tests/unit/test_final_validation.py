"""
Tests for final integration validation.

Verifies end-to-end functionality after all restructuring changes.
"""

import subprocess
import sys
from pathlib import Path


def test_doc_bench_package_importable() -> None:
    """Test that doc_bench package can be imported."""
    import doc_bench

    assert doc_bench is not None
    assert hasattr(doc_bench, "__version__")


def test_all_parsing_metrics_importable() -> None:
    """Test that all current parsing metrics are importable.

    NOTE: After the 2026-06-07 NED/metrics simplification spec, the retained
    parsing metrics are ned_score (NED) and table_teds (TEDS).  The old metrics
    (nid, mhs, reading_order, text_similarity, text_fidelity, structure_recall,
    layout_map) were deleted and must no longer be imported here.
    """
    from doc_bench.metrics.parsing import ned_score, table_teds

    assert ned_score is not None
    assert table_teds is not None


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
            raise AssertionError(f"{description} ({module_name}) should not be importable")
        except ImportError:
            pass  # Expected


def test_schemas_exist() -> None:
    """Test that required schemas exist.

    NOTE: The schema location was moved from contracts/ to src/doc_bench/fixtures/
    as part of the fixture bundling spec. The contracts/ directory may not exist
    in all environments; the canonical location is inside the package fixtures.
    """
    fixtures_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "doc_bench"
        / "fixtures"
    )
    parser_output = fixtures_dir / "parser_output.schema.json"
    assert parser_output.exists(), "parser_output.schema.json should exist in fixtures"


def test_config_required_sections_correct() -> None:
    """Test that config REQUIRED_SECTIONS requires only datasets."""
    from doc_bench.config import REQUIRED_SECTIONS

    assert "datasets" in REQUIRED_SECTIONS
    # metrics and models are not consumed by the grader — should not be required
    assert "metrics" not in REQUIRED_SECTIONS
    assert "models" not in REQUIRED_SECTIONS


def test_no_phoenix_dependencies() -> None:
    """Test that Phoenix dependencies are not installed."""
    try:
        import phoenix  # noqa: F401

        raise AssertionError("Phoenix should not be installed")
    except ImportError:
        pass  # Expected

    try:
        import arize  # noqa: F401

        raise AssertionError("Arize Phoenix should not be installed")
    except ImportError:
        pass  # Expected


def test_no_rag_dependencies() -> None:
    """Test that RAG dependencies are not installed."""
    try:
        import chromadb  # noqa: F401

        raise AssertionError("ChromaDB should not be installed")
    except ImportError:
        pass  # Expected

    try:
        import deepeval  # noqa: F401

        raise AssertionError("DeepEval should not be installed")
    except ImportError:
        pass  # Expected

    try:
        import openai  # noqa: F401

        raise AssertionError("OpenAI should not be installed")
    except ImportError:
        pass  # Expected


def test_parsing_dependencies_installed() -> None:
    """Test that core parsing dependencies are installed.

    NOTE: torchmetrics and torch were previously checked here but are not
    in the doc-bench dependency list. docling is an optional extra, not a
    core dependency. Only the core runtime dependencies are checked here.
    """
    import jsonschema
    import polars
    import pydantic

    assert polars is not None
    assert jsonschema is not None
    assert pydantic is not None
