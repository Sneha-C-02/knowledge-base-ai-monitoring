"""
Article repository for database operations on the articles table.

Handles insert, update, conflict detection, and change comparison
for Waters Knowledge Base article records using parameterized SQL.
"""

import logging
from typing import Any, Optional

import psycopg

logger = logging.getLogger(__name__)


class ArticleConflictError(Exception):
    """Raised when article_number and URL point to different existing rows."""
    pass


def find_existing_article_by_number(
    database_cursor: psycopg.Cursor,
    article_number: str,
) -> Optional[dict[str, Any]]:
    """
    Find an existing article by its unique article number.

    Args:
        database_cursor: An open database cursor.
        article_number: The article number to search for.

    Returns:
        A dictionary of article column values, or None if not found.
    """
    database_cursor.execute(
        """
        SELECT id, article_number, title, url, searchable_content,
               source_updated_at
        FROM public.articles
        WHERE article_number = %(article_number)s
        """,
        {"article_number": article_number},
    )
    return database_cursor.fetchone()


def find_existing_article_by_url(
    database_cursor: psycopg.Cursor,
    article_url: str,
) -> Optional[dict[str, Any]]:
    """
    Find an existing article by its unique URL.

    Args:
        database_cursor: An open database cursor.
        article_url: The article URL to search for.

    Returns:
        A dictionary of article column values, or None if not found.
    """
    database_cursor.execute(
        """
        SELECT id, article_number, title, url, searchable_content,
               source_updated_at
        FROM public.articles
        WHERE url = %(article_url)s
        """,
        {"article_url": article_url},
    )
    return database_cursor.fetchone()


def check_for_article_conflicts(
    database_cursor: psycopg.Cursor,
    article_number: str,
    article_url: str,
) -> None:
    """
    Check for data conflicts between article_number and URL uniqueness.

    Raises ArticleConflictError if article_number matches one row but
    the URL belongs to a different row.

    Args:
        database_cursor: An open database cursor.
        article_number: The article number to check.
        article_url: The article URL to check.

    Raises:
        ArticleConflictError: If a cross-reference conflict is detected.
    """
    row_by_number = find_existing_article_by_number(database_cursor, article_number)
    row_by_url = find_existing_article_by_url(database_cursor, article_url)

    if row_by_number and row_by_url:
        if row_by_number["id"] != row_by_url["id"]:
            raise ArticleConflictError(
                f"Data conflict: article_number '{article_number}' exists in "
                f"row {row_by_number['id']} but URL '{article_url}' exists in "
                f"row {row_by_url['id']}. Manual review required."
            )


def insert_article(
    database_cursor: psycopg.Cursor,
    article_number: str,
    title: str,
    article_url: str,
    searchable_content: str,
    source_updated_at: Any = None,
) -> int:
    """
    Insert a new article record and return its generated ID.

    Args:
        database_cursor: An open database cursor.
        article_number: Normalized article identifier.
        title: Cleaned article title.
        article_url: Canonical article URL.
        searchable_content: Cleaned article text.
        source_updated_at: Timezone-aware datetime or None.

    Returns:
        The generated article ID (bigint).
    """
    database_cursor.execute(
        """
        INSERT INTO public.articles
            (article_number, title, url, searchable_content, source_updated_at)
        VALUES
            (%(article_number)s, %(title)s, %(url)s,
             %(searchable_content)s, %(source_updated_at)s)
        RETURNING id
        """,
        {
            "article_number": article_number,
            "title": title,
            "url": article_url,
            "searchable_content": searchable_content,
            "source_updated_at": source_updated_at,
        },
    )
    result = database_cursor.fetchone()
    saved_article_id = result["id"]
    logger.debug("Inserted article %s with ID %d.", article_number, saved_article_id)
    return saved_article_id


def update_article(
    database_cursor: psycopg.Cursor,
    article_id: int,
    title: str,
    article_url: str,
    searchable_content: str,
    source_updated_at: Any = None,
) -> None:
    """
    Update an existing article record.

    Does NOT update article_number (the natural key) or search_vector
    (generated column).

    Args:
        database_cursor: An open database cursor.
        article_id: The existing article's ID.
        title: Updated title.
        article_url: Updated canonical URL.
        searchable_content: Updated article text.
        source_updated_at: Updated timezone-aware datetime or None.
    """
    database_cursor.execute(
        """
        UPDATE public.articles
        SET title = %(title)s,
            url = %(url)s,
            searchable_content = %(searchable_content)s,
            source_updated_at = %(source_updated_at)s
        WHERE id = %(article_id)s
        """,
        {
            "article_id": article_id,
            "title": title,
            "url": article_url,
            "searchable_content": searchable_content,
            "source_updated_at": source_updated_at,
        },
    )
    logger.debug("Updated article ID %d.", article_id)


def has_article_content_changed(
    existing_article: dict[str, Any],
    new_title: str,
    new_url: str,
    new_searchable_content: str,
    new_source_updated_at: Any = None,
) -> bool:
    """
    Compare existing article values with new values to detect changes.

    Performs normalized comparison in Python since the schema does not
    have a content_hash column.

    Args:
        existing_article: Dictionary of current database values.
        new_title: New title to compare.
        new_url: New URL to compare.
        new_searchable_content: New content to compare.
        new_source_updated_at: New date to compare.

    Returns:
        True if any field has changed, False if all match.
    """
    if existing_article["title"] != new_title:
        return True
    if existing_article["url"] != new_url:
        return True
    if existing_article["searchable_content"] != new_searchable_content:
        return True

    existing_date = existing_article.get("source_updated_at")
    if existing_date != new_source_updated_at:
        # Handle None vs None comparison
        if existing_date is None and new_source_updated_at is None:
            pass
        else:
            return True

    return False
