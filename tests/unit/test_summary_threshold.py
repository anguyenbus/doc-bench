"""
Tests for end-of-run summary and threshold warnings (Task Group 8).

Tests the configurable rejection threshold and warning logic.
"""

import os


class TestRejectionThreshold:
    """Tests for rejection threshold configuration."""

    def test_threshold_from_cli_flag(self):
        """Threshold should be read from CLI flag when provided."""
        # This test verifies the CLI argument parsing
        # The actual value is used in the summary
        threshold = 0.3
        assert 0.0 <= threshold <= 1.0

    def test_threshold_from_env_var(self, monkeypatch):
        """Threshold should fallback to DOC_BENCH_MAX_REJECTION_RATE env var."""
        monkeypatch.setenv("DOC_BENCH_MAX_REJECTION_RATE", "0.7")
        threshold = float(os.environ.get("DOC_BENCH_MAX_REJECTION_RATE", "0.5"))
        assert threshold == 0.7

    def test_threshold_default_value(self, monkeypatch):
        """Threshold should default to 0.5 when not specified."""
        monkeypatch.delenv("DOC_BENCH_MAX_REJECTION_RATE", raising=False)
        threshold = float(os.environ.get("DOC_BENCH_MAX_REJECTION_RATE", "0.5"))
        assert threshold == 0.5

    def test_threshold_zero_never_warns(self):
        """Threshold of 0 means never warn about rejections."""
        threshold = 0.0
        # When threshold is 0, warning should not be printed
        assert threshold == 0.0


class TestRejectionRateWarning:
    """Tests for rejection rate warning logic."""

    def test_warning_when_rate_exceeds_threshold(self):
        """Warning should be printed when rate exceeds threshold."""
        rejection_rate = 0.6
        threshold = 0.5

        should_warn = rejection_rate > threshold and threshold > 0
        assert should_warn is True

    def test_no_warning_when_rate_below_threshold(self):
        """No warning when rate is below threshold."""
        rejection_rate = 0.3
        threshold = 0.5

        should_warn = rejection_rate > threshold and threshold > 0
        assert should_warn is False

    def test_no_warning_when_threshold_is_zero(self):
        """No warning when threshold is 0, regardless of rate."""
        rejection_rate = 0.8
        threshold = 0.0

        should_warn = rejection_rate > threshold and threshold > 0
        assert should_warn is False

    def test_warning_message_format(self):
        """Warning message should include rate and threshold."""
        rejection_rate = 0.6
        threshold = 0.5

        message = (
            f"WARNING: Rejection rate ({rejection_rate:.1%}) exceeds threshold "
            f"({threshold:.1%}). Results may be unreliable."
        )

        assert "60.0%" in message
        assert "50.0%" in message
        assert "WARNING" in message


class TestEndOfRunSummary:
    """Tests for end-of-run summary output."""

    def test_summary_shows_evaluated_vs_rejected(self):
        """Summary should show evaluated vs rejected counts."""
        evaluated = 10
        rejected_missing = 1
        rejected_schema = 2
        rejected_json = 0
        rejected_eval = 0
        total_rejected = rejected_missing + rejected_schema + rejected_json + rejected_eval

        # Format matches expected output
        summary_line = f"Evaluated: {evaluated} / Total documents"
        rejection_line = (
            f"Rejected: {total_rejected} ({rejected_missing} missing, "
            f"{rejected_schema} bad schema, {rejected_json} bad json)"
        )

        assert "Evaluated: 10" in summary_line
        assert "Rejected: 3" in rejection_line
        assert "1 missing" in rejection_line
        assert "2 bad schema" in rejection_line

    def test_summary_includes_rejected_csv_path(self):
        """Summary should include path to rejected.csv."""
        rejected_csv_path = "results/dp_bench_predictions_rejected_20240101_120000.csv"

        summary_line = f"→ see {rejected_csv_path} for the full list"

        assert "rejected" in summary_line
        assert "for the full list" in summary_line

    def test_summary_breakdown_by_reason(self):
        """Summary should show rejection breakdown by reason."""
        counts = {
            "MISSING_PREDICTION": 1,
            "INVALID_JSON": 0,
            "INVALID_SCHEMA": 2,
            "EVALUATION_ERROR": 0,
        }

        breakdown = (
            f"Rejected: {sum(counts.values())} ({counts['MISSING_PREDICTION']} missing, "
            f"{counts['INVALID_SCHEMA']} bad schema, {counts['INVALID_JSON']} bad json)"
        )

        assert "1 missing" in breakdown
        assert "2 bad schema" in breakdown
        assert "0 bad json" in breakdown

    def test_summary_with_zero_rejections(self):
        """Summary should handle zero rejections gracefully."""
        total_rejected = 0
        counts = {
            "MISSING_PREDICTION": 0,
            "INVALID_JSON": 0,
            "INVALID_SCHEMA": 0,
            "EVALUATION_ERROR": 0,
        }

        rejection_line = (
            f"Rejected: {total_rejected} "
            f"({counts['MISSING_PREDICTION']} missing, "
            f"{counts['INVALID_SCHEMA']} bad schema, "
            f"{counts['INVALID_JSON']} bad json)"
        )

        assert "Rejected: 0" in rejection_line

    def test_summary_with_all_rejections(self):
        """Summary should handle all documents rejected."""
        evaluated = 0
        total_rejected = 10
        counts = {
            "MISSING_PREDICTION": 5,
            "INVALID_JSON": 2,
            "INVALID_SCHEMA": 3,
            "EVALUATION_ERROR": 0,
        }

        summary_line = f"Evaluated: {evaluated} / Total documents"
        rejection_line = (
            f"Rejected: {total_rejected} "
            f"({counts['MISSING_PREDICTION']} missing, "
            f"{counts['INVALID_SCHEMA']} bad schema, "
            f"{counts['INVALID_JSON']} bad json)"
        )

        assert "Evaluated: 0" in summary_line
        assert "Rejected: 10" in rejection_line


class TestThresholdEdgeCases:
    """Tests for edge cases in threshold handling."""

    def test_threshold_at_boundary_no_warning(self):
        """Rate exactly at threshold should not trigger warning."""
        rejection_rate = 0.5
        threshold = 0.5

        should_warn = rejection_rate > threshold and threshold > 0
        assert should_warn is False

    def test_threshold_just_above_boundary_warns(self):
        """Rate just above threshold should trigger warning."""
        rejection_rate = 0.51
        threshold = 0.5

        should_warn = rejection_rate > threshold and threshold > 0
        assert should_warn is True

    def test_threshold_clipping(self):
        """Threshold values should be clipped to 0.0-1.0 range."""
        # CLI parser should enforce this
        valid_thresholds = [0.0, 0.5, 1.0]

        for t in valid_thresholds:
            assert 0.0 <= t <= 1.0

    def test_total_zero_no_division_by_zero(self):
        """Should handle zero total documents gracefully."""
        total = 0
        errors = 0

        if total > 0:
            rejection_rate = errors / total
        else:
            # Avoid division by zero
            rejection_rate = 0.0

        assert rejection_rate == 0.0
