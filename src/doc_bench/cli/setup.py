"""
setup CLI command for NLTK data download.

This module provides the CLI for downloading required NLTK data
for METEOR metric computation.
"""

from pathlib import Path

import click
import nltk


def _get_nltk_data_dir(explicit_dir: Path | None) -> Path:
    """
    Get NLTK data directory.

    Args:
        explicit_dir: Explicit directory path override.

    Returns:
        Path to NLTK data directory.

    """
    if explicit_dir:
        return explicit_dir

    # Use ~/.cache/nltk_data as standard location
    return Path.home() / ".cache" / "nltk_data"


@click.command()
@click.option(
    "--nltk-data-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="NLTK data directory (default: ~/.cache/nltk_data)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-download even if data already exists",
)
def main(nltk_data_dir: Path | None, force: bool) -> None:
    """
    Download required NLTK data for METEOR metric.

    Downloads wordnet, punkt, and omw-1.4 corpora to ~/.cache/nltk_data.
    Required for METEOR text similarity metric.

    Example:
        doc-bench-setup

    """
    # Get NLTK data directory
    data_dir = _get_nltk_data_dir(nltk_data_dir)

    # Create directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"NLTK data directory: {data_dir}")

    # Required NLTK data packages
    required_packages = ["wordnet", "punkt", "omw-1.4"]

    for package in required_packages:
        # Check if already downloaded
        package_path = data_dir / "corpora" / package
        if package_path.exists() and not force:
            click.echo(f"  {package}: already downloaded (use --force to re-download)")
            continue

        # Download package
        click.echo(f"  Downloading {package}...")
        try:
            nltk.download(package, download_dir=str(data_dir))
            click.echo(f"  {package}: downloaded")
        except Exception as e:
            click.echo(f"  ERROR: Failed to download {package}: {e}")
            raise click.Abort()

    click.echo("\nNLTK data setup complete!")


if __name__ == "__main__":
    main()
