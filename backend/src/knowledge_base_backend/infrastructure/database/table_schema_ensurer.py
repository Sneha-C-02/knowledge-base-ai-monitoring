"""Lazily provisions individual tables that opt into runtime auto-creation.

Schema provisioning is a distinct concern from data access: a repository's
job is to read and write rows, not to decide when DDL should run. This
collaborator exists so that concern has exactly one home instead of being
mixed into repository classes, and so it can be reused by any repository
that wants "auto-create my table if it's missing" behaviour.

Registered as a process-wide singleton by the DI container, so the
"have we already verified this table?" cache is explicit, injectable state
owned by one object — not a hidden mutable class attribute on a repository
that is otherwise constructed per-request.
"""

import logging
from typing import Set

from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TableSchemaEnsurer:
    """
    Ensures a given SQLAlchemy `Table` exists in the database, creating it
    (and its indexes/constraints) on first use if it doesn't. Safe to call
    repeatedly: verified tables are cached for the lifetime of this instance
    so the existence check only runs once per table per process.
    """

    def __init__(self) -> None:
        self._verified_table_names: Set[str] = set()

    async def ensure_table_exists(self, session: AsyncSession, table: Table) -> None:
        """
        Create `table` via `CREATE TABLE IF NOT EXISTS` semantics if it has
        not already been verified in this process. Failures are logged but
        never raised: a concurrent request may have created the table first,
        and if the table genuinely does not exist, the caller's subsequent
        query will surface a clear error on its own.
        """
        if table.name in self._verified_table_names:
            return
        try:
            connection = await session.connection()
            await connection.run_sync(lambda sync_conn: table.create(sync_conn, checkfirst=True))
            self._verified_table_names.add(table.name)
        except Exception as e:
            logger.warning(f"Auto-creation check for table '{table.name}' failed: {e}")
