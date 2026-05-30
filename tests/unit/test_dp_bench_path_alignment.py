"""
Tests for DP-Bench dataset loader path flexibility.

Tests that the loader supports both flat and dataset/ subdirectory layouts
for Docker container compatibility.
"""

import json

import pytest


class TestDPBenchPathFlexibility:
    """Tests for DP-Bench loader supporting both layouts."""

    def test_loader_with_flat_layout(self, tmp_path):
        """Test loader works with flat layout (reference.json at root)."""
        from doc_bench.datasets.dp_bench import load_dp_bench

        # Create flat layout structure
        dp_bench_dir = tmp_path / "dp_bench"
        dp_bench_dir.mkdir()

        # Create reference.json with one document
        reference = {
            "test1.pdf": {
                "elements": [
                    {
                        "page": 1,
                        "coordinates": [{"x": 100, "y": 100}],
                        "category": "Paragraph",
                        "content": {"text": "Test content"},
                    }
                ]
            }
        }

        with open(dp_bench_dir / "reference.json", "w") as f:
            json.dump(reference, f)

        # Create pdfs directory
        pdfs_dir = dp_bench_dir / "pdfs"
        pdfs_dir.mkdir()

        # Create a dummy PDF
        (pdfs_dir / "test1.pdf").write_bytes(b"%PDF-1.4 dummy")

        # Load dataset
        results = list(load_dp_bench(dp_bench_dir))

        assert len(results) == 1
        doc_id, pdf_path, gold_elements = results[0]
        assert doc_id is not None
        assert pdf_path == pdfs_dir / "test1.pdf"
        assert gold_elements == reference["test1.pdf"]

    def test_loader_with_dataset_subdirectory_layout(self, tmp_path):
        """Test loader works with dataset/ subdirectory layout."""
        from doc_bench.datasets.dp_bench import load_dp_bench

        # Create dataset subdirectory layout
        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()

        # Create reference.json
        reference = {
            "test2.pdf": {
                "elements": [
                    {
                        "page": 1,
                        "coordinates": [{"x": 100, "y": 100}],
                        "category": "Header",
                        "content": {"text": "Header"},
                    }
                ]
            }
        }

        with open(dataset_dir / "reference.json", "w") as f:
            json.dump(reference, f)

        # Create pdfs directory
        pdfs_dir = dataset_dir / "pdfs"
        pdfs_dir.mkdir()

        # Create a dummy PDF
        (pdfs_dir / "test2.pdf").write_bytes(b"%PDF-1.4 dummy")

        # Load dataset (should find dataset/ subdirectory)
        results = list(load_dp_bench(tmp_path))

        assert len(results) == 1
        doc_id, pdf_path, gold_elements = results[0]
        assert doc_id is not None
        assert pdf_path == pdfs_dir / "test2.pdf"
        assert gold_elements == reference["test2.pdf"]

    def test_loader_path_resolution_via_config(self, tmp_path):
        """Test path resolution works via config settings."""
        from doc_bench.datasets.dp_bench import load_dp_bench

        # Create config-like structure
        data_dir = tmp_path / "data" / "parsing" / "dp_bench"
        data_dir.mkdir(parents=True)

        reference = {
            "test3.pdf": {
                "elements": [
                    {
                        "page": 1,
                        "coordinates": [{"x": 100, "y": 100}],
                        "category": "Table",
                        "content": {"text": "Table data"},
                    }
                ]
            }
        }

        with open(data_dir / "reference.json", "w") as f:
            json.dump(reference, f)

        pdfs_dir = data_dir / "pdfs"
        pdfs_dir.mkdir()
        (pdfs_dir / "test3.pdf").write_bytes(b"%PDF-1.4 dummy")

        # Test loading from nested path
        results = list(load_dp_bench(data_dir))

        assert len(results) == 1
        doc_id, pdf_path, gold_elements = results[0]
        assert pdf_path.exists()

    def test_loader_fails_on_missing_structure(self, tmp_path):
        """Test loader raises FileNotFoundError when structure is invalid."""
        from doc_bench.datasets.dp_bench import load_dp_bench

        # Empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="DP-Bench not found"):
            list(load_dp_bench(empty_dir))

    def test_loader_skips_missing_pdfs(self, tmp_path):
        """Test loader gracefully skips PDFs that don't exist."""
        from doc_bench.datasets.dp_bench import load_dp_bench

        dp_bench_dir = tmp_path / "dp_bench"
        dp_bench_dir.mkdir()

        reference = {
            "exists.pdf": {
                "elements": [
                    {
                        "page": 1,
                        "coordinates": [{"x": 100, "y": 100}],
                        "category": "Paragraph",
                        "content": {"text": "Exists"},
                    }
                ]
            },
            "missing.pdf": {
                "elements": [
                    {
                        "page": 1,
                        "coordinates": [{"x": 100, "y": 100}],
                        "category": "Paragraph",
                        "content": {"text": "Missing"},
                    }
                ]
            },
        }

        with open(dp_bench_dir / "reference.json", "w") as f:
            json.dump(reference, f)

        pdfs_dir = dp_bench_dir / "pdfs"
        pdfs_dir.mkdir()
        (pdfs_dir / "exists.pdf").write_bytes(b"%PDF-1.4 dummy")
        # Don't create missing.pdf

        results = list(load_dp_bench(dp_bench_dir))

        # Should only return the PDF that exists
        assert len(results) == 1
        assert results[0][0] is not None  # doc_id should be generated
