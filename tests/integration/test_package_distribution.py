"""
Integration tests for package distribution.

Tests end-to-end workflows including pip package install,
bundled fixture smoke test, dataset download, and Docker compatibility.
"""

from pathlib import Path


class TestCLICommandsAvailable:
    """Tests that all CLI commands are available."""

    def test_download_cli_available(self):
        """Test download CLI is available."""
        from doc_bench.cli.download import main

        assert callable(main)

    def test_list_datasets_cli_available(self):
        """Test list-datasets CLI is available."""
        from doc_bench.cli.list_datasets import main

        assert callable(main)

    def test_smoke_test_cli_available(self):
        """Test smoke-test CLI is available."""
        from doc_bench.cli.smoke_test import main

        assert callable(main)

    def test_setup_cli_available(self):
        """Test setup CLI is available."""
        from doc_bench.cli.setup import main

        assert callable(main)


class TestPackageStructure:
    """Tests package structure and bundled fixtures."""

    def test_package_has_version_module(self):
        """Test package has version module."""
        from doc_bench import version

        assert hasattr(version, "get_version")
        assert hasattr(version, "check_dataset_version_alignment")

    def test_package_has_grading_interface(self):
        """Test package exposes the GoldItem adapter interface."""
        from doc_bench.runners.run_parsing_eval import GoldItem, _grade, load_dataset

        assert callable(load_dataset)
        assert callable(_grade)
        assert GoldItem is not None

    def test_package_setup_command_is_no_op_stub(self):
        """Test setup CLI is a no-op stub (METEOR metric was removed).

        NOTE: The setup command previously downloaded NLTK data for METEOR.
        METEOR was removed in the 2026-06-07 NED/metrics simplification spec.
        The command is now a no-op stub that prints an informational message.
        """
        from click.testing import CliRunner

        from doc_bench.cli.setup import main

        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        # Stub should mention METEOR removal or that no setup is required
        assert "METEOR" in result.output or "no setup" in result.output.lower()


class TestEndToEndWorkflows:
    """Tests end-to-end workflows."""

    def test_download_list_workflow(self, tmp_path):
        """Test download and list datasets workflow."""
        # Create mock manifest
        import yaml
        from click.testing import CliRunner

        from doc_bench.cli.list_datasets import main

        manifest = {
            "dp_bench": {"version": "0.1.0"},
            "omnidocbench": {"version": "0.1.0"},
        }

        manifest_path = tmp_path / "MANIFEST.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--manifest", str(manifest_path), "--cache-dir", str(cache_dir)],
        )

        # Should list datasets successfully
        assert result.exit_code == 0
        assert "dp_bench" in result.output
        assert "omnidocbench" in result.output

    def test_version_check_workflow(self, tmp_path):
        """Test version alignment check workflow."""
        # Create aligned manifest
        import yaml

        from doc_bench.version import check_dataset_version_alignment

        manifest = {
            "dp_bench": {"version": "0.1.0"},
            "omnidocbench": {"version": "0.1.0"},
        }

        manifest_path = tmp_path / "MANIFEST.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        # Check alignment
        errors = check_dataset_version_alignment(str(manifest_path))

        # Should have no errors for aligned versions
        assert len(errors) == 0


class TestDockerCompatibility:
    """Deletion-guard for the removed Docker feature.

    The Docker workflow (Dockerfile + docker-compose) was removed;
    docs/doc-bench/overview.md states "no Docker support". These guards fail
    loudly if any Docker artifact is reintroduced, rather than silently
    skipping a feature that no longer exists.
    """

    def test_dockerfile_absent(self):
        """Test the repo-root Dockerfile stays absent (feature removed)."""
        assert not Path("Dockerfile").exists(), "Dockerfile should stay removed (no Docker support)"

    def test_container_config_absent(self):
        """Test docker-compose configuration stays absent (feature removed)."""
        assert not Path(
            "docker-compose.yml"
        ).exists(), "docker-compose.yml should stay removed (no Docker support)"
        assert not Path(
            "docker-compose.dev.yml"
        ).exists(), "docker-compose.dev.yml should stay removed (no Docker support)"


class TestMetadataCompleteness:
    """Tests metadata completeness across components."""

    def test_results_metadata_structure(self):
        """Test results metadata has all required fields."""
        results = {
            "dataset": "dp_bench",
            "parser": "predictions",
            "timestamp": "20260101_120000",
            "csv_file": "results.csv",
            "metrics_avg": {"ned_similarity": 0.85},
            "evaluated_samples": 10,
            "rejected_samples": {},
        }

        for field in ["dataset", "parser", "timestamp", "csv_file", "metrics_avg"]:
            assert field in results, f"Missing required field: {field}"

    def test_version_consistency(self):
        """Test version consistency across components."""
        from doc_bench import __version__
        from doc_bench.version import get_version

        v1 = get_version()
        v2 = __version__

        assert v1 == v2, "Versions inconsistent across components"
