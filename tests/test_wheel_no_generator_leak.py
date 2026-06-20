"""Mandatory wheel-leak guard: the vendored generator must never ship.

Spec: @agent-os/specs/2026-06-03-docling-baseline-generator-integration/spec.md
(FR6 / AC4).

The verbatim generator lives at ``src/docling_baseline/`` as a sibling of the
production ``src/doc_bench/`` package. Wheel packaging is scoped to
``src/doc_bench/**`` via ``[tool.hatch.build.targets.wheel]`` ``packages`` and the
``[tool.hatch.build]`` ``include`` globs, so the sibling is a never-matched path.
This test enforces that structural guarantee end-to-end by building the actual
wheel and inspecting its contents.

It is marked ``build`` because building the wheel is slow; the ``build`` marker is
deselected from the default fast loop (see ``addopts`` in ``pyproject.toml``) and
selected explicitly in CI with ``uv run pytest -m build``.
"""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import pytest

# NOTE: Repo root is two levels up from this test file (tests/ -> repo root).
REPO_ROOT: Path = Path(__file__).resolve().parents[1]


@pytest.mark.build
def test_wheel_excludes_docling_baseline_and_includes_doc_bench(tmp_path: Path) -> None:
    """Build the wheel and assert it ships doc_bench but never docling_baseline.

    Builds into an isolated ``tmp_path`` (not the repo ``dist/``) to avoid
    clobbering local artifacts, then inspects the wheel's archive members.

    Asserts:
        - ZERO archive paths contain ``docling_baseline`` (the wheel-leak guard).
        - At least one archive path contains ``doc_bench`` (so the test fails
          loudly on an empty/garbage build rather than passing vacuously).
    """
    out_dir = tmp_path / "dist"

    # WARN: Building the wheel is slow (invokes the hatchling backend); hence the
    # `build` marker keeps this out of the default fast loop.
    build = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert build.returncode == 0, (
        f"`uv build --wheel` failed (rc={build.returncode}).\n"
        f"stdout:\n{build.stdout}\nstderr:\n{build.stderr}"
    )

    wheels = sorted(out_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel in {out_dir}, found {wheels}"

    with zipfile.ZipFile(wheels[0], "r") as zf:
        members = zf.namelist()

    # Positive assertion: a real doc_bench build, not an empty artifact.
    doc_bench_members = [m for m in members if "doc_bench" in m]
    assert doc_bench_members, (
        f"wheel contains no doc_bench paths -- build produced nothing usable. " f"members={members}"
    )

    # The load-bearing guard: the vendored generator must never leak into the wheel.
    leaked = [m for m in members if "docling_baseline" in m]
    assert not leaked, f"docling_baseline leaked into the wheel: {leaked}"
