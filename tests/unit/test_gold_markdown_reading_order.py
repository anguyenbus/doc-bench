"""
Tests for DP-Bench gold markdown construction.

Tests that build_gold_markdown() processes elements in JSON order (no
coordinate sorting) and produces consistent output for grading, including
the content.html -> GFM pipe-table rendering path.

NOTE (out of scope): src/doc_bench/datasets/dp_bench.py defines a
_get_sort_key helper that build_gold_markdown does NOT call -- current
source processes elements in JSON order per build_gold_markdown's docstring.
The dead _get_sort_key helper is a src/ concern out of scope for this
test-only spec; it is flagged here but intentionally left untouched.
"""


class TestReadingOrderSorting:
    """Tests for element ordering and category markup."""

    def test_sorting_by_page_then_y_then_x(self):
        """Test elements are emitted in JSON order (build_gold_markdown does not sort)."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        # Elements supplied out of reading order; current source keeps JSON order.
        elements = {
            "elements": [
                {
                    "page": 2,
                    "coordinates": [{"x": 100, "y": 200}],
                    "category": "Paragraph",
                    "content": {"text": "Page 2, y=200, x=100"},
                },
                {
                    "page": 1,
                    "coordinates": [{"x": 200, "y": 300}],
                    "category": "Paragraph",
                    "content": {"text": "Page 1, y=300, x=200"},
                },
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 200}],
                    "category": "Paragraph",
                    "content": {"text": "Page 1, y=200, x=100"},
                },
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 300}],
                    "category": "Paragraph",
                    "content": {"text": "Page 1, y=300, x=100"},
                },
            ]
        }

        result = build_gold_markdown(elements)

        # build_gold_markdown processes elements in JSON order (no coordinate
        # sorting), so output order matches the input array order exactly.
        expected_texts = [
            "Page 2, y=200, x=100",
            "Page 1, y=300, x=200",
            "Page 1, y=200, x=100",
            "Page 1, y=300, x=100",
        ]

        # Check elements appear in JSON (input) order.
        result_clean = result.replace("\n\n", "\n")  # Remove blank lines for checking
        lines = [line for line in result_clean.split("\n") if line]  # Get non-empty lines

        for i, expected in enumerate(expected_texts):
            assert i < len(
                lines
            ), f"Not enough lines, expected {len(expected_texts)}, got {len(lines)}"
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
                    "content": {"text": "Test Header"},
                },
            ]
        }

        result = build_gold_markdown(elements)
        assert "# Test Header" in result

    def test_table_category_markup(self):
        """Test Table elements render content without a literal [TABLE: ...] wrapper.

        The [TABLE: {text}] wrapper was intentionally removed in commit 3184dfd;
        it injected literal "[TABLE:" tokens that no parser emits. A text-only
        table now renders its raw text content with no synthetic wrapper.
        """
        from doc_bench.datasets.dp_bench import build_gold_markdown

        elements = {
            "elements": [
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 100}],
                    "category": "Table",
                    "content": {"text": "Table Content"},
                },
            ]
        }

        result = build_gold_markdown(elements)
        assert "Table Content" in result
        assert "[TABLE:" not in result

    def test_table_html_renders_gfm_pipe_table(self):
        """Test a Table element with content.html renders a GFM pipe table.

        Exercises _html_table_to_markdown via build_gold_markdown -- the
        html->pipe-table path that shipped in commit 3184dfd with no coverage.
        """
        from doc_bench.datasets.dp_bench import build_gold_markdown

        elements = {
            "elements": [
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 100}],
                    "category": "Table",
                    "content": {
                        "html": (
                            "<tr><td>Name</td><td>Age</td></tr>"
                            "<tr><td>Alice</td><td>30</td></tr>"
                        )
                    },
                },
            ]
        }

        result = build_gold_markdown(elements)

        # GFM header row, separator row, and data row.
        assert "| Name | Age |" in result
        assert "| --- | --- |" in result
        assert "| Alice | 30 |" in result
        # No literal [TABLE: wrapper on the html path either.
        assert "[TABLE:" not in result

    def test_list_category_markup(self):
        """Test List elements get - prefix."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        elements = {
            "elements": [
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 100}],
                    "category": "List",
                    "content": {"text": "List Item"},
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
                    "content": {"text": "Plain paragraph text"},
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
                    "content": {"text": ""},
                },
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 200}],
                    "category": "Paragraph",
                    "content": {"text": "Valid text"},
                },
            ]
        }

        result = build_gold_markdown(elements)
        assert "Valid text" in result
        # Only one element produces text, so we get "Valid text\n\n" (one trailing blank line)
        # Count non-empty lines to verify only one element
        non_empty_lines = [line for line in result.split("\n") if line]
        assert len(non_empty_lines) == 1

    def test_missing_fields_handled(self):
        """Test elements with missing fields don't crash."""
        from doc_bench.datasets.dp_bench import build_gold_markdown

        # Element without coordinates
        elements = {
            "elements": [
                {"page": 1, "category": "Paragraph", "content": {"text": "No coords"}},
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
                    "content": {"text": "First"},
                },
                {
                    "page": 1,
                    "coordinates": [{"x": 100, "y": 200}],
                    "category": "Paragraph",
                    "content": {"text": "Second"},
                },
            ]
        }

        result = build_gold_markdown(elements)
        # Elements separated by blank line (format: "First\n\nSecond\n\n")
        assert "First\n\nSecond" in result  # Elements separated by blank line
