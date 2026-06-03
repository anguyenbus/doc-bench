"""Tests for ``scripts/regenerate_fixtures.py``.

These tests enforce FR3 / AC2 of the docling-baseline generator integration
spec. The regeneration script drives the vendored generator in-place against
``src/doc_bench/fixtures/``, regenerating DP-Bench and OmniDocBench by default,
with a ``DATASET=`` override for a single dataset, and applying the DP-Bench
rename (``dp_bench_results.json`` -> ``dpbench_results.json``) on copy.

The generator invocation is mocked throughout so these tests stay fast and need
no Docling install (the generator-invocation step is a separate, monkeypatchable
function). The script mirrors ``scripts/verify_equivalence.py``'s exit-code
convention: ``0`` success, ``2`` error.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import regenerate_fixtures as rf


def _seed_outputs(fixtures_dir: Path, datasets: list[str]) -> None:
    """Create the generator's produced ``*_results.json`` outputs in-place.

    Stands in for a real generator pass: writes the raw (pre-rename) output file
    each runner would emit into ``fixtures_dir``.
    """
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    (fixtures_dir / "manifest.json").write_text(json.dumps({"seed": True}))
    for ds in datasets:
        (fixtures_dir / f"{ds}_results.json").write_text(json.dumps({"dataset": ds, "total": 1}))


def test_select_datasets_default_runs_both_in_scope() -> None:
    """All-by-default selects DP-Bench + OmniDocBench, never ATO-Bench."""
    selected = rf.select_datasets(None)
    assert selected == ["dp_bench", "omnidocbench"]
    assert "ato_bench" not in selected


def test_select_datasets_override_picks_single_dataset() -> None:
    """A ``DATASET=`` override selects exactly the one named dataset."""
    assert rf.select_datasets("dp_bench") == ["dp_bench"]
    assert rf.select_datasets("omnidocbench") == ["omnidocbench"]


def test_select_datasets_rejects_unknown_or_out_of_scope() -> None:
    """ATO-Bench and unknown names are rejected (out of scope)."""
    with pytest.raises(ValueError):
        rf.select_datasets("ato_bench")
    with pytest.raises(ValueError):
        rf.select_datasets("nope")


def test_copy_with_rename_applies_dpbench_mapping(tmp_path: Path) -> None:
    """DP-Bench output is renamed to ``dpbench_results.json`` on copy."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _seed_outputs(src, ["dp_bench"])
    dst.mkdir()

    copied = rf.copy_results(src, dst, ["dp_bench"])

    assert (dst / "dpbench_results.json").exists()
    assert not (dst / "dp_bench_results.json").exists()
    assert (dst / "manifest.json").exists()
    assert dst / "dpbench_results.json" in copied


def test_copy_omnidocbench_passes_through_unchanged(tmp_path: Path) -> None:
    """OmniDocBench output keeps its filename on copy."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _seed_outputs(src, ["omnidocbench"])
    dst.mkdir()

    rf.copy_results(src, dst, ["omnidocbench"])

    assert (dst / "omnidocbench_results.json").exists()
    payload = json.loads((dst / "omnidocbench_results.json").read_text())
    assert payload["dataset"] == "omnidocbench"


def test_regenerate_success_exit_code_and_mocked_generator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful run returns exit code 0 with the generator mocked.

    The generator invocation is monkeypatched to seed outputs rather than run a
    real Docling pass.
    """
    fixtures_dir = tmp_path / "fixtures"
    calls: list[str] = []

    def _fake_run(dataset: str, target_dir: Path) -> None:
        calls.append(dataset)
        _seed_outputs(target_dir, [dataset])

    monkeypatch.setattr(rf, "run_generator", _fake_run)

    code = rf.regenerate(fixtures_dir=fixtures_dir, dataset=None)

    assert code == 0
    assert calls == ["dp_bench", "omnidocbench"]
    assert (fixtures_dir / "dpbench_results.json").exists()
    assert (fixtures_dir / "omnidocbench_results.json").exists()


def test_regenerate_error_exit_code_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An error during generation returns the error exit code 2."""
    fixtures_dir = tmp_path / "fixtures"

    def _boom(dataset: str, target_dir: Path) -> None:
        raise RuntimeError("generator blew up")

    monkeypatch.setattr(rf, "run_generator", _boom)

    code = rf.regenerate(fixtures_dir=fixtures_dir, dataset="dp_bench")

    assert code == 2


def test_main_honours_dataset_env_var_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``main()`` is the seam ``make regen-fixtures`` drives.

    It reads the ``DATASET`` env var (the Makefile passes ``DATASET=`` through),
    runs end-to-end with the generator invocation mocked (no real Docling pass),
    and returns the success exit code. This exercises the argparse + env-var glue
    that the bare ``regenerate()`` unit tests do not.
    """
    fixtures_dir = tmp_path / "fixtures"
    calls: list[str] = []

    def _fake_run(dataset: str, target_dir: Path) -> None:
        calls.append(dataset)
        _seed_outputs(target_dir, [dataset])

    monkeypatch.setattr(rf, "run_generator", _fake_run)
    monkeypatch.setattr(
        rf.sys, "argv", ["regenerate_fixtures.py", "--fixtures-dir", str(fixtures_dir)]
    )
    monkeypatch.setenv("DATASET", "dp_bench")

    code = rf.main()

    assert code == 0
    assert calls == ["dp_bench"]
    assert (fixtures_dir / "dpbench_results.json").exists()
    assert not (fixtures_dir / "omnidocbench_results.json").exists()


def test_main_empty_dataset_env_runs_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty ``DATASET`` (Makefile passes ``DATASET=""`` when unset) runs all.

    ``make regen-fixtures`` always passes ``DATASET="$(DATASET)"``; when the user
    does not override it the value is the empty string, which must be treated as
    "regenerate every in-scope dataset", not as an unknown dataset name.
    """
    fixtures_dir = tmp_path / "fixtures"
    calls: list[str] = []

    def _fake_run(dataset: str, target_dir: Path) -> None:
        calls.append(dataset)
        _seed_outputs(target_dir, [dataset])

    monkeypatch.setattr(rf, "run_generator", _fake_run)
    monkeypatch.setattr(
        rf.sys, "argv", ["regenerate_fixtures.py", "--fixtures-dir", str(fixtures_dir)]
    )
    monkeypatch.setenv("DATASET", "")

    code = rf.main()

    assert code == 0
    assert calls == ["dp_bench", "omnidocbench"]


def test_run_generator_invokes_cli_as_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``run_generator`` invokes the generator AS A MODULE (D9), not a script.

    The command must be ``<python> -m docling_baseline.cli <dataset> <dir>`` so
    the vendored generator runs under the dev ``generator`` group without a
    registered console-script entry point. ``subprocess.run`` is mocked so no
    real process spawns.
    """
    captured: dict[str, object] = {}

    def _fake_run(args: list[str], **kwargs: object):  # type: ignore[no-untyped-def]
        captured["args"] = args
        captured["check"] = kwargs.get("check")
        return None

    monkeypatch.setattr(rf.subprocess, "run", _fake_run)

    rf.run_generator("dp_bench", tmp_path)

    args = captured["args"]
    assert isinstance(args, list)
    assert args[0] == rf.sys.executable
    assert args[1:4] == ["-m", "docling_baseline.cli", "dp_bench"]
    assert args[4] == str(tmp_path)
    assert captured["check"] is True
