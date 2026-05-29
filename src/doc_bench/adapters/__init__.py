"""
Adapters for parsers.

The adapter pattern allows swapping between stub implementations and real parsers
while maintaining schema validation.
"""

from doc_bench.adapters.schema_validator import (
    SchemaValidationError,
    validate,
)

__all__ = ["SchemaValidationError", "validate"]
