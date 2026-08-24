#!/usr/bin/env python3
"""
Waters Knowledge Base Loader — Command-line runner.

Provides an argparse-based CLI for running article extraction in
various modes: full, incremental, discover-only, single-article,
retry-failed, and dry-run.

Usage examples:
    python run_extraction.py --mode full
    python run_extraction.py --mode incremental
    python run_extraction.py --mode discover-only
    python run_extraction.py --article-url "https://www.waters.com/..."
    python run_extraction.py --mode full --maximum-articles 10
    python run_extraction.py --mode full --maximum-articles 10 --dry-run
    python run_extraction.py --retry-failed output/failed_articles.json
    python run_extraction.py --mode incremental --log-level DEBUG
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser with all supported options."""
    parser = argparse.ArgumentParser(
        prog="run_extraction",
        description=(
            "Waters Knowledge Base Loader — Extract authorized articles "
            "and load them into a Supabase PostgreSQL database."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  Full extraction:          python run_extraction.py --mode full\n"
            "  Incremental sync:         python run_extraction.py --mode incremental\n"
            "  Discover URLs only:       python run_extraction.py --mode discover-only\n"
            "  Single article:           python run_extraction.py --article-url URL\n"
            "  10-article test:          python run_extraction.py --mode full --maximum-articles 10\n"
            "  Dry run (no DB writes):   python run_extraction.py --mode full --maximum-articles 10 --dry-run\n"
            "  Retry failed articles:    python run_extraction.py --retry-failed output/failed_articles.json\n"
            "  Debug logging:            python run_extraction.py --mode incremental --log-level DEBUG\n"
        ),
    )

    parser.add_argument(
        "--mode",
        choices=["full", "incremental", "discover-only"],
        default="full",
        help=(
            "Extraction mode. 'full' processes all discovered articles. "
            "'incremental' skips unchanged articles. "
            "'discover-only' finds article URLs without downloading. "
            "(default: full)"
        ),
    )

    parser.add_argument(
        "--article-url",
        type=str,
        default="",
        help="Process a single authorized article URL instead of crawling.",
    )

    parser.add_argument(
        "--maximum-articles",
        type=int,
        default=0,
        help=(
            "Maximum number of articles to process. "
            "Use for testing. 0 means unlimited. (default: 0)"
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help=(
            "Extract and validate articles without writing to the database. "
            "Useful for testing selectors and parsing logic."
        ),
    )

    parser.add_argument(
        "--retry-failed",
        type=str,
        default="",
        help=(
            "Path to a failed_articles.json file. Retries articles "
            "marked as retry_recommended."
        ),
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Override the LOG_LEVEL environment variable.",
    )

    return parser


def validate_environment_configuration() -> list[str]:
    """
    Validate that required environment variables are set.

    Returns a list of error messages for missing or invalid variables.
    """
    validation_errors: list[str] = []

    # DATABASE_CONNECTION_URL is required for non-dry-run modes
    database_url = os.environ.get("DATABASE_CONNECTION_URL", "")
    # (Will be validated at connection time; just warn if empty)

    # RESPECT_ROBOTS_TXT must be true
    respect_robots = os.environ.get("RESPECT_ROBOTS_TXT", "true").lower()
    if respect_robots != "true":
        validation_errors.append(
            "RESPECT_ROBOTS_TXT must be 'true'. "
            "This application refuses to run with robots.txt disabled "
            "unless an explicit authorized override is documented."
        )

    return validation_errors


def configure_logging(log_level: str, output_directory: str) -> None:
    """Configure logging to console and timestamped file."""
    os.makedirs(output_directory, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    log_file_path = os.path.join(
        output_directory, f"extraction_{timestamp}.log"
    )

    log_format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    console_handler.setFormatter(
        logging.Formatter(log_format, datefmt=date_format)
    )
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(log_format, datefmt=date_format)
    )
    root_logger.addHandler(file_handler)

    logging.info("Log file: %s", log_file_path)


def run_scrapy_crawl(
    run_mode: str,
    maximum_articles: int,
    single_article_url: str,
    dry_run: bool,
    discover_only: bool,
    retry_failed_file: str,
) -> None:
    """
    Run the Scrapy crawler with the specified configuration.

    Args:
        run_mode: Extraction mode (full, incremental, discover-only).
        maximum_articles: Maximum articles to process.
        single_article_url: Single article URL to process.
        dry_run: Whether to skip database writes.
        discover_only: Whether to only discover URLs.
        retry_failed_file: Path to failed articles JSON for retry.
    """
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    settings = get_project_settings()

    # Override log level if set by CLI
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    settings.set("LOG_LEVEL", log_level)

    # Disable Scrapy's built-in log handler since we configured our own
    settings.set("LOG_ENABLED", False)

    crawler_process = CrawlerProcess(settings)

    spider_kwargs = {
        "run_mode": run_mode,
        "maximum_articles": maximum_articles,
        "single_article_url": single_article_url,
        "dry_run": dry_run,
        "discover_only": discover_only,
        "retry_failed_file": retry_failed_file,
    }

    crawler_process.crawl(
        "waters_articles",
        **spider_kwargs,
    )

    logging.info("Starting Scrapy crawl (mode=%s)...", run_mode)
    crawler_process.start()
    logging.info("Scrapy crawl completed.")


def main() -> None:
    """Main entry point for the Waters Knowledge Base Loader CLI."""
    # Load environment variables
    load_dotenv()

    # Parse command-line arguments
    parser = create_argument_parser()
    parsed_arguments = parser.parse_args()

    # Determine effective settings
    run_mode = parsed_arguments.mode
    log_level = parsed_arguments.log_level or os.environ.get("LOG_LEVEL", "INFO")
    output_directory = os.environ.get("OUTPUT_DIRECTORY", "output")
    discover_only = run_mode == "discover-only"

    # Set LOG_LEVEL in environment for Scrapy settings to pick up
    os.environ["LOG_LEVEL"] = log_level

    # Configure logging
    configure_logging(log_level, output_directory)

    logging.info("=" * 60)
    logging.info("Waters Knowledge Base Loader")
    logging.info("=" * 60)
    logging.info("Mode:             %s", run_mode)
    logging.info("Maximum articles: %s",
                 parsed_arguments.maximum_articles or "unlimited")
    logging.info("Dry run:          %s", parsed_arguments.dry_run)
    logging.info("Log level:        %s", log_level)

    if parsed_arguments.article_url:
        logging.info("Single URL:       %s", parsed_arguments.article_url)
    if parsed_arguments.retry_failed:
        logging.info("Retry file:       %s", parsed_arguments.retry_failed)

    # Validate environment configuration
    config_errors = validate_environment_configuration()
    if config_errors:
        for error_message in config_errors:
            logging.error("Configuration error: %s", error_message)
        sys.exit(1)

    # Validate database URL is present for non-dry-run, non-discover-only modes
    if not parsed_arguments.dry_run and not discover_only:
        database_url = os.environ.get("DATABASE_CONNECTION_URL", "")
        if not database_url:
            logging.error(
                "DATABASE_CONNECTION_URL is not set. "
                "Set it in your .env file or use --dry-run mode."
            )
            sys.exit(1)

    # Run the crawl
    try:
        run_scrapy_crawl(
            run_mode=run_mode,
            maximum_articles=parsed_arguments.maximum_articles,
            single_article_url=parsed_arguments.article_url,
            dry_run=parsed_arguments.dry_run,
            discover_only=discover_only,
            retry_failed_file=parsed_arguments.retry_failed,
        )
    except KeyboardInterrupt:
        logging.warning("Extraction interrupted by user.")
        sys.exit(130)
    except Exception as fatal_error:
        logging.critical("Fatal error: %s", fatal_error, exc_info=True)
        sys.exit(1)

    logging.info("Extraction run complete.")


if __name__ == "__main__":
    main()
