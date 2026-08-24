"""
Tests for database repository modules.

Uses mocks to test article and instrument repository logic without
connecting to a production database. Validates insert, update, conflict
detection, unchanged detection, instrument upsert, and relationship
synchronization behavior.
"""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest

from waters_knowledge_base.database.article_repository import (
    ArticleConflictError,
    check_for_article_conflicts,
    find_existing_article_by_number,
    has_article_content_changed,
    insert_article,
    update_article,
)
from waters_knowledge_base.database.instrument_repository import (
    find_or_create_instrument,
    get_current_instrument_ids_for_article,
    synchronize_article_instrument_links,
)


class TestArticleInsert:
    """Tests for article insert logic."""

    def test_insert_returns_generated_id(self):
        """Insert should return the auto-generated article ID."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 42}

        saved_id = insert_article(
            database_cursor=mock_cursor,
            article_number="WKB12345",
            title="Test Article",
            article_url="https://www.waters.com/test",
            searchable_content="Content goes here...",
            source_updated_at=None,
        )

        assert saved_id == 42
        mock_cursor.execute.assert_called_once()

    def test_insert_uses_parameterized_sql(self):
        """Insert should use parameterized SQL, not string concatenation."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1}

        insert_article(
            database_cursor=mock_cursor,
            article_number="WKB99999",
            title="Title",
            article_url="https://example.com",
            searchable_content="Content",
        )

        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        parameters = call_args[0][1]

        # SQL should contain parameter placeholders, not literal values
        assert "%(article_number)s" in sql_query
        assert "WKB99999" not in sql_query
        assert parameters["article_number"] == "WKB99999"


class TestArticleUpdate:
    """Tests for article update logic."""

    def test_update_does_not_change_article_number(self):
        """Update should not modify the article_number column."""
        mock_cursor = MagicMock()

        update_article(
            database_cursor=mock_cursor,
            article_id=42,
            title="Updated Title",
            article_url="https://www.waters.com/updated",
            searchable_content="Updated content",
        )

        sql_query = mock_cursor.execute.call_args[0][0]
        # The SET clause should not include article_number
        assert "article_number" not in sql_query.split("SET")[1].split("WHERE")[0]


class TestArticleChangeDetection:
    """Tests for detecting whether article content has changed."""

    def test_detects_title_change(self):
        """Should detect when the title has changed."""
        existing = {
            "title": "Old Title",
            "url": "https://example.com",
            "searchable_content": "Content",
            "source_updated_at": None,
        }
        assert has_article_content_changed(
            existing, "New Title", "https://example.com", "Content", None
        ) is True

    def test_detects_content_change(self):
        """Should detect when searchable_content has changed."""
        existing = {
            "title": "Title",
            "url": "https://example.com",
            "searchable_content": "Old Content",
            "source_updated_at": None,
        }
        assert has_article_content_changed(
            existing, "Title", "https://example.com", "New Content", None
        ) is True

    def test_detects_unchanged(self):
        """Should report no change when all fields match."""
        existing = {
            "title": "Title",
            "url": "https://example.com",
            "searchable_content": "Content",
            "source_updated_at": None,
        }
        assert has_article_content_changed(
            existing, "Title", "https://example.com", "Content", None
        ) is False

    def test_detects_url_change(self):
        """Should detect when the URL has changed."""
        existing = {
            "title": "Title",
            "url": "https://old.example.com",
            "searchable_content": "Content",
            "source_updated_at": None,
        }
        assert has_article_content_changed(
            existing, "Title", "https://new.example.com", "Content", None
        ) is True


class TestArticleConflictDetection:
    """Tests for detecting article number / URL conflicts."""

    def test_no_conflict_when_both_match_same_row(self):
        """No conflict when article_number and URL point to the same row."""
        mock_cursor = MagicMock()
        same_row = {"id": 1, "article_number": "WKB12345", "url": "https://example.com",
                     "title": "", "searchable_content": "", "source_updated_at": None}

        mock_cursor.fetchone.side_effect = [same_row, same_row]

        # Should not raise
        check_for_article_conflicts(mock_cursor, "WKB12345", "https://example.com")

    def test_conflict_when_pointing_to_different_rows(self):
        """Should raise when article_number and URL point to different rows."""
        mock_cursor = MagicMock()
        row_by_number = {"id": 1, "article_number": "WKB12345", "url": "https://a.com",
                         "title": "", "searchable_content": "", "source_updated_at": None}
        row_by_url = {"id": 2, "article_number": "WKB99999", "url": "https://b.com",
                      "title": "", "searchable_content": "", "source_updated_at": None}

        mock_cursor.fetchone.side_effect = [row_by_number, row_by_url]

        with pytest.raises(ArticleConflictError):
            check_for_article_conflicts(mock_cursor, "WKB12345", "https://b.com")


class TestInstrumentUpsert:
    """Tests for instrument upsert logic."""

    def test_returns_instrument_id(self):
        """Should return the instrument ID after upsert."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 7}

        saved_id = find_or_create_instrument(mock_cursor, "Empower")
        assert saved_id == 7

    def test_uses_on_conflict(self):
        """Should use ON CONFLICT for safe upsert."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1}

        find_or_create_instrument(mock_cursor, "ACQUITY UPLC")

        sql_query = mock_cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in sql_query


class TestRelationshipSynchronization:
    """Tests for article-instrument relationship synchronization."""

    def test_adds_missing_links(self):
        """Should insert new instrument links."""
        mock_cursor = MagicMock()
        # First call: get current links (empty)
        mock_cursor.fetchall.return_value = []

        result = synchronize_article_instrument_links(
            mock_cursor,
            article_id=1,
            desired_instrument_ids={10, 20},
        )

        assert result["added"] == 2
        assert result["removed"] == 0

    def test_removes_stale_links(self):
        """Should delete instrument links no longer present."""
        mock_cursor = MagicMock()
        # Current links include instrument 30 which is no longer desired
        mock_cursor.fetchall.return_value = [
            {"instrument_id": 10},
            {"instrument_id": 30},
        ]

        result = synchronize_article_instrument_links(
            mock_cursor,
            article_id=1,
            desired_instrument_ids={10, 20},
        )

        assert result["added"] == 1   # 20 is new
        assert result["removed"] == 1  # 30 is stale
        assert result["unchanged"] == 1  # 10 stays

    def test_leaves_matching_links(self):
        """Should not modify links that are already correct."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"instrument_id": 10},
            {"instrument_id": 20},
        ]

        result = synchronize_article_instrument_links(
            mock_cursor,
            article_id=1,
            desired_instrument_ids={10, 20},
        )

        assert result["added"] == 0
        assert result["removed"] == 0
        assert result["unchanged"] == 2
