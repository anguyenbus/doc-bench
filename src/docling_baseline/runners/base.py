"""
Base evaluation runner with common utilities.

This module provides the BaseRunner class with shared functionality
for all dataset-specific runners.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from docling_baseline.adapters import parse as docling_parse
from docling_baseline.converters import parser_output_to_markdown
from docling_baseline.metrics import (
    ned_score,
    teds_score,
    teds_s_score,
)


def safe_float(x: float | None) -> float:
    """Convert to float, returning 0.0 for None values."""
    return round(x, 4) if x is not None else 0.0


class BaseRunner(ABC):
    """
    Abstract base class for dataset evaluation runners.

    Each runner implements dataset-specific logic for:
    - Loading ground truth data
    - Generating predictions
    - Calculating metrics
    - Aggregating results
    """

    def __init__(self, fixtures_dir: Path, manifest: dict[str, Any]):
        """Initialize runner with fixtures directory and manifest."""
        self.fixtures_dir = fixtures_dir
        self.manifest = manifest
        self.results: list[dict[str, Any]] = []

    @abstractmethod
    def get_dataset_name(self) -> str:
        """Return the dataset name for this runner."""
        pass

    @abstractmethod
    def evaluate(self) -> dict[str, Any]:
        """
        Run evaluation and return results dict.

        Returns:
            Dict with 'total', 'successful', 'errors', 'averages', 'results' keys.

        """
        pass

    def calculate_metrics(
        self, gold_text: str, pred_markdown: str
    ) -> dict[str, float]:
        """
        Calculate all metrics for a single document.

        Args:
            gold_text: Ground truth text/markdown.
            pred_markdown: Predicted markdown from Docling.

        Returns:
            Dict with all metric scores.

        """
        if not gold_text or not pred_markdown:
            return {
                "ned": 0.0,
                "teds": 0.0,
                "teds_s": 0.0,
            }

        ned = ned_score(gold_text, pred_markdown)
        teds = teds_score(gold_text, pred_markdown)
        teds_s = teds_s_score(gold_text, pred_markdown)

        return {
            "ned": safe_float(ned),
            "teds": safe_float(teds),
            "teds_s": safe_float(teds_s),
        }

    def compute_averages(self, metrics_list: list[dict[str, float]]) -> dict[str, float]:
        """
        Compute average scores across all results.

        Args:
            metrics_list: List of metric dicts from calculate_metrics().

        Returns:
            Dict with average scores for each metric.

        """
        if not metrics_list:
            return {}

        metric_names = ["ned", "teds", "teds_s"]
        averages = {}

        for metric in metric_names:
            values = [r.get(metric, 0.0) for r in metrics_list]
            avg = sum(values) / len(values) if values else 0.0
            averages[metric] = round(avg, 4)

        return averages

    def generate_prediction(self, file_path: Path) -> dict[str, Any] | None:
        """
        Generate Docling prediction for a file.

        Args:
            file_path: Path to PDF or image file.

        Returns:
            Parser output dict, or None if parsing fails.

        """
        try:
            return docling_parse(file_path)
        except Exception as e:
            print(f"  ERROR: Failed to parse {file_path.name}: {e}")
            return None

    def prediction_to_markdown(self, prediction: dict[str, Any]) -> str:
        """
        Convert prediction to markdown for metric evaluation.

        Args:
            prediction: Parser output dict.

        Returns:
            Markdown string.

        """
        return parser_output_to_markdown(prediction)

    def save_results(self, results: dict[str, Any], output_path: Path) -> None:
        """
        Save results to JSON file.

        Args:
            results: Results dict from evaluate().
            output_path: Path to save results.

        """
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Saved: {output_path}")
