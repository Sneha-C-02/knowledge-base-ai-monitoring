"""
Date parsing utilities for Waters Knowledge Base articles.

Supports a variety of date formats commonly found in article metadata
and visible page elements. All parsed dates are returned as timezone-aware
datetime objects.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)

# Common date formats found in Waters Knowledge Base articles
RECOGNIZED_DATE_FORMATS: list[str] = [
    "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601 with timezone
    "%Y-%m-%dT%H:%M:%SZ",        # ISO 8601 UTC
    "%Y-%m-%dT%H:%M:%S",         # ISO 8601 without timezone
    "%Y-%m-%d",                    # Simple date
    "%B %d, %Y",                   # "August 15, 2026"
    "%b %d, %Y",                   # "Aug 15, 2026"
    "%d %B %Y",                    # "15 August 2026"
    "%d %b %Y",                    # "15 Aug 2026"
    "%m/%d/%Y",                    # US format
    "%d/%m/%Y",                    # European format
    "%Y/%m/%d",                    # Asian format
]


def parse_article_date(
    raw_date_string: Optional[str],
    article_url: str = "",
) -> Optional[datetime]:
    """
    Parse a date string from an article into a timezone-aware datetime.

    Tries recognized formats first, then falls back to dateutil's
    fuzzy parser. Returns None if the date cannot be parsed.

    Args:
        raw_date_string: The raw date text extracted from the article.
        article_url: URL of the article, used for logging context.

    Returns:
        Timezone-aware datetime if parsing succeeds, None otherwise.
    """
    if not raw_date_string or not raw_date_string.strip():
        return None

    cleaned_date_string = _clean_date_string(raw_date_string)

    if not cleaned_date_string:
        return None

    # Attempt each recognized format
    for date_format in RECOGNIZED_DATE_FORMATS:
        try:
            parsed_date = datetime.strptime(cleaned_date_string, date_format)
            return _ensure_timezone_aware(parsed_date)
        except ValueError:
            continue

    # Fall back to dateutil fuzzy parsing
    try:
        parsed_date = dateutil_parser.parse(cleaned_date_string, fuzzy=True)
        return _ensure_timezone_aware(parsed_date)
    except (ValueError, OverflowError) as parse_error:
        logger.warning(
            "Could not parse date '%s' from article %s: %s",
            raw_date_string,
            article_url,
            parse_error,
        )
        return None


def _clean_date_string(raw_date_string: str) -> str:
    """Remove common non-date prefixes and normalize whitespace."""
    cleaned = raw_date_string.strip()

    # Remove common label prefixes
    date_label_patterns = [
        r"^(?:last\s+)?(?:modified|updated|published|created|date)\s*[:]\s*",
        r"^date\s*[:]\s*",
    ]
    for pattern in date_label_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned


def _ensure_timezone_aware(parsed_date: datetime) -> datetime:
    """Ensure a datetime object has timezone information (default UTC)."""
    if parsed_date.tzinfo is None:
        return parsed_date.replace(tzinfo=timezone.utc)
    return parsed_date
