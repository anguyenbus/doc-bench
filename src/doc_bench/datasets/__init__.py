"""
Dataset loaders for public benchmarks.

This module provides loaders for:
- OmniDocBench: Document layout parsing benchmark
- DP-Bench: Document parsing benchmark

All loaders use iterator pattern for memory efficiency.
"""

from doc_bench.datasets.dp_bench import load_dp_bench
from doc_bench.datasets.omnidocbench import load_omnidocbench

__all__ = [
    "load_omnidocbench",
    "load_dp_bench",
]
