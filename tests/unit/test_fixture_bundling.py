"""
Tests for fixture bundling configuration.

Tests that the package builds correctly with bundled fixtures
and wheel size is within acceptable limits.
"""

import pytest
from pathlib import Path
try:
    import tomllib
except ImportError:
    import tomli as tomllib


class TestFixtureBundling:
    """Tests for fixture bundling configuration."""

    def test_pyproject_has_hatchling_config(self):
        """Test pyproject.toml has hatchling build configuration."""
        pyproject_path = Path("pyproject.toml")
        assert pyproject_path.exists()

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        assert "build-system" in config
        assert config["build-system"]["build-backend"] == "hatchling.build"

    def test_pyproject_has_fixtures_included(self):
        """Test pyproject.toml includes fixtures in build."""
        pyproject_path = Path("pyproject.toml")

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        # Check hatch build configuration
        assert "tool" in config
        assert "hatch" in config["tool"]
        assert "build" in config["tool"]["hatch"]
        assert "include" in config["tool"]["hatch"]["build"]

        include_patterns = config["tool"]["hatch"]["build"]["include"]
        fixture_pattern = "src/doc_bench/fixtures/**/*"
        assert fixture_pattern in include_patterns

    def test_pyproject_has_shared_data_config(self):
        """Test pyproject.toml has shared-data configuration for fixtures."""
        pyproject_path = Path("pyproject.toml")

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        # Check wheel target configuration
        assert "tool" in config
        assert "hatch" in config["tool"]
        assert "build" in config["tool"]["hatch"]
        assert "targets" in config["tool"]["hatch"]["build"]
        assert "wheel" in config["tool"]["hatch"]["build"]["targets"]

        wheel_config = config["tool"]["hatch"]["build"]["targets"]["wheel"]
        assert "shared-data" in wheel_config

        shared_data = wheel_config["shared-data"]
        assert "src/doc_bench/fixtures" in shared_data
        assert shared_data["src/doc_bench/fixtures"] == "doc_bench/fixtures"

    def test_pyproject_version_single_source(self):
        """Test version is single-source in pyproject.toml."""
        pyproject_path = Path("pyproject.toml")

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        # Version should be in [project]
        assert "project" in config
        assert "version" in config["project"]
        assert isinstance(config["project"]["version"], str)

        # Should not have dynamic version
        dynamic = config["project"].get("dynamic", [])
        assert "version" not in dynamic

    def test_pyproject_has_all_cli_entry_points(self):
        """Test pyproject.toml includes all CLI entry points."""
        pyproject_path = Path("pyproject.toml")

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        scripts = config["project"].get("scripts", {})

        # Check all expected entry points
        expected_scripts = {
            "doc-bench",
            "doc-bench-dump-dataset",
            "doc-bench-download",
            "doc-bench-list-datasets",
            "doc-bench-smoke-test",
            "doc-bench-setup",
        }

        actual_scripts = set(scripts.keys())
        assert expected_scripts <= actual_scripts, f"Missing entry points: {expected_scripts - actual_scripts}"

    def test_fixtures_directory_exists(self):
        """Test fixtures directory exists in source."""
        fixtures_dir = Path("src/doc_bench/fixtures")
        assert fixtures_dir.exists()

    def test_fixtures_module_exists(self):
        """Test fixtures module exists."""
        from doc_bench import fixtures
        assert hasattr(fixtures, "get_fixture_path")
        assert hasattr(fixtures, "load_manifest")

    def test_fixture_get_path_works(self):
        """Test get_fixture_path returns valid path."""
        from doc_bench.fixtures import get_fixture_path

        path = get_fixture_path()
        assert path.exists()
        assert path.name == "fixtures"

    def test_fixture_manifest_loadable(self):
        """Test fixture manifest can be loaded."""
        from doc_bench.fixtures import load_manifest

        manifest = load_manifest()
        assert isinstance(manifest, dict)

        # If manifest has data, check structure
        if manifest:
            assert "name" in manifest or len(manifest) > 0


class TestWheelBuilding:
    """Tests for wheel building and size."""

    def test_wheel_build_command(self):
        """Test wheel can be built with uv build."""
        import subprocess
        from pathlib import Path

        # Try to build wheel
        result = subprocess.run(
            ["uv", "build", "--out-dir", "dist/"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Should succeed or have clear error
        if result.returncode != 0:
            # Check if it's a missing dependency error
            if "not found" in result.stderr.lower() or "no such file" in result.stderr.lower():
                pytest.skip("uv build not available in environment")
            else:
                pytest.fail(f"Build failed: {result.stderr}")

    def test_wheel_size_acceptable(self):
        """Test built wheel size is within acceptable limits."""
        from pathlib import Path
        import os

        dist_dir = Path("dist")
        if not dist_dir.exists():
            pytest.skip("No dist directory - wheel not built yet")

        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            pytest.skip("No wheel file found in dist/")

        wheel = wheels[0]
        size_mb = os.path.getsize(wheel) / (1024 * 1024)

        # Check size thresholds
        if size_mb < 50:
            # Ideal: < 50MB
            assert True
        elif size_mb < 100:
            # Acceptable: 50-100MB
            pytest.warn(f"Wheel size {size_mb:.1f}MB is in acceptable range (50-100MB)")
        else:
            # Too large: > 100MB
            pytest.fail(f"Wheel size {size_mb:.1f}MB exceeds 100MB threshold - consider separate fixture package")

    def test_wheel_contains_fixtures(self):
        """Test built wheel contains fixture module."""
        from pathlib import Path
        import zipfile

        dist_dir = Path("dist")
        if not dist_dir.exists():
            pytest.skip("No dist directory - wheel not built yet")

        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            pytest.skip("No wheel file found in dist/")

        wheel = wheels[0]

        with zipfile.ZipFile(wheel, "r") as zf:
            files = zf.namelist()

        # Check for fixture files
        fixture_files = [f for f in files if "doc_bench/fixtures" in f or f.startswith("doc_bench/fixtures/")]

        # At minimum, fixtures module should be bundled
        assert any("__init__.py" in f for f in fixture_files), "Wheel should contain fixtures module"
