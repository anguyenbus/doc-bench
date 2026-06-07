"""
CLI entry point for docling-baseline.

This module provides the command-line interface for running baseline evaluations.
"""

import json
import os
from pathlib import Path

import click

# Force CPU usage
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["DOCLING_DEVICE"] = "cpu"

from docling_baseline.runners import (
    ATOBenchRunner,
    DPBenchRunner,
    OmniDocBenchRunner,
)


def load_manifest(fixtures_dir: Path) -> dict:
    """Load manifest.json from fixtures directory."""
    manifest_path = fixtures_dir / "manifest.json"
    if not manifest_path.exists():
        raise click.ClickException(f"Manifest not found: {manifest_path}")
    with open(manifest_path) as f:
        return json.load(f)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """
    Docling Baseline - Standalone evaluation tool for Docling document parser.

    Generate baseline scores across three datasets:
    - DP-Bench: 16 PDF documents
    - OmniDocBench: 16 document images
    - ATO-Bench: 5 multi-page PDF forms (23 pages)

    All scores are saved to JSON files in the fixtures directory.
    """
    pass


@main.command()
@click.argument("fixtures_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output path for results JSON")
def dp_bench(fixtures_dir: Path, output: Path | None = None):
    """
    Evaluate DP-Bench dataset.

    Evaluates 16 PDF documents with NID, BLEU, METEOR, TEDS, MHS, and ARD metrics.
    """
    manifest = load_manifest(fixtures_dir)
    runner = DPBenchRunner(fixtures_dir, manifest)
    results = runner.evaluate()

    output_path = output or (fixtures_dir / "dp_bench_results.json")
    runner.save_results(results, output_path)


@main.command()
@click.argument("fixtures_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output path for results JSON")
def omnidocbench(fixtures_dir: Path, output: Path | None = None):
    """
    Evaluate OmniDocBench dataset.

    Evaluates 16 document images with NID, BLEU, METEOR, TEDS, MHS, and ARD metrics.
    """
    manifest = load_manifest(fixtures_dir)
    runner = OmniDocBenchRunner(fixtures_dir, manifest)
    results = runner.evaluate()

    output_path = output or (fixtures_dir / "omnidocbench_results.json")
    runner.save_results(results, output_path)


@main.command()
@click.argument("fixtures_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output path for results JSON")
def ato_bench(fixtures_dir: Path, output: Path | None = None):
    """
    Evaluate ATO-Bench dataset.

    Evaluates 5 multi-page PDF forms (23 pages total) with NED and TEDS metrics.
    """
    manifest = load_manifest(fixtures_dir)
    runner = ATOBenchRunner(fixtures_dir, manifest)
    results = runner.evaluate()

    output_path = output or (fixtures_dir / "ato_bench_results.json")
    runner.save_results(results, output_path)


@main.command()
@click.argument("fixtures_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), help="Output directory for results")
def all(fixtures_dir: Path, output_dir: Path | None = None):
    """
    Evaluate all three datasets.

    Runs DP-Bench, OmniDocBench, and ATO-Bench evaluations sequentially.
    """
    output_dir = output_dir or fixtures_dir

    click.echo("=" * 60)
    click.echo("DOCLING BASELINE EVALUATION - ALL DATASETS")
    click.echo("=" * 60)

    manifest = load_manifest(fixtures_dir)

    # DP-Bench
    click.echo("\n")
    dp_runner = DPBenchRunner(fixtures_dir, manifest)
    dp_results = dp_runner.evaluate()
    dp_runner.save_results(dp_results, output_dir / "dp_bench_results.json")

    # OmniDocBench
    click.echo("\n")
    omni_runner = OmniDocBenchRunner(fixtures_dir, manifest)
    omni_results = omni_runner.evaluate()
    omni_runner.save_results(omni_results, output_dir / "omnidocbench_results.json")

    # ATO-Bench
    click.echo("\n")
    ato_runner = ATOBenchRunner(fixtures_dir, manifest)
    ato_results = ato_runner.evaluate()
    ato_runner.save_results(ato_results, output_dir / "ato_bench_results.json")

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("SUMMARY")
    click.echo("=" * 60)
    click.echo(f"DP-Bench:      {dp_results['successful']}/{dp_results['total']} docs")
    click.echo(f"OmniDocBench:  {omni_results['successful']}/{omni_results['total']} images")
    click.echo(f"ATO-Bench:     {ato_results['successful']}/{ato_results['total']} pages")

    # Aggregate averages
    all_averages = {
        "dp_bench": dp_results.get("averages", {}),
        "omnidocbench": omni_results.get("averages", {}),
        "ato_bench": ato_results.get("averages", {}),
    }

    summary_path = output_dir / "baseline_summary.json"
    with open(summary_path, "w") as f:
        json.dump(all_averages, f, indent=2)
    click.echo(f"\nSummary saved: {summary_path}")


if __name__ == "__main__":
    main()
