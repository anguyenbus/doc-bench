"""Dependency-isolation guard for the vendored docling-baseline generator.

These tests enforce FR7/AC6 of the docling-baseline generator integration spec:
the generator's heavy dependencies must live ONLY in the dev-only
``[dependency-groups]`` ``generator`` set, and must never leak into the shipped
``doc-bench`` distribution via ``[project.dependencies]`` or the ``[docling]``
optional extra.

Nuance on shared libraries
--------------------------
The authoritative generator dependency list
(``@references/docling-baseline/pyproject.toml``) is:

    docling>=2, docling-core, apted, rapidfuzz, beautifulsoup4, lxml, nltk,
    sacrebleu, jsonschema, polars, click, pydantic, beartype

Many of those names (``apted``, ``rapidfuzz``, ``beautifulsoup4``, ``lxml``,
``nltk``, ``sacrebleu``, ``jsonschema``, ``polars``, ``click``, ``pydantic``,
``beartype``) ALSO legitimately appear in ``doc-bench``'s own runtime
``[project.dependencies]`` because ``doc-bench`` uses them at runtime. The
isolation guarantee that actually matters is about the dependencies that are
genuinely GENERATOR-EXCLUSIVE and must not leak into the runtime distribution:

    * ``docling``      -- only permitted in the optional ``[docling]`` extra,
                          never in ``[project.dependencies]``.
    * ``docling-core`` -- the generator's transitive doc-model dependency; it
                          must not appear anywhere in the core distribution
                          (neither ``[project.dependencies]`` nor ``[docling]``).

So the assertions below are designed around those genuinely generator-exclusive
deps rather than failing on shared runtime libraries.

Verification command (Task 2.3)
-------------------------------
A no-group ``uv sync`` must NOT pull the generator-only deps into the default
environment. Verify with::

    uv sync
    uv pip list | grep -iE '^(docling|docling-core)\b'   # expect no output

The generator deps are only installed via ``uv sync --group generator`` (or the
``make regen-fixtures`` target, which uses ``uv run --python 3.13 --group
generator``).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Final

import pytest

PYPROJECT_PATH: Final[Path] = Path(__file__).resolve().parent.parent / "pyproject.toml"

# The full authoritative generator dependency list (FR2). Used to assert the
# generator group is fully populated.
GENERATOR_DEPS: Final[tuple[str, ...]] = (
    "docling",
    "docling-core",
    "apted",
    "rapidfuzz",
    "beautifulsoup4",
    "lxml",
    "nltk",
    "sacrebleu",
    "jsonschema",
    "polars",
    "click",
    "pydantic",
    "beartype",
)

# Dependencies that are genuinely generator-EXCLUSIVE and must never leak into
# the shipped doc-bench distribution. The rest of GENERATOR_DEPS are shared
# runtime libs that doc-bench legitimately depends on, so they are not asserted
# absent from [project.dependencies] (see module docstring).
GENERATOR_ONLY_DEPS: Final[tuple[str, ...]] = ("docling", "docling-core")


def _dep_names(requirements: list[str]) -> set[str]:
    """Return the normalised distribution names from a PEP 508 requirement list.

    Strips version specifiers, extras, and markers, lower-cases the name, and
    normalises underscores to hyphens so ``docling-core`` and ``docling_core``
    compare equal.
    """
    names: set[str] = set()
    for raw in requirements:
        token = raw.strip()
        # Cut markers / environment conditions.
        token = token.split(";", 1)[0]
        # Cut version specifiers and extras: stop at the first non-name char.
        name = ""
        for ch in token:
            if ch.isalnum() or ch in "-_.":
                name += ch
            else:
                break
        if name:
            names.add(name.strip().lower().replace("_", "-"))
    return names


@pytest.fixture(scope="module")
def pyproject() -> dict[str, object]:
    with PYPROJECT_PATH.open("rb") as handle:
        return tomllib.load(handle)


def test_generator_group_contains_all_generator_deps(
    pyproject: dict[str, object],
) -> None:
    """The dev-only `generator` group holds the full authoritative dep list."""
    groups = pyproject["dependency-groups"]
    assert isinstance(groups, dict)
    assert "generator" in groups, "missing [dependency-groups] generator set"
    group_names = _dep_names(list(groups["generator"]))
    expected = {dep.lower().replace("_", "-") for dep in GENERATOR_DEPS}
    missing = expected - group_names
    assert not missing, f"generator group missing deps: {sorted(missing)}"


def test_generator_only_deps_absent_from_project_dependencies(
    pyproject: dict[str, object],
) -> None:
    """`docling`/`docling-core` must never be in core [project.dependencies].

    Shared libs (rapidfuzz, lxml, ...) are intentionally NOT asserted absent
    here because doc-bench depends on them at runtime; only the
    generator-exclusive deps are checked.
    """
    project = pyproject["project"]
    assert isinstance(project, dict)
    core_names = _dep_names(list(project["dependencies"]))
    leaked = {dep for dep in GENERATOR_ONLY_DEPS if dep.lower().replace("_", "-") in core_names}
    assert not leaked, (
        f"generator-only deps leaked into [project.dependencies]: " f"{sorted(leaked)}"
    )


def test_docling_extra_contains_only_docling(
    pyproject: dict[str, object],
) -> None:
    """The [docling] optional extra holds only `docling>=2`, nothing else.

    In particular `docling-core` and the other generator-only deps must not be
    smuggled into the runtime extra.
    """
    project = pyproject["project"]
    assert isinstance(project, dict)
    optional = project["optional-dependencies"]
    assert isinstance(optional, dict)
    docling_extra = _dep_names(list(optional["docling"]))
    assert docling_extra == {"docling"}, (
        f"[docling] extra must contain only docling; found: " f"{sorted(docling_extra)}"
    )
    assert "docling-core" not in docling_extra
