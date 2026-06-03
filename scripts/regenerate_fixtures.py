#!/usr/bin/env python3
"""
Regenerate the DP-Bench and OmniDocBench baseline-score fixtures in-place.

This script drives the vendored ``docling_baseline`` generator (under the dev-only
``generator`` dependency-group) against ``src/doc_bench/fixtures/`` so that the
baseline-score fixtures for the two in-scope datasets can be regenerated from
real source. The generator is invoked AS A MODULE
(``python -m docling_baseline.cli <dataset> <fixtures_dir>``), not via a
registered console script.

On copy, the DP-Bench output is renamed: ``dp_bench_results.json`` becomes
``dpbench_results.json`` (doc-bench's canonical fixture name); the
``omnidocbench_results.json`` output passes through unchanged. The produced
``*_results.json`` files and ``manifest.json`` are placed into
``src/doc_bench/fixtures/``. Because the run is in-place (inputs and outputs are
co-located in the fixtures directory), the copy step is a self-copy in normal
operation; the rename mapping is still applied.

ATO-Bench is OUT OF SCOPE: this script only handles DP-Bench and OmniDocBench.

Usage:
    python scripts/regenerate_fixtures.py [--dataset DATASET]

    # Or via the env-var override honoured by `make regen-fixtures`:
    DATASET=dp_bench python scripts/regenerate_fixtures.py

Exit codes (mirroring scripts/verify_equivalence.py):
    0: Regeneration succeeded
    2: Error in execution
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final

# Repo root resolved relative to this file (scripts/), NOT the cwd, so the
# default fixtures directory is stable regardless of where the script is run.
REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURES_DIR: Final[Path] = REPO_ROOT / "src" / "doc_bench" / "fixtures"

# In-scope datasets, in deterministic run order. ATO-Bench is excluded by design.
IN_SCOPE_DATASETS: Final[tuple[str, ...]] = ("dp_bench", "omnidocbench")

# Generator output filename -> doc-bench fixture filename. Only DP-Bench is
# renamed; OmniDocBench passes through unchanged.
RESULTS_RENAME: Final[dict[str, str]] = {
    "dp_bench_results.json": "dpbench_results.json",
    "omnidocbench_results.json": "omnidocbench_results.json",
}


def select_datasets(dataset: str | None) -> list[str]:
    """Resolve which datasets to regenerate.

    Args:
        dataset: A single dataset name to regenerate, or ``None`` to regenerate
            all in-scope datasets (DP-Bench + OmniDocBench).

    Returns:
        The ordered list of dataset names to regenerate.

    Raises:
        ValueError: If ``dataset`` names an unknown or out-of-scope dataset
            (e.g. ``ato_bench``).

    """
    if dataset is None:
        return list(IN_SCOPE_DATASETS)

    if dataset not in IN_SCOPE_DATASETS:
        raise ValueError(
            f"Unknown or out-of-scope dataset: {dataset!r}. "
            f"In-scope datasets: {', '.join(IN_SCOPE_DATASETS)}."
        )
    return [dataset]


def run_generator(dataset: str, target_dir: Path) -> None:
    """Invoke the vendored generator for a single dataset, in-place.

    Runs ``python -m docling_baseline.cli <dataset> <target_dir>`` so the
    generator is invoked as a module under the dev ``generator`` group rather
    than via a registered console script. The generator writes
    ``<dataset>_results.json`` (and refreshes ``manifest.json``) into
    ``target_dir``.

    Args:
        dataset: One of the in-scope dataset subcommand names.
        target_dir: The fixtures directory the generator runs against.

    Raises:
        subprocess.CalledProcessError: If the generator process exits non-zero.

    """
    # NOTE: sys.executable keeps us on the active (uv-provisioned 3.13) interpreter.
    _ = subprocess.run(  # noqa: S603 - args are constant + repo-controlled
        [
            sys.executable,
            "-m",
            "docling_baseline.cli",
            dataset,
            str(target_dir),
        ],
        check=True,
    )


def copy_results(source_dir: Path, fixtures_dir: Path, datasets: list[str]) -> list[Path]:
    """Copy produced results into the fixtures dir, applying the DP-Bench rename.

    Copies each dataset's ``<dataset>_results.json`` (renaming DP-Bench to
    ``dpbench_results.json``) plus ``manifest.json`` into ``fixtures_dir``. When
    ``source_dir`` equals ``fixtures_dir`` (the in-place default) the copy is a
    no-op self-copy except for the DP-Bench rename.

    Args:
        source_dir: Directory the generator wrote its outputs to.
        fixtures_dir: doc-bench fixtures directory to copy into.
        datasets: The datasets that were regenerated.

    Returns:
        The list of destination paths written.

    """
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for dataset in datasets:
        produced_name = f"{dataset}_results.json"
        dest_name = RESULTS_RENAME[produced_name]
        produced = source_dir / produced_name
        dest = fixtures_dir / dest_name
        if produced.resolve() != dest.resolve():
            _ = shutil.copyfile(produced, dest)
        written.append(dest)

    manifest = source_dir / "manifest.json"
    manifest_dest = fixtures_dir / "manifest.json"
    if manifest.exists() and manifest.resolve() != manifest_dest.resolve():
        _ = shutil.copyfile(manifest, manifest_dest)
    if manifest_dest.exists():
        written.append(manifest_dest)

    return written


def regenerate(fixtures_dir: Path, dataset: str | None) -> int:
    """Regenerate the selected dataset fixtures in-place.

    Args:
        fixtures_dir: The doc-bench fixtures directory (in-place target).
        dataset: A single dataset override, or ``None`` for all in-scope.

    Returns:
        Exit code (0 success, 2 error), mirroring verify_equivalence.py.

    """
    try:
        datasets = select_datasets(dataset)

        for ds in datasets:
            print(f"REGENERATING: {ds} -> {fixtures_dir}")
            run_generator(ds, fixtures_dir)

        # In-place run: source and destination are the same directory; the copy
        # step still applies the DP-Bench rename mapping.
        copied = copy_results(fixtures_dir, fixtures_dir, datasets)

        print("REGENERATION COMPLETE")
        for path in copied:
            print(f"  - {path}")
        return 0

    except ValueError as e:
        print(f"ERROR: {e}")
        return 2
    except subprocess.CalledProcessError as e:
        print(f"ERROR: generator failed (exit {e.returncode})")
        return 2
    except Exception as e:  # noqa: BLE001 - top-level guard, mirror reference script
        print(f"UNEXPECTED ERROR: {e}")
        return 2


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments; ``--dataset`` falls back to the ``DATASET`` env var."""
    parser = argparse.ArgumentParser(
        description=("Regenerate DP-Bench and OmniDocBench baseline fixtures in-place."),
    )
    _ = parser.add_argument(
        "--dataset",
        default=os.environ.get("DATASET"),
        help=(
            "Single dataset to regenerate (dp_bench or omnidocbench). "
            "Defaults to the DATASET env var, then to all in-scope datasets."
        ),
    )
    _ = parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=DEFAULT_FIXTURES_DIR,
        help="Fixtures directory (defaults to src/doc_bench/fixtures/).",
    )
    return parser.parse_args(argv)


def main() -> int:
    """Main entry point."""
    args = _parse_args(sys.argv[1:])
    dataset = args.dataset if args.dataset else None
    return regenerate(fixtures_dir=args.fixtures_dir, dataset=dataset)


if __name__ == "__main__":
    sys.exit(main())
