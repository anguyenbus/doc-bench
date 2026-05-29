"""
Evaluation harness for document parsing systems.

This package provides:
- Dataset loaders for public benchmarks (OmniDocBench, DP-Bench)
- Deterministic metrics for parsing quality
- Adapter pattern for swapping parsers
- CLI entry points for running evaluations

Typical usage:
    uv run eval-parsing --dataset dp_bench --parser stub
"""

__version__ = "0.1.0"
