"""
Tests for CLI rename validation.

Verifies that CLI commands have been renamed correctly.
"""

import subprocess
import sys


def test_eval_parsing_command_exists() -> None:
    """Test that eval-parsing command is available."""
    result = subprocess.run(
        [sys.executable, "-m", "doc_bench.runners.run_parsing_eval", "--help"],
        capture_output=True,
        text=True,
    )
    # Should show help for eval-parsing command
    assert result.returncode == 0 or "usage" in result.stderr.lower()


def test_removed_commands_not_available() -> None:
    """Test that removed RAG commands are not in pyproject.toml."""
    import tomllib
    from pathlib import Path

    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    scripts = config.get("project", {}).get("scripts", {})

    removed_commands = [
        "eval-rag",
        "generate-spans",
        "eval-replay",
        "chunking-compare",
        "eval-harness-check",
    ]

    for cmd in removed_commands:
        assert cmd not in scripts, f"Removed command {cmd} should not be in scripts"


def test_doc_bench_entry_point_works() -> None:
    """Test that doc-bench entry point is configured."""
    # Check that pyproject.toml has the right entry points
    import tomllib
    from pathlib import Path

    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    scripts = config.get("project", {}).get("scripts", {})

    # Check eval-parsing entry point
    assert "eval-parsing" in scripts
    assert scripts["eval-parsing"] == "doc_bench.runners.run_parsing_eval:main"

    # Check that removed commands are not in scripts
    removed = [
        "eval-rag",
        "generate-spans",
        "eval-replay",
        "chunking-compare",
        "eval-harness-check",
    ]
    for cmd in removed:
        assert cmd not in scripts
