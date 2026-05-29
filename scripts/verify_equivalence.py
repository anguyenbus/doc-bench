#!/usr/bin/env python3
"""
Equivalence verification script for file-based evaluation.

This script verifies that running the same parser via both modes (--parser and
--predictions) produces identical metrics. This validates that the file-based
evaluation mode is equivalent to the in-process parser mode.

Usage:
    python scripts/verify_equivalence.py <parser_mode_scores.json> <predictions_mode_scores.json>

Exit codes:
    0: Metrics are equivalent
    1: Metrics differ
    2: Error in execution
"""

import json
import math
import sys
from pathlib import Path


def load_scores(scores_path: Path) -> dict:
    """
    Load scores.json file.

    Args:
        scores_path: Path to scores.json file.

    Returns:
        Parsed scores dictionary.

    Raises:
        FileNotFoundError: If scores file doesn't exist.
        ValueError: If scores file contains invalid JSON.

    """
    if not scores_path.exists():
        raise FileNotFoundError(f"Scores file not found: {scores_path}")

    try:
        with open(scores_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in scores file: {e}") from e


def compare_metrics(parser_metrics: dict, predictions_metrics: dict, tolerance: float = 1e-4) -> list[str]:
    """
    Compare metrics from two runs.

    Args:
        parser_metrics: Metrics dictionary from parser mode.
        predictions_metrics: Metrics dictionary from predictions mode.
        tolerance: Tolerance for floating-point comparison.

    Returns:
        List of error messages describing divergences.

    """
    errors = []

    # Get metric keys (exclude non-metric fields)
    metric_fields = {"nid", "nid_s", "teds", "teds_s", "mhs", "mhs_s", "ard", "bleu", "meteor"}

    for key in metric_fields:
        if key in parser_metrics and key in predictions_metrics:
            parser_val = parser_metrics[key]
            pred_val = predictions_metrics[key]

            # Handle None values
            if parser_val is None and pred_val is None:
                continue
            if parser_val is None or pred_val is None:
                errors.append(f"{key}: parser={parser_val}, predictions={pred_val}")
                continue

            # Compare floats with tolerance
            if not math.isclose(parser_val, pred_val, rel_tol=tolerance, abs_tol=tolerance):
                errors.append(f"{key}: parser={parser_val}, predictions={pred_val}")

    return errors


def verify_equivalence(parser_scores_path: Path, predictions_scores_path: Path) -> int:
    """
    Verify equivalence between parser mode and predictions mode scores.

    Args:
        parser_scores_path: Path to parser mode scores.json.
        predictions_scores_path: Path to predictions mode scores.json.

    Returns:
        Exit code (0 for success, 1 for divergence, 2 for error).

    """
    try:
        # Load both scores files
        parser_scores = load_scores(parser_scores_path)
        predictions_scores = load_scores(predictions_scores_path)

        # Extract metrics_avg
        parser_metrics = parser_scores.get("metrics_avg", {})
        predictions_metrics = predictions_scores.get("metrics_avg", {})

        # Compare metrics
        errors = compare_metrics(parser_metrics, predictions_metrics)

        if errors:
            print("METRIC DIVERGENCE DETECTED:")
            for error in errors:
                print(f"  - {error}")
            return 1
        else:
            print("METRICS ARE EQUIVALENT")
            return 0

    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        return 2
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        return 2


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python scripts/verify_equivalence.py <parser_scores.json> <predictions_scores.json>")
        print("Verifies that parser mode and predictions mode produce identical metrics.")
        return 2

    parser_scores_path = Path(sys.argv[1])
    predictions_scores_path = Path(sys.argv[2])

    return verify_equivalence(parser_scores_path, predictions_scores_path)


if __name__ == "__main__":
    sys.exit(main())
