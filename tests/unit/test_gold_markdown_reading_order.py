"""
Tests for DP-Bench gold markdown construction with reading-order sorting.

Tests that build_gold_markdown() sorts elements by (page, y, x) coordinates
and produces consistent output for grading.
"""

import pytest


class TestReadingOrderSorting:
    """Tests for element sorting by reading order."""

    def test_sorting_by_page_then_y_then_x(self):
        """Test elements are sorted by page, then y coordinate, then x coordinate."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        # Create elements in reverse order
        elements = {
            "elements": [
                {
                    "page": 2,
                    "coordinates": [{"x": 100, "y": 200}],
                    "category": "Paragraph",
                    "content": {"text": "Page 2, y=200, x=100"}
                },
                {
                    "page": 1,
                    "coordinates": [{"x": 200, "y": 300}],
                    "category": "Paragraph",
                    "content": {"text": "Page 1, y=300, x=200"}
                },
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 200}],
                    "category": "Paragraph",
                    "content": {"text": "Page 1, y=200, x=100"}
                },
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 300}],
                    "category": "Paragraph",
                    "content": {"text": "Page 1, y=300, x=100"}
                },
            ]
        }

        result = build_gold_markdown(elements)

        # Expected order: page 1, y=200, x=100 -> page 1, y=300, x=100 -> page 1, y=300, x=200 -> page 2, y=200, x=100
        expected_texts = [
            "Page 1, y=200, x=100",
            "Page 1, y=300, x=100",
            "Page 1, y=300, x=200",
            "Page 2, y=200, x=100"
        ]

        # Check elements appear in correct order
        result_clean = result.replace("\n\n", "\n")  # Remove blank lines for checking
        lines = [line for line in result_clean.split('\n') if line]  # Get non-empty lines

        for i, expected in enumerate(expected_texts):
            assert i < len(lines), f"Not enough lines, expected {len(expected_texts)}, got {len(lines)}"
            assert expected in lines[i], f"Line {i} should contain '{expected}', got '{lines[i]}'"

    def test_header_category_markup(self):
        """Test Header elements get # prefix."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        elements = {
            "elements": [
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 100}],
                    "category": "Header",
                    "content": {"text": "Test Header"}
                },
            ]
        }

        result = build_gold_markdown(elements)
        assert "# Test Header" in result

    def test_table_category_markup(self):
        """Test Table elements get [TABLE: ...] markup."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        elements = {
            "elements": [
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 100}],
                    "category": "Table",
                    "content": {"text": "Table Content"}
                },
            ]
        }

        result = build_gold_markdown(elements)
        assert "[TABLE: Table Content]" in result

    def test_list_category_markup(self):
        """Test List elements get - prefix."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        elements = {
            "elements": [
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 100}],
                    "category": "List",
                    "content": {"text": "List Item"}
                },
            ]
        }

        result = build_gold_markdown(elements)
        assert "- List Item" in result

    def test_plain_text_paragraph(self):
        """Test Paragraph elements have no markup."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        elements = {
            "elements": [
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 100}],
                    "category": "Paragraph",
                    "content": {"text": "Plain paragraph text"}
                },
            ]
        }

        result = build_gold_markdown(elements)
        assert "Plain paragraph text" in result
        assert "#" not in result  # No header markup
        assert "[TABLE:" not in result  # No table markup
        assert result.strip().startswith("Plain paragraph text")  # Direct text

    def test_empty_elements_skipped(self):
        """Test elements with empty text are skipped."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        elements = {
            "elements": [
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 100}],
                    "category": "Paragraph",
                    "content": {"text": ""}
                },
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 200}],
                    "category": "Paragraph",
                    "content": {"text": "Valid text"}
                },
            ]
        }

        result = build_gold_markdown(elements)
        assert "Valid text" in result
        # Only one element produces text, so we get "Valid text\n\n" (one trailing blank line)
        # Count non-empty lines to verify only one element
        non_empty_lines = [l for l in result.split('\n') if l]
        assert len(non_empty_lines) == 1

    def test_missing_fields_handled(self):
        """Test elements with missing fields don't crash."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        # Element without coordinates
        elements = {
            "elements": [
                {
                    "page": 1,
                    "category": "Paragraph",
                    "content": {"text": "No coords"}
                },
            ]
        }

        # Should handle gracefully
        result = build_gold_markdown(elements)
        assert "No coords" in result

    def test_blank_line_separation(self):
        """Test elements are separated by blank lines."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        elements = {
            "elements": [
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 100}],
                    "category": "Paragraph",
                    "content": {"text": "First"}
                },
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 200}],
                    "category": "Paragraph",
                    "content": {"text": "Second"}
                },
            ]
        }

        result = build_gold_markdown(elements)
        # Elements separated by blank line (format: "First\n\nSecond\n\n")
        assert "First\n\nSecond" in result  # Elements separated by blank line
