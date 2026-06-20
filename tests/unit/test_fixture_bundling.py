"""
Tests for fixture bundling configuration.

Tests that the package builds correctly with bundled fixtures
and wheel size is within acceptable limits.
"""

from pathlib import Path

import pytest

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

    def test_pyproject_has_no_shared_data_config(self):
        """Test the shared-data wheel mapping was deliberately removed.

        The [tool.hatch.build.targets.wheel.shared-data] mapping was
        intentionally removed: it packaged a second copy of the fixtures under
        doc_bench-<ver>.data/data/. The in-package include-glob bundling is
        canonical (code reads fixtures via importlib.resources), so the
        shared-data mapping must stay absent.
        """
        pyproject_path = Path("pyproject.toml")

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        wheel_config = (
            config.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
        )
        assert (
            "shared-data" not in wheel_config
        ), "shared-data wheel mapping should be removed; include-globs are canonical"

        # The canonical bundling is the in-package include globs.
        include_patterns = config["tool"]["hatch"]["build"]["include"]
        assert "src/doc_bench/fixtures/**/*" in include_patterns

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
        assert (
            expected_scripts <= actual_scripts
        ), f"Missing entry points: {expected_scripts - actual_scripts}"

    def test_fixtures_directory_exists(self):
        """Test fixtures directory exists in source."""
        fixtures_dir = Path("src/doc_bench/fixtures")
        assert fixtures_dir.exists()

    def test_fixtures_python_module_removed(self):
        """Test the doc_bench.fixtures Python module was removed.

        The fixtures/__init__.py module (with get_fixture_path/load_manifest)
        was deleted in commit 23537f5; fixtures are now a pure data directory
        bundled via include-globs and read via importlib.resources. This guard
        fails loudly if the removed module API is reintroduced.
        """
        fixtures_init = Path("src/doc_bench/fixtures/__init__.py")
        assert (
            not fixtures_init.exists()
        ), f"fixtures Python module should stay removed: {fixtures_init}"

    def test_fixture_data_directory_present(self):
        """Test the bundled fixtures data directory exists with content."""
        fixtures_dir = Path("src/doc_bench/fixtures")
        assert fixtures_dir.exists()
        assert fixtures_dir.name == "fixtures"
        # Data subdirectories ship as package data via the include globs.
        assert (fixtures_dir / "dp_bench").exists()
        assert (fixtures_dir / "ato_bench").exists()

    def test_fixture_manifest_loadable(self):
        """Test the bundled fixtures manifest.json loads as a dict."""
        import json

        manifest_path = Path("src/doc_bench/fixtures/manifest.json")
        assert manifest_path.exists(), "fixtures manifest.json should be bundled"

        manifest = json.loads(manifest_path.read_text())
        assert isinstance(manifest, dict)
        assert len(manifest) > 0


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
        import os
        from pathlib import Path

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
            pytest.fail(
                f"Wheel size {size_mb:.1f}MB exceeds 100MB threshold - "
                f"consider separate fixture package"
            )

    def test_wheel_contains_fixtures(self):
        """Test built wheel contains fixture module."""
        import zipfile
        from pathlib import Path

        dist_dir = Path("dist")
        if not dist_dir.exists():
            pytest.skip("No dist directory - wheel not built yet")

        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            pytest.skip("No wheel file found in dist/")

        wheel = wheels[0]

        with zipfile.ZipFile(wheel, "r") as zf:
            files = zf.namelist()

        # Check for fixture data files (fixtures is now a pure data directory
        # bundled via include-globs; there is no longer a fixtures __init__.py).
        fixture_files = [
            f for f in files if "doc_bench/fixtures" in f or f.startswith("doc_bench/fixtures/")
        ]

        # At minimum, the fixtures manifest should be bundled as package data.
        assert any(
            f.endswith("doc_bench/fixtures/manifest.json") for f in fixture_files
        ), "Wheel should contain bundled fixture data (manifest.json)"
