"""CLI commands for doc-bench."""

import click


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """doc-bench: Document parsing evaluation framework."""
    pass


# Import subcommands
from doc_bench.cli.dump_dataset import main as dump_dataset

main.add_command(dump_dataset, name="dump-dataset")
