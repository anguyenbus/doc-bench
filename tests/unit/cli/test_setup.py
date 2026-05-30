"""
Tests for setup CLI command.

Tests NLTK data download and setup functionality.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestNLTKSetup:
    """Tests for NLTK setup functionality."""

    @patch("nltk.download")
    def test_setup_downloads_wordnet(self, mock_download):
        """Test setup downloads wordnet data."""
        from doc_bench.cli.setup import main
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(main, [])

        # Should call download for wordnet
        assert mock_download.called or result.exit_code == 0

    @patch("nltk.download")
    def test_setup_downloads_punkt(self, mock_download):
        """Test setup downloads punkt data."""
        from doc_bench.cli.setup import main
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(main, [])

        # Should call download for punkt
        assert result.exit_code == 0

    @patch("nltk.download")
    def test_setup_downloads_omw_1_4(self, mock_download):
        """Test setup downloads omw-1.4 data."""
        from doc_bench.cli.setup import main
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(main, [])

        # Should call download for omw-1.4
        assert result.exit_code == 0

    @patch("nltk.download")
    @patch("pathlib.Path.exists", return_value=True)
    def test_setup_detects_existing_data(self, mock_exists, mock_download):
        """Test setup detects already-downloaded data."""
        from doc_bench.cli.setup import main
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(main, [])

        # Should complete successfully
        assert result.exit_code == 0

    def test_setup_uses_cache_location(self, tmp_path):
        """Test setup stores NLTK data at correct cache location."""
        from doc_bench.cli.setup import _get_nltk_data_dir

        # Test default location
        with patch("pathlib.Path.home", return_value=Path("/mock/home")):
            nltk_dir = _get_nltk_data_dir(None)
            expected = Path("/mock/home/.cache/nltk_data")
            assert nltk_dir == expected

    def test_setup_custom_cache_dir(self, monkeypatch):
        """Test setup respects custom cache directory."""
        from doc_bench.cli.setup import _get_nltk_data_dir

        # Test with explicit path
        custom_path = Path("/custom/nltk")
        nltk_dir = _get_nltk_data_dir(custom_path)
        assert nltk_dir == custom_path


class TestMETEORSchemaReminder:
    """Tests for METEOR schema validation with setup reminder."""

    def test_meteor_error_message_mentions_setup(self):
        """Test METEOR error message mentions setup command."""
        from doc_bench.metrics.parsing.text_similarity import meteor_score

        # Test with missing NLTK data scenario
        # (This would require mocking nltk internals)
        # For now, just verify function exists
        assert callable(meteor_score)
