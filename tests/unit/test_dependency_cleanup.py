"""
Phase 7 gap-fill tests for the 2026-06-07 NED/metrics simplification spec.

Covers:
- Dependency pruning: sacrebleu and nltk must be absent from [project.dependencies]
  (they were removed from the doc-bench runtime; the frozen generator still needs them)
- Levenshtein package presence in [project.dependencies]
- ned_score importable via the top-level parsing package
- Degraded-mode warning emitted by markdown_to_pseudo_elements / asm_ned_score_from_markdown
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Final
from unittest.mock import MagicMock, patch

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent
PYPROJECT_PATH: Final[Path] = REPO_ROOT / "pyproject.toml"


def _read_pyproject() -> dict:
    """Return parsed pyproject.toml as a dict."""
    with PYPROJECT_PATH.open("rb") as fh:
        return tomllib.load(fh)


# ---------------------------------------------------------------------------
# Dependency pruning assertions (sacrebleu, nltk absent from RUNTIME deps).
# NOTE: sacrebleu and nltk are retained in [dependency-groups].generator
# because the frozen vendored docling_baseline/runners/base.py still calls
# bleu_score/meteor_score via text_similarity.py. They must NOT be in
# [project.dependencies] (the shipped doc-bench runtime no longer uses them).
# ---------------------------------------------------------------------------


def test_sacrebleu_absent_from_project_dependencies() -> None:
    """sacrebleu must not appear in [project.dependencies] (runtime deps).

    NOTE: sacrebleu may legitimately appear in [dependency-groups].generator
    because the frozen vendored docling_baseline generator still needs it.
    This test only checks the shipped runtime dependencies.
    """
    pyproject = _read_pyproject()
    deps = pyproject["project"]["dependencies"]
    for dep in deps:
        assert "sacrebleu" not in dep.lower(), (
            f"sacrebleu found in [project.dependencies]: {dep!r}. "
            "It was removed from the doc-bench runtime as part of the "
            "NED/metrics simplification spec. It may remain in the generator group."
        )


def test_nltk_absent_from_project_dependencies() -> None:
    """nltk must not appear in [project.dependencies] (runtime deps).

    NOTE: nltk may legitimately appear in [dependency-groups].generator
    because the frozen vendored docling_baseline generator still needs it.
    This test only checks the shipped runtime dependencies.
    """
    pyproject = _read_pyproject()
    deps = pyproject["project"]["dependencies"]
    for dep in deps:
        assert "nltk" not in dep.lower(), (
            f"nltk found in [project.dependencies]: {dep!r}. "
            "It was removed from the doc-bench runtime as part of the "
            "NED/metrics simplification spec. It may remain in the generator group."
        )


def test_levenshtein_present_in_project_dependencies() -> None:
    """Levenshtein (python-Levenshtein) must be in [project.dependencies]."""
    pyproject = _read_pyproject()
    deps = pyproject["project"]["dependencies"]
    found = any("levenshtein" in dep.lower() for dep in deps)
    assert found, (
        "Levenshtein package not found in [project.dependencies]. "
        "It is required for the NED metric (ned.py)."
    )


# ---------------------------------------------------------------------------
# ned_score importable from top-level parsing package.
# ---------------------------------------------------------------------------


def test_ned_score_importable_from_top_level_parsing_package() -> None:
    """ned_score must be importable via doc_bench.metrics.parsing."""
    from doc_bench.metrics.parsing import ned_score

    assert callable(ned_score)
    # Quick sanity: identical strings score 1.0
    assert ned_score("hello", "hello") == 1.0


# ---------------------------------------------------------------------------
# Degraded-mode warning emitted when markdown_to_pseudo_elements is called.
# ---------------------------------------------------------------------------


def test_markdown_to_pseudo_elements_emits_rich_warning() -> None:
    """markdown_to_pseudo_elements must emit a rich warning to stderr."""
    from doc_bench.metrics.parsing.asm import markdown_to_pseudo_elements

    mock_console = MagicMock()
    with patch("doc_bench.metrics.parsing.asm._console", mock_console):
        result = markdown_to_pseudo_elements("# Hello\n\nSome paragraph.")

    # The warning must have been printed
    mock_console.print.assert_called_once()
    call_args = mock_console.print.call_args[0][0]
    assert "WARNING" in call_args or "DEGRADED" in call_args.upper()

    # The result must still be a non-empty list with one pseudo-element
    assert len(result) == 1
    assert result[0]["content"]["text"] == "# Hello\n\nSome paragraph."
