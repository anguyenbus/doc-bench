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

from pathlib import Path

__version__ = "0.1.0"


def get_bundled_schema_path(schema_arg: Path | None = None) -> Path:
    """
    Resolve schema path from argument, bundled fixtures, or contracts directory.

    Args:
        schema_arg: Explicit schema path from CLI argument.

    Returns:
        Path to parser_output.schema.json.

    """
    if schema_arg:
        return schema_arg

    # Try bundled fixtures first (installed package)
    try:
        from doc_bench import __file__ as pkg_file

        pkg_dir = Path(pkg_file).parent
        schema_path = pkg_dir / "fixtures" / "parser_output.schema.json"
        if schema_path.exists():
            return schema_path
    except (ImportError, AttributeError):
        pass

    # Fall back to contracts directory (local development)
    contracts_path = Path("contracts/parser_output.schema.json")
    if contracts_path.exists():
        return contracts_path

    # Try src/ contracts path (local development)
    src_contracts = Path("src/contracts/parser_output.schema.json")
    if src_contracts.exists():
        return src_contracts

    # Return default (will error if not found)
    return Path("contracts/parser_output.schema.json")
