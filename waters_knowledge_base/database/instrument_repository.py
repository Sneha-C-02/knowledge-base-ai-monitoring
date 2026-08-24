"""
Instrument repository for database operations on the instruments
and article_instruments tables.

Handles instrument upsert, relationship synchronization, and
transactional link management using parameterized SQL.
"""

import logging
from typing import Any, Optional

import psycopg

logger = logging.getLogger(__name__)


def find_or_create_instrument(
    database_cursor: psycopg.Cursor,
    instrument_name: str,
) -> int:
    """
    Find an existing instrument by name or create it if it does not exist.

    Uses INSERT ... ON CONFLICT to safely handle concurrent upserts.

    Args:
        database_cursor: An open database cursor.
        instrument_name: The canonical instrument name.

    Returns:
        The instrument ID (bigint).
    """
    database_cursor.execute(
        """
        INSERT INTO public.instruments (name)
        VALUES (%(instrument_name)s)
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """,
        {"instrument_name": instrument_name},
    )
    result = database_cursor.fetchone()
    saved_instrument_id = result["id"]
    logger.debug(
        "Instrument '%s' has ID %d.", instrument_name, saved_instrument_id
    )
    return saved_instrument_id


def get_current_instrument_ids_for_article(
    database_cursor: psycopg.Cursor,
    article_id: int,
) -> set[int]:
    """
    Retrieve the current set of instrument IDs linked to an article.

    Args:
        database_cursor: An open database cursor.
        article_id: The article's ID.

    Returns:
        Set of instrument IDs currently linked to the article.
    """
    database_cursor.execute(
        """
        SELECT instrument_id
        FROM public.article_instruments
        WHERE article_id = %(article_id)s
        """,
        {"article_id": article_id},
    )
    rows = database_cursor.fetchall()
    return {row["instrument_id"] for row in rows}


def synchronize_article_instrument_links(
    database_cursor: psycopg.Cursor,
    article_id: int,
    desired_instrument_ids: set[int],
) -> dict[str, int]:
    """
    Synchronize the article-to-instrument relationships.

    Adds missing links, removes stale links, and leaves matching
    links unchanged. All operations happen within the caller's
    transaction.

    Args:
        database_cursor: An open database cursor.
        article_id: The article's ID.
        desired_instrument_ids: The set of instrument IDs that should
            be linked to this article.

    Returns:
        A dictionary with counts: {"added": N, "removed": N, "unchanged": N}
    """
    current_instrument_ids = get_current_instrument_ids_for_article(
        database_cursor, article_id
    )

    ids_to_add = desired_instrument_ids - current_instrument_ids
    ids_to_remove = current_instrument_ids - desired_instrument_ids
    ids_unchanged = current_instrument_ids & desired_instrument_ids

    # Add missing links
    for instrument_id in ids_to_add:
        database_cursor.execute(
            """
            INSERT INTO public.article_instruments (article_id, instrument_id)
            VALUES (%(article_id)s, %(instrument_id)s)
            ON CONFLICT (article_id, instrument_id) DO NOTHING
            """,
            {"article_id": article_id, "instrument_id": instrument_id},
        )

    # Remove stale links
    if ids_to_remove:
        database_cursor.execute(
            """
            DELETE FROM public.article_instruments
            WHERE article_id = %(article_id)s
              AND instrument_id = ANY(%(instrument_ids)s)
            """,
            {
                "article_id": article_id,
                "instrument_ids": list(ids_to_remove),
            },
        )

    sync_result = {
        "added": len(ids_to_add),
        "removed": len(ids_to_remove),
        "unchanged": len(ids_unchanged),
    }
    logger.debug(
        "Instrument links for article %d: %s", article_id, sync_result
    )
    return sync_result
