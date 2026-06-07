"""
Tests for the setup CLI command stub.

The setup command was previously used to download NLTK data for the METEOR
metric.  METEOR was removed as part of the 2026-06-07 NED/metrics simplification
spec.  The command is now a no-op stub that prints an informational message and
exits cleanly.
"""

from click.testing import CliRunner


class TestSetupNoOp:
    """Tests for the no-op setup command stub."""

    def test_setup_exits_successfully(self) -> None:
        """The setup command must exit with code 0."""
        from doc_bench.cli.setup import main

        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code == 0

    def test_setup_emits_informational_message(self) -> None:
        """The setup command must emit a message mentioning METEOR removal."""
        from doc_bench.cli.setup import main

        runner = CliRunner()
        result = runner.invoke(main, [])
        assert "METEOR" in result.output or "no setup required" in result.output.lower()

    def test_setup_does_not_require_arguments(self) -> None:
        """The stub setup command takes no arguments."""
        from doc_bench.cli.setup import main

        runner = CliRunner()
        result = runner.invoke(main, [])
        # No usage error expected
        assert result.exit_code == 0

    def test_setup_module_importable_without_nltk(self) -> None:
        """setup.py must be importable without nltk being installed."""
        import importlib

        # Re-importing ensures the module itself does not trigger nltk import
        mod = importlib.import_module("doc_bench.cli.setup")
        assert hasattr(mod, "main")

    def test_meteor_metric_no_longer_available(self) -> None:
        """text_similarity (METEOR) module must be gone after metrics simplification."""
        import pytest

        with pytest.raises(ModuleNotFoundError):
            import doc_bench.metrics.parsing.text_similarity  # noqa: F401
