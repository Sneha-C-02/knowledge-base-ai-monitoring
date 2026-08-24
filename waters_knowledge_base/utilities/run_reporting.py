"""
Run reporting utilities for extraction summaries and failure reports.

Generates structured JSON reports after each extraction run, including
summary statistics, failed article details, and unreviewed instrument names.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ExtractionRunReport:
    """
    Accumulates extraction results and generates structured reports.

    Tracks inserted, updated, unchanged, skipped, and failed articles
    throughout an extraction run and writes summary files on completion.
    """

    def __init__(self, run_mode: str, output_directory: str):
        """
        Initialize a new extraction run report.

        Args:
            run_mode: The extraction mode (full, incremental, discover-only, etc.).
            output_directory: Path to the output directory for report files.
        """
        self.run_mode: str = run_mode
        self.output_directory: str = output_directory
        self.run_started_at: datetime = datetime.now(timezone.utc)
        self.run_completed_at: datetime | None = None

        self.discovered_article_count: int = 0
        self.successfully_inserted_count: int = 0
        self.successfully_updated_count: int = 0
        self.unchanged_article_count: int = 0
        self.skipped_article_count: int = 0
        self.failed_article_count: int = 0

        self.failed_articles: list[dict[str, Any]] = []
        self.unreviewed_instrument_names: dict[str, dict[str, Any]] = {}

    def record_inserted(self, article_number: str, article_url: str) -> None:
        """Record a successfully inserted article."""
        self.successfully_inserted_count += 1
        logger.info(
            "INSERTED article %s from %s", article_number, article_url
        )

    def record_updated(self, article_number: str, article_url: str) -> None:
        """Record a successfully updated article."""
        self.successfully_updated_count += 1
        logger.info(
            "UPDATED article %s from %s", article_number, article_url
        )

    def record_unchanged(self, article_number: str, article_url: str) -> None:
        """Record an article that was unchanged since the last run."""
        self.unchanged_article_count += 1
        logger.debug(
            "UNCHANGED article %s from %s", article_number, article_url
        )

    def record_skipped(
        self, article_url: str, reason: str, article_number: str = ""
    ) -> None:
        """Record a skipped article with the reason."""
        self.skipped_article_count += 1
        logger.warning(
            "SKIPPED article %s (%s): %s",
            article_number or "unknown",
            article_url,
            reason,
        )
        self.failed_articles.append({
            "article_url": article_url,
            "article_number": article_number,
            "failure_stage": "skipped",
            "error_type": "skipped",
            "readable_error_message": reason,
            "retry_recommended": False,
            "attempted_at": datetime.now(timezone.utc).isoformat(),
        })

    def record_failed(
        self,
        article_url: str,
        failure_stage: str,
        error_type: str,
        readable_error_message: str,
        retry_recommended: bool = False,
        article_number: str = "",
    ) -> None:
        """Record a failed article with full diagnostic information."""
        self.failed_article_count += 1
        logger.error(
            "FAILED article %s (%s) at stage '%s': %s",
            article_number or "unknown",
            article_url,
            failure_stage,
            readable_error_message,
        )
        self.failed_articles.append({
            "article_url": article_url,
            "article_number": article_number,
            "failure_stage": failure_stage,
            "error_type": error_type,
            "readable_error_message": readable_error_message,
            "retry_recommended": retry_recommended,
            "attempted_at": datetime.now(timezone.utc).isoformat(),
        })

    def record_unreviewed_instrument_name(
        self,
        original_value: str,
        cleaned_value: str,
        source_article_url: str,
    ) -> None:
        """Track an instrument name not found in the alias configuration."""
        lowercase_key = cleaned_value.lower()
        if lowercase_key in self.unreviewed_instrument_names:
            self.unreviewed_instrument_names[lowercase_key][
                "occurrence_count"
            ] += 1
        else:
            self.unreviewed_instrument_names[lowercase_key] = {
                "original_value": original_value,
                "cleaned_value": cleaned_value,
                "source_article_url": source_article_url,
                "occurrence_count": 1,
            }

    def finalize(self) -> dict[str, Any]:
        """
        Finalize the run, calculate duration, and write all report files.

        Returns:
            The summary dictionary.
        """
        self.run_completed_at = datetime.now(timezone.utc)
        duration_seconds = (
            self.run_completed_at - self.run_started_at
        ).total_seconds()

        summary = {
            "run_started_at": self.run_started_at.isoformat(),
            "run_completed_at": self.run_completed_at.isoformat(),
            "run_mode": self.run_mode,
            "discovered_article_count": self.discovered_article_count,
            "successfully_inserted_count": self.successfully_inserted_count,
            "successfully_updated_count": self.successfully_updated_count,
            "unchanged_article_count": self.unchanged_article_count,
            "skipped_article_count": self.skipped_article_count,
            "failed_article_count": self.failed_article_count,
            "unreviewed_instrument_name_count": len(
                self.unreviewed_instrument_names
            ),
            "duration_seconds": round(duration_seconds, 2),
        }

        # Ensure output directory exists
        os.makedirs(self.output_directory, exist_ok=True)

        # Write extraction summary
        summary_file_path = os.path.join(
            self.output_directory, "extraction_summary.json"
        )
        _write_json_report(summary_file_path, summary)

        # Write failed articles report
        if self.failed_articles:
            failed_file_path = os.path.join(
                self.output_directory, "failed_articles.json"
            )
            _write_json_report(failed_file_path, self.failed_articles)

        # Write unreviewed instrument names
        if self.unreviewed_instrument_names:
            unreviewed_file_path = os.path.join(
                self.output_directory, "unreviewed_instrument_names.json"
            )
            _write_json_report(
                unreviewed_file_path,
                list(self.unreviewed_instrument_names.values()),
            )

        # Log the summary
        logger.info("=" * 60)
        logger.info("EXTRACTION RUN SUMMARY")
        logger.info("=" * 60)
        logger.info("  Mode:        %s", self.run_mode)
        logger.info("  Discovered:  %d", self.discovered_article_count)
        logger.info("  Inserted:    %d", self.successfully_inserted_count)
        logger.info("  Updated:     %d", self.successfully_updated_count)
        logger.info("  Unchanged:   %d", self.unchanged_article_count)
        logger.info("  Skipped:     %d", self.skipped_article_count)
        logger.info("  Failed:      %d", self.failed_article_count)
        logger.info(
            "  Unreviewed instruments: %d",
            len(self.unreviewed_instrument_names),
        )
        logger.info("  Duration:    %.2f seconds", duration_seconds)
        logger.info("=" * 60)

        return summary


def _write_json_report(file_path: str, data: Any) -> None:
    """Write a JSON report file with readable formatting."""
    try:
        with open(file_path, "w", encoding="utf-8") as report_file:
            json.dump(data, report_file, indent=2, ensure_ascii=False)
        logger.info("Report written to %s", file_path)
    except OSError as write_error:
        logger.error(
            "Failed to write report to %s: %s", file_path, write_error
        )
