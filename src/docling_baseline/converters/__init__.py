"""
Converters for transforming parser outputs to evaluation formats.

This module provides converters for transforming structured parser outputs
into formats suitable for metric evaluation (e.g., Markdown).
"""

from docling_baseline.converters.markdown import (
    elements_to_markdown,
    parser_output_to_markdown,
)

__all__ = [
    "elements_to_markdown",
    "parser_output_to_markdown",
]
