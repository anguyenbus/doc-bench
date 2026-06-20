"""
Evaluation runners for different datasets.

This module provides dataset-specific evaluation runners that:
1. Load fixtures (PDFs/images + ground truth)
2. Generate Docling predictions
3. Calculate metrics
4. Aggregate results into JSON output
"""

from docling_baseline.runners.base import BaseRunner, safe_float
from docling_baseline.runners.dp_bench import DPBenchRunner
from docling_baseline.runners.omnidocbench import OmniDocBenchRunner
from docling_baseline.runners.ato_bench import ATOBenchRunner

__all__ = [
    "BaseRunner",
    "safe_float",
    "DPBenchRunner",
    "OmniDocBenchRunner",
    "ATOBenchRunner",
]
