"""
Tests for the ArticleRecord Pydantic validation model.

Validates required fields, pattern matching, whitespace normalization,
content hash generation, and rejection of invalid data.
"""

from datetime import datetime, timezone

import pytest

from waters_knowledge_base.models.article_record import ArticleRecord


class TestArticleNumberValidation:
    """Tests for article number validation rules."""

    def test_valid_article_number(self):
        """Valid WKB numbers should be accepted."""
        record = ArticleRecord(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
        )
        assert record.article_number == "WKB12345"

    def test_normalizes_to_uppercase(self):
        """Article numbers should be normalized to uppercase."""
        record = ArticleRecord(
            article_number="wkb12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
        )
        assert record.article_number == "WKB12345"

    def test_rejects_empty_article_number(self):
        """Empty article number should raise ValidationError."""
        with pytest.raises(Exception):
            ArticleRecord(
                article_number="",
                title="Test Title",
                url="https://www.waters.com/test",
                searchable_content="A" * 60,
            )

    def test_rejects_invalid_pattern(self):
        """Non-WKB article numbers should be rejected."""
        with pytest.raises(Exception):
            ArticleRecord(
                article_number="INVALID123",
                title="Test Title",
                url="https://www.waters.com/test",
                searchable_content="A" * 60,
            )


class TestTitleValidation:
    """Tests for title validation rules."""

    def test_rejects_empty_title(self):
        """Empty title should raise ValidationError."""
        with pytest.raises(Exception):
            ArticleRecord(
                article_number="WKB12345",
                title="",
                url="https://www.waters.com/test",
                searchable_content="A" * 60,
            )

    def test_normalizes_whitespace(self):
        """Title whitespace should be normalized."""
        record = ArticleRecord(
            article_number="WKB12345",
            title="  Title   with   spaces  ",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
        )
        assert record.title == "Title with spaces"


class TestUrlValidation:
    """Tests for URL validation rules."""

    def test_valid_https_url(self):
        """Valid HTTPS URLs should be accepted."""
        record = ArticleRecord(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/support/kb/WKB12345",
            searchable_content="A" * 60,
        )
        assert "waters.com" in record.url

    def test_rejects_empty_url(self):
        """Empty URL should raise ValidationError."""
        with pytest.raises(Exception):
            ArticleRecord(
                article_number="WKB12345",
                title="Test Title",
                url="",
                searchable_content="A" * 60,
            )


class TestSearchableContentValidation:
    """Tests for searchable content validation."""

    def test_rejects_too_short_content(self):
        """Content shorter than 50 characters should be rejected."""
        with pytest.raises(Exception):
            ArticleRecord(
                article_number="WKB12345",
                title="Test Title",
                url="https://www.waters.com/test",
                searchable_content="Too short",
            )

    def test_accepts_sufficient_content(self):
        """Content with 50+ characters should be accepted."""
        long_content = "This is test content. " * 5
        record = ArticleRecord(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content=long_content,
        )
        assert len(record.searchable_content) >= 50


class TestInstrumentNameValidation:
    """Tests for instrument name list validation."""

    def test_deduplicates_instrument_names(self):
        """Duplicate names should be removed case-insensitively."""
        record = ArticleRecord(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
            instrument_names=["Empower", "EMPOWER", "empower"],
        )
        assert len(record.instrument_names) == 1

    def test_sorts_instrument_names(self):
        """Instrument names should be sorted."""
        record = ArticleRecord(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
            instrument_names=["Zebra", "Alpha", "Middle"],
        )
        assert record.instrument_names == ["Alpha", "Middle", "Zebra"]

    def test_removes_empty_strings(self):
        """Empty strings should be filtered from instrument names."""
        record = ArticleRecord(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
            instrument_names=["Empower", "", "  ", "QSM"],
        )
        assert "" not in record.instrument_names
        assert len(record.instrument_names) == 2


class TestContentHashGeneration:
    """Tests for deterministic content hash generation."""

    def test_generates_content_hash(self):
        """A content hash should be generated automatically."""
        record = ArticleRecord(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
        )
        assert record.content_hash != ""
        assert len(record.content_hash) == 64  # SHA-256 hex digest

    def test_hash_is_deterministic(self):
        """Same inputs should produce the same hash."""
        kwargs = dict(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
            instrument_names=["Empower"],
        )
        record1 = ArticleRecord(**kwargs)
        record2 = ArticleRecord(**kwargs)
        assert record1.content_hash == record2.content_hash

    def test_hash_changes_with_different_content(self):
        """Different content should produce different hashes."""
        common = dict(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
        )
        record1 = ArticleRecord(searchable_content="A" * 60, **common)
        record2 = ArticleRecord(searchable_content="B" * 60, **common)
        assert record1.content_hash != record2.content_hash


class TestDateValidation:
    """Tests for source_updated_at validation."""

    def test_accepts_timezone_aware_date(self):
        """Timezone-aware dates should be accepted as-is."""
        aware_date = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        record = ArticleRecord(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
            source_updated_at=aware_date,
        )
        assert record.source_updated_at is not None
        assert record.source_updated_at.tzinfo is not None

    def test_makes_naive_date_utc(self):
        """Naive dates should be converted to UTC."""
        naive_date = datetime(2026, 1, 15, 10, 0, 0)
        record = ArticleRecord(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
            source_updated_at=naive_date,
        )
        assert record.source_updated_at is not None
        assert record.source_updated_at.tzinfo == timezone.utc

    def test_accepts_none_date(self):
        """None date should be accepted."""
        record = ArticleRecord(
            article_number="WKB12345",
            title="Test Title",
            url="https://www.waters.com/test",
            searchable_content="A" * 60,
            source_updated_at=None,
        )
        assert record.source_updated_at is None
