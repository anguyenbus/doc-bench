"""
Adapters for document parsing libraries.

This module provides adapters to convert parser outputs to our
standardized schema format.
"""

from docling_baseline.adapters.docling import DoclingParser, parse

__all__ = ["DoclingParser", "parse"]
