"""
Tests for file-based evaluation documentation (Task Group 11).

Tests the completeness and accuracy of docs/file-based-evaluation.md.
"""

import re
from pathlib import Path

import pytest


class TestDocumentationExists:
    """Tests that file-based evaluation documentation exists."""

    def test_file_based_evaluation_docs_exist(self):
        """docs/file-based-evaluation.md should exist."""
        doc_path = Path("docs/file-based-evaluation.md")
        assert doc_path.exists()

    def test_document_identity_docs_exist(self):
        """docs/document-identity.md should exist."""
        doc_path = Path("docs/document-identity.md")
        assert doc_path.exists()


class TestDocumentationContent:
    """Tests for documentation content completeness."""

    @pytest.fixture
    def doc_content(self):
        """Load file-based-evaluation.md content."""
        doc_path = Path("docs/file-based-evaluation.md")
        with open(doc_path) as f:
            return f.read()

    def test_quick_start_section(self, doc_content):
        """Should include Quick Start section."""
        assert "Quick Start" in doc_content or "## Quick Start" in doc_content

    def test_dump_dataset_command(self, doc_content):
        """Should document dump-dataset command."""
        assert "dump-dataset" in doc_content
        assert "--dataset" in doc_content
        assert "--output" in doc_content

    def test_predictions_flag(self, doc_content):
        """Should document --predictions flag."""
        assert "--predictions" in doc_content
        assert "predictions" in doc_content.lower()

    def test_rejection_reasons(self, doc_content):
        """Should document rejection reason codes."""
        expected_reasons = [
            "MISSING_PREDICTION",
            "INVALID_JSON",
            "INVALID_SCHEMA",
            "EVALUATION_ERROR"
        ]
        for reason in expected_reasons:
            assert reason in doc_content

    def test_rejected_csv_format(self, doc_content):
        """Should document rejected.csv format."""
        assert "rejected.csv" in doc_content
        assert "doc_id" in doc_content
        assert "reason" in doc_content
        assert "source_file" in doc_content
        assert "detail" in doc_content

    def test_threshold_documentation(self, doc_content):
        """Should document rejection threshold."""
        assert "threshold" in doc_content.lower()
        assert "max-rejection-rate" in doc_content or "max_rejection_rate" in doc_content

    def test_scores_json_fields(self, doc_content):
        """Should document scores.json fields."""
        assert "evaluated_samples" in doc_content
        assert "rejected_samples" in doc_content

    def test_document_identity_reference(self, doc_content):
        """Should reference document-identity.md."""
        assert "document-identity.md" in doc_content or "document identity" in doc_content.lower()

    def test_equivalence_verification(self, doc_content):
        """Should document equivalence verification."""
        assert "verify_equivalence" in doc_content or "equivalence" in doc_content.lower()

    def test_troubleshooting_section(self, doc_content):
        """Should include troubleshooting section."""
        assert "Troubleshooting" in doc_content or "## Troubleshooting" in doc_content

    def test_examples_section(self, doc_content):
        """Should include examples section."""
        assert "Examples" in doc_content or "## Examples" in doc_content


class TestDocumentationAccuracy:
    """Tests for documentation accuracy against implementation."""

    def test_cli_flags_match_implementation(self):
        """CLI flags in docs should match implementation."""
        doc_path = Path("docs/file-based-evaluation.md")
        with open(doc_path) as f:
            content = f.read()

        # These flags should be documented
        expected_flags = ["--dataset", "--predictions", "--max-rejection-rate", "--output-dir", "--limit"]
        for flag in expected_flags:
            assert flag in content, f"CLI flag {flag} not documented"

    def test_rejection_reasons_match_implementation(self):
        """Rejection reasons should match RejectionReason enum."""
        from doc_bench.rejections import RejectionReason

        doc_path = Path("docs/file-based-evaluation.md")
        with open(doc_path) as f:
            content = f.read()

        for reason in RejectionReason:
            assert reason.value in content, f"Rejection reason {reason.value} not documented"

    def test_schema_reference(self):
        """Should reference the correct schema file."""
        doc_path = Path("docs/file-based-evaluation.md")
        with open(doc_path) as f:
            content = f.read()

        assert "parser_output.schema.json" in content
        assert "results_v1.schema.json" in content


class TestDocumentationReadability:
    """Tests for documentation readability and structure."""

    @pytest.fixture
    def doc_content(self):
        """Load file-based-evaluation.md content."""
        doc_path = Path("docs/file-based-evaluation.md")
        with open(doc_path) as f:
            return f.read()

    def test_heading_hierarchy(self, doc_content):
        """Should have proper heading hierarchy."""
        # Should have level 1 heading
        assert "# " in doc_content
        # Should have level 2 headings
        assert "## " in doc_content

    def test_code_blocks(self, doc_content):
        """Should include code examples."""
        assert "```bash" in doc_content or "```" in doc_content

    def test_json_examples(self, doc_content):
        """Should include JSON format examples."""
        assert "```json" in doc_content

    def test_tables(self, doc_content):
        """Should include tables for structured information."""
        # Tables in markdown use | characters
        assert "|" in doc_content

    def test_not_emoji(self, doc_content):
        """Should not contain emojis (per project standards)."""
        # Check for common emoji patterns
        emoji_patterns = [r"[\U0001F600-\U0001F64F]", r"[\U0001F300-\U0001F5FF]", r"[\U0001F680-\U0001F6FF]"]
        for pattern in emoji_patterns:
            matches = re.findall(pattern, doc_content)
            assert len(matches) == 0, f"Found emojis in documentation: {matches}"
