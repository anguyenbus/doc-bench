"""Tests for dump-dataset CLI command."""

import json

from click.testing import CliRunner


class TestDumpDatasetCommand:
    """Test suite for dump-dataset CLI command."""

    def test_dp_bench_export_with_small_limit(self, tmp_path):
        """Test DP-Bench export with small limit."""
        from doc_bench.cli.dump_dataset import main as dump_dataset

        # Setup DP-Bench test dataset
        dataset_dir = tmp_path / "dp_bench_data" / "dataset"
        pdfs_dir = dataset_dir / "pdfs"
        pdfs_dir.mkdir(parents=True)

        # Create reference.json with multiple documents
        ref_data = {
            "doc001.pdf": {"elements": [{"category": "Paragraph", "content": {"text": "Text 1"}}]},
            "doc002.pdf": {"elements": [{"category": "Header", "content": {"text": "Title"}}]},
            "doc003.pdf": {"elements": [{"category": "Table", "content": {"text": "Table"}}]},
        }

        (dataset_dir / "reference.json").write_text(json.dumps(ref_data))
        for doc_name in ref_data.keys():
            (pdfs_dir / doc_name).write_bytes(b"%PDF-1.4")

        # Create config file
        config_data = {
            "datasets": {
                "dp_bench": {"path": str(tmp_path / "dp_bench_data")},
                "omnidocbench": {"path": str(tmp_path / "omnidocbench_data")},
            },
            "metrics": {},
            "models": {},
        }
        config_path = tmp_path / "eval_config.yaml"
        import yaml

        config_path.write_text(yaml.dump(config_data))

        output_dir = tmp_path / "output"

        # Run dump-dataset command
        runner = CliRunner()
        result = runner.invoke(
            dump_dataset,
            [
                "--dataset",
                "dp_bench",
                "--output",
                str(output_dir),
                "--config",
                str(config_path),
                "--limit",
                "2",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert output_dir.exists()

        # Check that exactly 2 documents were exported
        exported_files = list(output_dir.glob("*.pdf"))
        assert len(exported_files) == 2

        # Check filenames use doc_id (stem without .pdf)
        expected_files = {"doc001.pdf", "doc002.pdf"}
        actual_files = {f.name for f in exported_files}
        assert actual_files == expected_files

    def test_omnidocbench_export_with_small_limit(self, tmp_path):
        """Test OmniDocBench export with small limit."""
        from doc_bench.cli.dump_dataset import main as dump_dataset

        # Setup OmniDocBench test dataset
        json_data = [
            {
                "page_info": {
                    "page_no": 1,
                    "height": 792,
                    "width": 612,
                    "image_path": "page-abc123.png",
                    "page_attribute": {
                        "language": "english",
                        "data_source": "research_report",
                        "fuzzy_scan": False,
                        "watermark": False,
                    },
                },
                "layout_dets": [{"text": "Sample text"}],
            },
            {
                "page_info": {
                    "page_no": 2,
                    "height": 792,
                    "width": 612,
                    "image_path": "page-def456.png",
                    "page_attribute": {
                        "language": "english",
                        "data_source": "book",
                        "fuzzy_scan": False,
                        "watermark": False,
                    },
                },
                "layout_dets": [{"text": "More text"}],
            },
        ]

        omnidocbench_dir = tmp_path / "omnidocbench_data"
        omnidocbench_dir.mkdir(parents=True)
        (omnidocbench_dir / "OmniDocBench.json").write_text(json.dumps(json_data))

        # Create dummy images directory
        images_dir = omnidocbench_dir / "images"
        images_dir.mkdir()
        (images_dir / "page-abc123.png").write_bytes(b"PNG_DATA")
        (images_dir / "page-def456.png").write_bytes(b"PNG_DATA")

        # Create config file
        config_data = {
            "datasets": {
                "dp_bench": {"path": str(tmp_path / "dp_bench_data")},
                "omnidocbench": {"path": str(omnidocbench_dir)},
            },
            "metrics": {},
            "models": {},
        }
        config_path = tmp_path / "eval_config.yaml"
        import yaml

        config_path.write_text(yaml.dump(config_data))

        output_dir = tmp_path / "output"

        # Run dump-dataset command
        runner = CliRunner()
        result = runner.invoke(
            dump_dataset,
            [
                "--dataset",
                "omnidocbench",
                "--output",
                str(output_dir),
                "--config",
                str(config_path),
                "--limit",
                "2",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert output_dir.exists()

        # Check that documents were exported
        exported_files = list(output_dir.glob("*.png"))
        assert len(exported_files) == 2

        # Check filenames use doc_id (stem from image_path)
        expected_files = {"page-abc123.png", "page-def456.png"}
        actual_files = {f.name for f in exported_files}
        assert actual_files == expected_files

    def test_manifest_json_creation_and_structure(self, tmp_path):
        """Test manifest.json creation and structure."""
        from doc_bench.cli.dump_dataset import main as dump_dataset

        # Setup minimal dataset
        dataset_dir = tmp_path / "dp_bench_data" / "dataset"
        pdfs_dir = dataset_dir / "pdfs"
        pdfs_dir.mkdir(parents=True)

        ref_data = {
            "doc001.pdf": {"elements": []},
        }

        (dataset_dir / "reference.json").write_text(json.dumps(ref_data))
        (pdfs_dir / "doc001.pdf").write_bytes(b"%PDF-1.4")

        # Create config file
        config_data = {
            "datasets": {
                "dp_bench": {"path": str(tmp_path / "dp_bench_data")},
                "omnidocbench": {"path": str(tmp_path / "omnidocbench_data")},
            },
            "metrics": {},
            "models": {},
        }
        config_path = tmp_path / "eval_config.yaml"
        import yaml

        config_path.write_text(yaml.dump(config_data))

        output_dir = tmp_path / "output"

        # Run dump-dataset command
        runner = CliRunner()
        result = runner.invoke(
            dump_dataset,
            [
                "--dataset",
                "dp_bench",
                "--output",
                str(output_dir),
                "--config",
                str(config_path),
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Check manifest.json exists and has correct structure
        manifest_path = output_dir / "manifest.json"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Verify required keys
        expected_keys = {
            "dataset_name",
            "dataset_version",
            "doc_bench_version",
            "dumped_at",
            "limit",
            "count",
            "documents",
        }
        assert set(manifest.keys()) == expected_keys

        # Verify documents array structure
        assert isinstance(manifest["documents"], list)
        assert len(manifest["documents"]) == 1

        doc_entry = manifest["documents"][0]
        assert "doc_id" in doc_entry
        assert "file" in doc_entry
        assert "sha256" in doc_entry
        assert doc_entry["doc_id"] == "doc001"
        assert doc_entry["file"] == "doc001.pdf"
        assert len(doc_entry["sha256"]) == 64  # SHA256 is 64 hex chars

    def test_output_directory_creation(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        from doc_bench.cli.dump_dataset import main as dump_dataset

        output_dir = tmp_path / "deeply" / "nested" / "output"

        assert not output_dir.exists()

        # Setup minimal dataset
        dataset_dir = tmp_path / "dp_bench_data" / "dataset"
        pdfs_dir = dataset_dir / "pdfs"
        pdfs_dir.mkdir(parents=True)

        ref_data = {"doc001.pdf": {"elements": []}}
        (dataset_dir / "reference.json").write_text(json.dumps(ref_data))
        (pdfs_dir / "doc001.pdf").write_bytes(b"%PDF-1.4")

        # Create config file
        config_data = {
            "datasets": {
                "dp_bench": {"path": str(tmp_path / "dp_bench_data")},
                "omnidocbench": {"path": str(tmp_path / "omnidocbench_data")},
            },
            "metrics": {},
            "models": {},
        }
        config_path = tmp_path / "eval_config.yaml"
        import yaml

        config_path.write_text(yaml.dump(config_data))

        # Run dump-dataset command
        runner = CliRunner()
        result = runner.invoke(
            dump_dataset,
            [
                "--dataset",
                "dp_bench",
                "--output",
                str(output_dir),
                "--config",
                str(config_path),
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert output_dir.exists()
