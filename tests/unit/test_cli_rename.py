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

    # Check the current doc-bench entry point (per [project.scripts]).
    assert "doc-bench" in scripts
    assert scripts["doc-bench"] == "doc_bench.runners.run_parsing_eval:main"

    # Check the doc-bench-* subcommands are configured.
    expected_subcommands = {
        "doc-bench-dump-dataset": "doc_bench.cli.dump_dataset:main",
        "doc-bench-download": "doc_bench.cli.download:main",
        "doc-bench-list-datasets": "doc_bench.cli.list_datasets:main",
        "doc-bench-smoke-test": "doc_bench.cli.smoke_test:main",
        "doc-bench-setup": "doc_bench.cli.setup:main",
    }
    for cmd, target in expected_subcommands.items():
        assert cmd in scripts, f"Expected subcommand {cmd} in scripts"
        assert scripts[cmd] == target

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
