"""
Tests for version alignment.

Tests package version matches dataset versions in MANIFEST.yaml
and CI check detects version misalignment.
"""

from unittest.mock import patch


class TestVersionModule:
    """Tests for version module functions."""

    def test_get_version_returns_string(self):
        """Test get_version returns a version string."""
        from doc_bench.version import get_version

        version = get_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_get_version_format(self):
        """Test get_version returns properly formatted version."""
        from doc_bench.version import get_version

        version = get_version()
        # Should match semver pattern like "0.1.0"
        parts = version.split(".")
        assert len(parts) >= 2  # At least major.minor

    def test_get_version_from_package(self):
        """Test get_version reads from package."""
        from doc_bench.version import get_version

        # Should successfully read version
        version = get_version()
        assert version is not None


class TestVersionAlignment:
    """Tests for version alignment checks."""

    def test_version_alignment_passes_when_aligned(self, tmp_path):
        """Test version alignment passes when versions match."""
        # Create mock manifest with matching version
        import yaml

        from doc_bench.version import check_dataset_version_alignment

        manifest = {
            "dp_bench": {"version": "0.1.0"},
            "omnidocbench": {"version": "0.1.0"},
        }

        manifest_path = tmp_path / "MANIFEST.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        with patch("doc_bench.version.get_version", return_value="0.1.0"):
            errors = check_dataset_version_alignment(str(manifest_path))
            assert len(errors) == 0  # No errors when aligned

    def test_version_alignment_fails_when_mismatched(self, tmp_path):
        """Test version alignment fails when versions don't match."""
        # Create mock manifest with mismatched version
        import yaml

        from doc_bench.version import check_dataset_version_alignment

        manifest = {
            "dp_bench": {"version": "0.2.0"},  # Different version
            "omnidocbench": {"version": "0.1.0"},
        }

        manifest_path = tmp_path / "MANIFEST.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        with patch("doc_bench.version.get_version", return_value="0.1.0"):
            errors = check_dataset_version_alignment(str(manifest_path))
            assert len(errors) > 0  # Should have errors
            assert "dp_bench" in str(errors)  # Should mention mismatched dataset

    def test_version_alignment_missing_manifest(self, tmp_path):
        """Test version alignment handles missing manifest."""
        from doc_bench.version import check_dataset_version_alignment

        missing_manifest = tmp_path / "MISSING_MANIFEST.yaml"
        errors = check_dataset_version_alignment(str(missing_manifest))

        # Should handle gracefully or return error
        assert isinstance(errors, list)

    def test_version_alignment_partial_match(self, tmp_path):
        """Test version alignment with some datasets matching."""
        # Create mock manifest with mixed versions
        import yaml

        from doc_bench.version import check_dataset_version_alignment

        manifest = {
            "dp_bench": {"version": "0.1.0"},  # Matches
            "omnidocbench": {"version": "0.2.0"},  # Doesn't match
            "other_dataset": {"version": "0.1.0"},  # Matches
        }

        manifest_path = tmp_path / "MANIFEST.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        with patch("doc_bench.version.get_version", return_value="0.1.0"):
            errors = check_dataset_version_alignment(str(manifest_path))
            # Should report only mismatched datasets
            assert len(errors) == 1
            assert "omnidocbench" in str(errors)


class TestCIVersionCheck:
    """Tests for CI version check functionality."""

    def test_ci_check_fails_on_misalignment(self, tmp_path):
        """Test CI check fails on version misalignment."""
        # Create misaligned manifest
        import yaml

        from doc_bench.version import check_dataset_version_alignment

        manifest = {
            "dp_bench": {"version": "0.2.0"},
        }

        manifest_path = tmp_path / "MANIFEST.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        with patch("doc_bench.version.get_version", return_value="0.1.0"):
            errors = check_dataset_version_alignment(str(manifest_path))
            # Should have errors for CI to fail
            assert len(errors) > 0

    def test_ci_check_passes_on_alignment(self, tmp_path):
        """Test CI check passes when versions align."""
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

        with patch("doc_bench.version.get_version", return_value="0.1.0"):
            errors = check_dataset_version_alignment(str(manifest_path))
            # Should have no errors for CI to pass
            assert len(errors) == 0
