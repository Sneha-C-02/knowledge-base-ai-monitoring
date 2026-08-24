"""
Content hashing for deterministic change detection.

Generates a stable SHA-256 hash from article fields so that unchanged
articles can be skipped during incremental synchronization.
"""

import hashlib
from datetime import datetime
from typing import Optional


def compute_article_content_hash(
    article_number: str,
    title: str,
    url: str,
    searchable_content: str,
    instrument_names: list[str],
    source_updated_at: Optional[datetime] = None,
) -> str:
    """
    Compute a deterministic SHA-256 hash from stable article values.

    The hash is built from a normalized concatenation of all fields that
    affect whether an article should be updated in the database. Instrument
    names are sorted case-insensitively to ensure consistent ordering.

    Args:
        article_number: Normalized article identifier (e.g., WKB12345).
        title: Cleaned article title.
        url: Canonical article URL.
        searchable_content: Cleaned main article text.
        instrument_names: Sorted list of canonical instrument names.
        source_updated_at: Timezone-aware update timestamp, or None.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    hash_input_parts: list[str] = [
        f"article_number={article_number.strip().upper()}",
        f"title={title.strip()}",
        f"url={url.strip()}",
        f"searchable_content={searchable_content.strip()}",
        f"instrument_names={','.join(sorted(instrument_names, key=str.lower))}",
    ]

    if source_updated_at is not None:
        formatted_date = source_updated_at.isoformat()
        hash_input_parts.append(f"source_updated_at={formatted_date}")
    else:
        hash_input_parts.append("source_updated_at=None")

    combined_hash_input = "\n".join(hash_input_parts)
    content_hash = hashlib.sha256(combined_hash_input.encode("utf-8")).hexdigest()

    return content_hash
