"""
Scrapy item pipeline for processing downloaded Waters Knowledge Base articles.

Orchestrates the full processing flow: extraction, cleaning, normalization,
validation, change detection, database upsert, and relationship synchronization.
Each article is processed independently; individual failures do not stop the run.
"""

import logging
import os
from typing import Any

from scrapy import Spider
from twisted.internet import threads

from waters_knowledge_base.database.article_repository import (
    ArticleConflictError,
    check_for_article_conflicts,
    find_existing_article_by_number,
    has_article_content_changed,
    insert_article,
    update_article,
)
from waters_knowledge_base.database.connection import (
    DatabaseConnectionError,
    DatabaseConnectionManager,
)
from waters_knowledge_base.database.instrument_repository import (
    find_or_create_instrument,
    synchronize_article_instrument_links,
)
from waters_knowledge_base.extraction.article_parser import (
    extract_article_information,
)
from waters_knowledge_base.extraction.instrument_normalizer import (
    InstrumentNameNormalizer,
)
from waters_knowledge_base.items import WatersArticleItem
from waters_knowledge_base.models.article_record import ArticleRecord
from waters_knowledge_base.utilities.run_reporting import ExtractionRunReport
from waters_knowledge_base.utilities.text_helpers import truncate_for_logging

logger = logging.getLogger(__name__)


class ArticleProcessingPipeline:
    """
    Scrapy pipeline that processes each downloaded article through
    the complete extraction-to-database workflow.
    """

    def __init__(self, crawler: Any = None):
        self.crawler = crawler
        self.database_connection_manager: DatabaseConnectionManager | None = None
        self.instrument_normalizer: InstrumentNameNormalizer | None = None
        self.run_report: ExtractionRunReport | None = None
        self.dry_run: bool = False

    @classmethod
    def from_crawler(cls, crawler: Any) -> "ArticleProcessingPipeline":
        return cls(crawler)

    def open_spider(self) -> None:
        """Initialize database connection and normalizer when the spider opens."""
        spider = self.crawler.spider if self.crawler else None
        self.dry_run = getattr(spider, "dry_run", False)
        run_mode = getattr(spider, "run_mode", "full")
        output_directory = os.environ.get("OUTPUT_DIRECTORY", "output")

        self.run_report = ExtractionRunReport(
            run_mode=run_mode,
            output_directory=output_directory,
        )
        self.instrument_normalizer = InstrumentNameNormalizer()

        if not self.dry_run:
            try:
                self.database_connection_manager = DatabaseConnectionManager()
                self.database_connection_manager.test_connection()
            except DatabaseConnectionError as connection_error:
                logger.error(
                    "Database connection failed during pipeline startup: %s",
                    connection_error,
                )
                raise

    def close_spider(self) -> None:
        """Write reports and clean up when the spider closes."""
        if self.run_report:
            # Transfer unreviewed instrument names to the report
            if self.instrument_normalizer:
                for unreviewed in self.instrument_normalizer.get_unreviewed_names():
                    self.run_report.record_unreviewed_instrument_name(
                        original_value=unreviewed["original_value"],
                        cleaned_value=unreviewed["cleaned_value"],
                        source_article_url=unreviewed["source_article_url"],
                    )
            self.run_report.finalize()
            
        if self.database_connection_manager:
            self.database_connection_manager.close()

    def process_item(
        self, item: WatersArticleItem
    ) -> Any:
        """
        Process a single downloaded article through the full workflow.

        Steps:
        1. Extract article information from HTML.
        2. Normalize instrument names.
        3. Validate the article record.
        4. Compare with existing database record.
        5. Insert or update the article.
        6. Synchronize instrument relationships.

        Args:
            item: The downloaded article item.
            spider: The Scrapy spider instance.

        Returns:
            The processed item (for Scrapy pipeline chain).
        """
        response_url = item.get("response_url", "")
        html_content = item.get("html_content", "")

        def _do_processing():
            try:
                self._process_single_article(response_url, html_content)
            except Exception as processing_error:
                error_type = type(processing_error).__name__
                logger.exception(
                    "Unexpected error processing %s",
                    response_url,
                )
                if self.run_report:
                    self.run_report.record_failed(
                        article_url=response_url,
                        failure_stage="unexpected_error",
                        error_type=error_type,
                        readable_error_message=str(processing_error),
                        retry_recommended=False,
                    )
            return item

        return threads.deferToThread(_do_processing)

    def _process_single_article(
        self, response_url: str, html_content: str
    ) -> None:
        """Process a single article through extraction, validation, and storage."""
        # Step 1: Extract article information
        extraction_result = extract_article_information(html_content, response_url)

        if not extraction_result.article_number:
            if self.run_report:
                self.run_report.record_failed(
                    article_url=response_url,
                    failure_stage="extraction",
                    error_type="MissingArticleNumber",
                    readable_error_message="Could not extract article number.",
                    retry_recommended=False,
                )
            return

        # Log extraction warnings
        for warning in extraction_result.extraction_warnings:
            logger.warning(
                "Extraction warning for %s: %s",
                extraction_result.article_number,
                warning,
            )

        # Step 2: Normalize instrument names
        normalized_instruments = []
        if self.instrument_normalizer:
            normalized_instruments = self.instrument_normalizer.normalize_instrument_names(
                extraction_result.raw_instrument_names,
                source_article_url=response_url,
            )

        # Step 3: Validate the article record
        try:
            article_record = ArticleRecord(
                article_number=extraction_result.article_number,
                title=extraction_result.title,
                url=extraction_result.canonical_url,
                searchable_content=extraction_result.searchable_content,
                source_updated_at=extraction_result.source_updated_at,
                instrument_names=normalized_instruments,
            )
        except Exception as validation_error:
            if self.run_report:
                self.run_report.record_failed(
                    article_url=response_url,
                    failure_stage="validation",
                    error_type="ValidationError",
                    readable_error_message=str(validation_error),
                    retry_recommended=False,
                    article_number=extraction_result.article_number,
                )
            return

        logger.info(
            "Validated article %s: '%s'",
            article_record.article_number,
            truncate_for_logging(article_record.title, 80),
        )

        # Step 4: Dry run stops here
        if self.dry_run:
            logger.info(
                "DRY RUN: Would save article %s with %d instruments.",
                article_record.article_number,
                len(article_record.instrument_names),
            )
            if self.run_report:
                self.run_report.record_skipped(
                    article_url=response_url,
                    reason="Dry run mode — no database writes.",
                    article_number=article_record.article_number,
                )
            return

        # Step 5-6: Database operations
        self._save_article_to_database(article_record, response_url)

    def _save_article_to_database(
        self, article_record: ArticleRecord, response_url: str
    ) -> None:
        """Save or update an article and its instrument links in the database."""
        if not self.database_connection_manager:
            return

        try:
            with self.database_connection_manager.get_connection() as database_connection:
                with self.database_connection_manager.get_cursor(database_connection) as database_cursor:
                    # Check for conflicts
                    try:
                        check_for_article_conflicts(
                            database_cursor,
                            article_record.article_number,
                            article_record.url,
                        )
                    except ArticleConflictError as conflict_error:
                        if self.run_report:
                            self.run_report.record_failed(
                                article_url=response_url,
                                failure_stage="conflict_check",
                                error_type="ArticleConflictError",
                                readable_error_message=str(conflict_error),
                                retry_recommended=False,
                                article_number=article_record.article_number,
                            )
                        return

                    # Find existing article
                    existing_article = find_existing_article_by_number(
                        database_cursor, article_record.article_number
                    )

                    if existing_article is None:
                        # Insert new article
                        saved_article_id = insert_article(
                            database_cursor,
                            article_number=article_record.article_number,
                            title=article_record.title,
                            article_url=article_record.url,
                            searchable_content=article_record.searchable_content,
                            source_updated_at=article_record.source_updated_at,
                        )
                        if self.run_report:
                            self.run_report.record_inserted(
                                article_record.article_number, response_url
                            )
                    else:
                        saved_article_id = existing_article["id"]
                        content_changed = has_article_content_changed(
                            existing_article,
                            new_title=article_record.title,
                            new_url=article_record.url,
                            new_searchable_content=article_record.searchable_content,
                            new_source_updated_at=article_record.source_updated_at,
                        )

                        if content_changed:
                            update_article(
                                database_cursor,
                                article_id=saved_article_id,
                                title=article_record.title,
                                article_url=article_record.url,
                                searchable_content=article_record.searchable_content,
                                source_updated_at=article_record.source_updated_at,
                            )
                            if self.run_report:
                                self.run_report.record_updated(
                                    article_record.article_number, response_url
                                )
                        else:
                            if self.run_report:
                                self.run_report.record_unchanged(
                                    article_record.article_number, response_url
                                )

                    # Synchronize instrument links
                    desired_instrument_ids: set[int] = set()
                    for instrument_name in article_record.instrument_names:
                        saved_instrument_id = find_or_create_instrument(
                            database_cursor, instrument_name
                        )
                        desired_instrument_ids.add(saved_instrument_id)

                    synchronize_article_instrument_links(
                        database_cursor,
                        article_id=saved_article_id,
                        desired_instrument_ids=desired_instrument_ids,
                    )

        except DatabaseConnectionError as db_error:
            if self.run_report:
                self.run_report.record_failed(
                    article_url=response_url,
                    failure_stage="database_save",
                    error_type="DatabaseConnectionError",
                    readable_error_message=str(db_error),
                    retry_recommended=True,
                    article_number=article_record.article_number,
                )
        except Exception as save_error:
            error_type = type(save_error).__name__
            if self.run_report:
                self.run_report.record_failed(
                    article_url=response_url,
                    failure_stage="database_save",
                    error_type=error_type,
                    readable_error_message=str(save_error),
                    retry_recommended=False,
                    article_number=article_record.article_number,
                )
