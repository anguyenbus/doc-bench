"""
setup CLI command stub.

This module previously provided the CLI for downloading required NLTK data
for METEOR metric computation.  The METEOR metric was removed as part of the
2026-06-07 NED/metrics simplification spec; doc-bench now uses only NED
(Normalized Edit Distance) for text scoring, which requires no runtime data
downloads.

The command is retained as a no-op stub so that existing scripts that invoke
``doc-bench-setup`` do not break.
"""

import click


@click.command()
def main() -> None:
    """
    No-op setup command (METEOR metric removed).

    This command previously downloaded NLTK data for the METEOR text similarity
    metric.  METEOR was removed as part of the 2026-06-07 NED/metrics
    simplification spec.  No setup is required for the current metric suite
    (NED + TEDS).

    Example:
        doc-bench-setup

    """
    click.echo(
        "doc-bench-setup: no setup required. "
        "METEOR metric was removed; NED + TEDS require no runtime data downloads."
    )


if __name__ == "__main__":
    main()
