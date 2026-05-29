"""Tests for document identity convention (doc_id_for helper)."""

from doc_bench.identity import doc_id_for


class TestDocumentIdentityConvention:
    """Test suite for doc_id_for() helper function."""

    def test_dp_bench_identifier_extraction(self, tmp_path):
        """Test DP-Bench identifier extraction (numeric IDs like '01030000000001')."""
        # Create a DP-Bench-like item structure
        # The loader yields (doc_id, pdf_path, gold_elements) tuples
        # But doc_id_for() should work with the raw item from reference.json
        # which is keyed by PDF filename

        # Simulate what the DP-Bench loader provides
        pdf_filename = "01030000000001.pdf"
        doc_id = pdf_filename.replace(".pdf", "")

        # Create a mock item that represents what reference.json contains
        item = {
            "elements": [
                {"category": "Paragraph", "content": {"text": "Sample"}, "page": 1}
            ]
        }

        # For DP-Bench, doc_id_for should extract from the pdf_filename
        # The loader passes the pdf_filename as part of context
        result = doc_id_for("dp_bench", (pdf_filename, item))

        assert result == "01030000000001"

    def test_dp_bench_with_various_filenames(self, tmp_path):
        """Test DP-Bench extraction with various filename patterns."""
        test_cases = [
            ("doc001.pdf", "doc001"),
            ("01030000000001.pdf", "01030000000001"),
            ("test_document.pdf", "test_document"),
            ("CAPS_DOC.pdf", "CAPS_DOC"),
        ]

        for pdf_filename, expected_doc_id in test_cases:
            item = {"elements": []}
            result = doc_id_for("dp_bench", (pdf_filename, item))
            assert result == expected_doc_id

    def test_omnidocbench_identifier_extraction(self, tmp_path):
        """Test OmniDocBench identifier extraction.

        Investigation in Task 1.2 will determine the exact field.
        This test documents the expected behavior based on investigation.
        """
        # OmniDocBench page dict structure
        page = {
            "page_info": {
                "page_no": 1,
                "height": 792,
                "width": 612,
                "image_path": "book_en_[搬书匠#375][High Performance MySQL...].png",
                "page_attribute": {
                    "language": "english",
                    "data_source": "research_report",
                },
            },
            "layout_dets": [],
            "extra": {},
        }

        # After investigation, we'll determine the stable identifier
        # For now, this test documents the expectation
        result = doc_id_for("omnidocbench", page)

        # The result should be a filesystem-safe identifier
        # After investigation: may need sanitization if using image_path
        assert isinstance(result, str)
        # Should not contain filesystem-hostile characters
        # (Investigation Task 1.2 will confirm exact behavior)

    def test_filesystem_hostile_character_handling(self, tmp_path):
        """Test handling of filesystem-hostile characters if needed.

        If native identifiers contain characters like Chinese characters,
        special chars, etc., doc_id_for() should sanitize them.
        """
        # This test will be updated based on Task 1.2 investigation
        # If sanitization is needed, it will test bidirectional mapping

        # Example with filesystem-hostile characters
        page_with_chinese = {
            "page_info": {
                "image_path": "book_en_[搬书匠#375][High Performance MySQL].png",
                "page_attribute": {"language": "english"},
            },
            "layout_dets": [],
        }

        result = doc_id_for("omnidocbench", page_with_chinese)

        # Result should be filesystem-safe
        # (Investigation will determine exact sanitization rules)
        assert isinstance(result, str)
        # Should be usable as a filename stem
        assert "/" not in result
        assert "\\" not in result
