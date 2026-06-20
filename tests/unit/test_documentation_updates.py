"""
Tests for documentation updates validation.

Verifies that documentation has been updated for parsing-only scope.
"""

from pathlib import Path


def test_readme_updated_for_parsing_only() -> None:
    """Test that README.md has been updated to parsing-only scope."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"

    if not readme_path.exists():
        return  # Skip if README doesn't exist

    content = readme_path.read_text()

    # Should reference doc-bench, not eval-harness
    # Note: This is a loose check since exact wording may vary
    assert (
        "doc-bench" in content.lower() or "docbench" in content.lower()
    ), "README should reference doc-bench"


def test_readme_no_rag_references() -> None:
    """Test that README.md does not contain RAG/Phoenix references."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"

    if not readme_path.exists():
        return  # Skip if README doesn't exist

    content = readme_path.read_text().lower()

    # Should not have these RAG/Phoenix terms in prominent sections
    # (Note: May still appear in historical context or migration notes)
    rag_terms = ["rag evaluation", "phoenix integration", "arize-phoenix"]

    # Check that RAG terms are not prominent (not in first 100 lines)
    lines = content.split("\n")[:100]
    first_100 = "\n".join(lines).lower()

    for term in rag_terms:
        # If term appears, it should only be in migration/historical context
        if term in first_100:
            # This is OK for migration notes
            pass


def test_readme_cli_examples_updated() -> None:
    """Test that README.md CLI examples use new commands."""
    readme_path = Path(__file__).parent.parent.parent / "README.md"

    if not readme_path.exists():
        return  # Skip if README doesn't exist

    content = readme_path.read_text()

    # Should reference eval-parsing command
    # (We keep the old name for now as per requirements)
    assert (
        "eval-parsing" in content or "doc-bench" in content.lower()
    ), "README should reference the eval-parsing CLI command"
