"""
Pydantic data model for a validated Waters Knowledge Base article record.

This module defines the ArticleRecord model that enforces data quality
rules on every extracted article before it reaches the database.
"""

import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator, model_validator


# Configurable pattern for Waters Knowledge Base article identifiers.
# Matches patterns like "WKB1234", "WAT038847", "205001171", etc.
ARTICLE_NUMBER_PATTERN: re.Pattern = re.compile(
    r"^(?:WKB|WAT)?\d{3,10}$", re.IGNORECASE
)


class ArticleRecord(BaseModel):
    """
    Validated record representing one Waters Knowledge Base article.

    All fields are cleaned and validated before the record can be used.
    The content_hash is computed from stable article values to enable
    efficient incremental synchronization.
    """

    article_number: str
    title: str
    url: str
    searchable_content: str
    source_updated_at: Optional[datetime] = None
    instrument_names: list[str] = []
    content_hash: str = ""

    @field_validator("article_number")
    @classmethod
    def validate_article_number(cls, article_number: str) -> str:
        """Ensure the article number is non-empty and matches the WKB pattern."""
        cleaned_number = article_number.strip()
        if not cleaned_number:
            raise ValueError("Article number must not be empty.")
        normalized_number = cleaned_number.upper()
        if not ARTICLE_NUMBER_PATTERN.match(normalized_number):
            raise ValueError(
                f"Article number '{cleaned_number}' does not match the expected "
                f"pattern (e.g., WKB12345). Override ARTICLE_NUMBER_PATTERN if "
                f"the Waters KB uses a different format."
            )
        return normalized_number

    @field_validator("title")
    @classmethod
    def validate_title(cls, title: str) -> str:
        """Ensure the title is non-empty and whitespace-normalized."""
        cleaned_title = _normalize_whitespace(title)
        if not cleaned_title:
            raise ValueError("Article title must not be empty.")
        return cleaned_title

    @field_validator("url")
    @classmethod
    def validate_url(cls, url: str) -> str:
        """Ensure the URL is a valid HTTP or HTTPS URL."""
        cleaned_url = url.strip()
        if not cleaned_url:
            raise ValueError("Article URL must not be empty.")
        # Validate it is a proper HTTP(S) URL
        try:
            parsed_url = HttpUrl(cleaned_url)
            scheme = str(parsed_url.scheme).lower()
            if scheme not in ("http", "https"):
                raise ValueError(
                    f"Article URL must use HTTP or HTTPS, got '{scheme}'."
                )
        except Exception as url_error:
            raise ValueError(
                f"Article URL '{cleaned_url}' is not a valid URL: {url_error}"
            )
        return cleaned_url

    @field_validator("searchable_content")
    @classmethod
    def validate_searchable_content(cls, searchable_content: str) -> str:
        """Ensure searchable content contains meaningful text."""
        cleaned_content = _normalize_whitespace(searchable_content)
        # Require at least 50 characters of meaningful text
        minimum_content_length = 50
        if len(cleaned_content) < minimum_content_length:
            raise ValueError(
                f"Searchable content is too short ({len(cleaned_content)} chars). "
                f"Expected at least {minimum_content_length} characters of "
                f"meaningful article text."
            )
        return cleaned_content

    @field_validator("source_updated_at")
    @classmethod
    def validate_source_updated_at(
        cls, source_updated_at: Optional[datetime]
    ) -> Optional[datetime]:
        """Ensure the source update date is timezone-aware if present."""
        if source_updated_at is None:
            return None
        if source_updated_at.tzinfo is None:
            # Assume UTC if no timezone is provided
            return source_updated_at.replace(tzinfo=timezone.utc)
        return source_updated_at

    @field_validator("instrument_names")
    @classmethod
    def validate_instrument_names(
        cls, instrument_names: list[str]
    ) -> list[str]:
        """Clean, deduplicate, and sort instrument names."""
        cleaned_names: list[str] = []
        seen_lowercase_names: set[str] = set()

        for raw_name in instrument_names:
            cleaned_name = _normalize_whitespace(raw_name)
            if not cleaned_name:
                continue
            lowercase_name = cleaned_name.lower()
            if lowercase_name not in seen_lowercase_names:
                seen_lowercase_names.add(lowercase_name)
                cleaned_names.append(cleaned_name)

        return sorted(cleaned_names, key=lambda name: name.lower())

    @model_validator(mode="after")
    def generate_content_hash_if_empty(self) -> "ArticleRecord":
        """Generate the content hash from stable values if not already set."""
        if not self.content_hash:
            from waters_knowledge_base.utilities.content_hashing import (
                compute_article_content_hash,
            )

            self.content_hash = compute_article_content_hash(
                article_number=self.article_number,
                title=self.title,
                url=self.url,
                searchable_content=self.searchable_content,
                instrument_names=self.instrument_names,
                source_updated_at=self.source_updated_at,
            )
        return self


def _normalize_whitespace(text: str) -> str:
    """Remove leading/trailing whitespace and collapse internal whitespace."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())
