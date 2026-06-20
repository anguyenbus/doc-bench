"""
Tests for dependency pruning validation.

Verifies that removed RAG/observability dependencies are not available
and that kept parsing dependencies are still importable.
"""

import pytest


def test_removed_chromadb_not_importable() -> None:
    """Test that chromadb is not available."""
    with pytest.raises(ImportError, match="No module named 'chromadb'"):
        import chromadb  # noqa: F401


def test_removed_deepeval_not_importable() -> None:
    """Test that deepeval is not available."""
    with pytest.raises(ImportError, match="No module named 'deepeval'"):
        import deepeval  # noqa: F401


def test_removed_openai_not_importable() -> None:
    """Test that openai is not available."""
    with pytest.raises(ImportError, match="No module named 'openai'"):
        import openai  # noqa: F401


def test_removed_anthropic_not_importable() -> None:
    """Test that anthropic is not available."""
    with pytest.raises(ImportError, match="No module named 'anthropic'"):
        import anthropic  # noqa: F401


def test_removed_sentence_transformers_not_importable() -> None:
    """Test that sentence-transformers is not available."""
    with pytest.raises(ImportError, match="No module named 'sentence_transformers'"):
        import sentence_transformers  # noqa: F401


def test_removed_langchain_openai_not_importable() -> None:
    """Test that langchain-openai is not available."""
    with pytest.raises(ImportError, match="No module named 'langchain_openai'"):
        import langchain_openai  # noqa: F401


def test_removed_phoenix_not_importable() -> None:
    """Test that arize-phoenix is not available."""
    with pytest.raises(ImportError, match="No module named 'phoenix'"):
        import phoenix  # noqa: F401


def test_removed_fastapi_not_importable() -> None:
    """Test that fastapi is not available."""
    with pytest.raises(ImportError, match="No module named 'fastapi'"):
        import fastapi  # noqa: F401


def test_removed_uvicorn_not_importable() -> None:
    """Test that uvicorn is not available."""
    with pytest.raises(ImportError, match="No module named 'uvicorn'"):
        import uvicorn  # noqa: F401


def test_removed_faiss_not_importable() -> None:
    """Test that faiss-cpu is not available."""
    with pytest.raises(ImportError, match="No module named 'faiss'"):
        import faiss  # noqa: F401


def test_kept_torch_importable() -> None:
    """Test that torch is still available."""
    import torch

    assert torch is not None


def test_removed_torchmetrics_not_importable() -> None:
    """Test that torchmetrics was pruned and is no longer available.

    torchmetrics was removed from [project.dependencies]; this guard fails
    loudly if it is reintroduced.
    """
    with pytest.raises(ImportError, match="No module named 'torchmetrics'"):
        import torchmetrics  # noqa: F401


def test_kept_huggingface_hub_importable() -> None:
    """Test that huggingface-hub is still available."""
    from huggingface_hub import snapshot_download

    assert snapshot_download is not None


def test_kept_pydantic_importable() -> None:
    """Test that pydantic is still available."""
    import pydantic

    assert pydantic is not None


def test_kept_jsonschema_importable() -> None:
    """Test that jsonschema is still available."""
    import jsonschema

    assert jsonschema is not None


def test_kept_polars_importable() -> None:
    """Test that polars is still available."""
    import polars

    assert polars is not None


def test_kept_docling_importable() -> None:
    """Test that docling is still available."""
    import docling

    assert docling is not None
