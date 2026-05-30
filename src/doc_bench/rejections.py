"""
Rejection tracking module for file-based evaluation.

This module provides data structures and utilities for tracking and
reporting rejected predictions during file-based evaluation.
"""

import csv
from enum import Enum
from pathlib import Path


class RejectionReason(str, Enum):
    """Rejection reason codes for failed predictions."""

    MISSING_PREDICTION = "MISSING_PREDICTION"
    INVALID_JSON = "INVALID_JSON"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    EVALUATION_ERROR = "EVALUATION_ERROR"


def format_rejection_detail(reason: RejectionReason, error_message: str = "") -> str:
    """
    Format rejection detail message for CSV output.

    Args:
        reason: The rejection reason code.
        error_message: Optional error message with details.

    Returns:
        Formatted detail string for the CSV detail column.

    """
    if reason == RejectionReason.MISSING_PREDICTION:
        return ""  # No detail needed for missing files
    elif reason == RejectionReason.INVALID_JSON:
        return f"JSON parse error: {error_message}" if error_message else "Invalid JSON"
    elif reason == RejectionReason.INVALID_SCHEMA:
        return error_message  # Field path and validation message
    elif reason == RejectionReason.EVALUATION_ERROR:
        return error_message  # Exception message from metric computation
    return ""


class RejectionTracker:
    """
    Track rejected predictions and write to rejected.csv.

    Usage:
        tracker = RejectionTracker(output_path)
        tracker.record_rejection("doc1", RejectionReason.MISSING_PREDICTION, "doc1.pdf")
        tracker.record_rejection("doc2", RejectionReason.INVALID_SCHEMA, "doc2.pdf", "elements[0]: Missing field")
        tracker.close()

    The CSV file has 4 columns: doc_id, reason, source_file, detail
    """

    def __init__(self, output_path: Path):
        """
        Initialize rejection tracker.

        Args:
            output_path: Path where rejected.csv will be written.

        """
        self.output_path = output_path
        self.rejection_counts = {reason: 0 for reason in RejectionReason}
        self._file = None
        self._writer = None
        self._initialized = False

    def _ensure_initialized(self):
        """Initialize CSV file if not already done."""
        if self._initialized:
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self._file = open(self.output_path, "w", newline="", encoding="utf-8")
        fieldnames = ["doc_id", "reason", "source_file", "detail"]
        self._writer = csv.DictWriter(self._file, fieldnames=fieldnames)
        self._writer.writeheader()
        self._file.flush()
        self._initialized = True

    def record_rejection(
        self, doc_id: str, reason: RejectionReason, source_file: str, detail: str = ""
    ) -> None:
        """
        Record a rejected prediction.

        Args:
            doc_id: Document identifier.
            reason: Rejection reason code.
            source_file: Source file path (e.g., "doc1.pdf" or "doc1.json").
            detail: Optional detail message (error info).

        """
        self._ensure_initialized()

        # Format detail if not provided
        if not detail and reason != RejectionReason.MISSING_PREDICTION:
            detail = format_rejection_detail(reason)

        # Write to CSV
        self._writer.writerow(
            {
                "doc_id": doc_id,
                "reason": reason.value,
                "source_file": source_file,
                "detail": detail,
            }
        )
        self._file.flush()

        # Update count
        self.rejection_counts[reason] += 1

    def get_total_rejections(self) -> int:
        """
        Get total number of rejections tracked.

        Returns:
            Total rejection count.

        """
        return sum(self.rejection_counts.values())

    def get_rejection_counts(self) -> dict[RejectionReason, int]:
        """
        Get rejection counts by reason.

        Returns:
            Dictionary mapping RejectionReason to count.

        """
        return self.rejection_counts.copy()

    def get_rejection_counts_serializable(self) -> dict[str, int]:
        """
        Get rejection counts as JSON-serializable dict.

        Returns:
            Dictionary mapping reason string to count.

        """
        return {reason.value: count for reason, count in self.rejection_counts.items()}

    def close(self) -> None:
        """Close the CSV file."""
        if self._file is not None:
            self._file.close()
            self._file = None
            self._writer = None
            self._initialized = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
