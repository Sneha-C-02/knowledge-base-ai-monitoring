"""
Database connection management for the Waters Knowledge Base Loader.

Provides safe PostgreSQL connection handling using psycopg version 3,
with context managers, connection testing, credential masking, and
configurable timeouts.
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator
import queue

import psycopg
from psycopg.rows import dict_row

from waters_knowledge_base.utilities.text_helpers import mask_database_credentials

logger = logging.getLogger(__name__)

# Default connection timeout in seconds
DEFAULT_CONNECTION_TIMEOUT_SECONDS: int = 15
DEFAULT_STATEMENT_TIMEOUT_SECONDS: int = 60
POOL_SIZE: int = 15


class DatabaseConnectionError(Exception):
    """Raised when the database connection cannot be established."""
    pass


class DatabaseConnectionManager:
    """
    Manages PostgreSQL connections using psycopg version 3.

    Provides context managers for safe connection and cursor lifecycle,
    connection testing, and credential-safe error reporting.
    """

    def __init__(
        self,
        connection_url: str | None = None,
        connection_timeout_seconds: int = DEFAULT_CONNECTION_TIMEOUT_SECONDS,
        statement_timeout_seconds: int = DEFAULT_STATEMENT_TIMEOUT_SECONDS,
    ):
        """
        Initialize the connection manager.

        Args:
            connection_url: PostgreSQL connection string. If None, reads
                from DATABASE_CONNECTION_URL env var.
            connection_timeout_seconds: Timeout for establishing connections.
            statement_timeout_seconds: Timeout for individual SQL statements.
        """
        self.connection_url: str = connection_url or os.environ.get(
            "DATABASE_CONNECTION_URL", ""
        )
        self.connection_timeout_seconds = connection_timeout_seconds
        self.statement_timeout_seconds = statement_timeout_seconds

        if not self.connection_url:
            raise DatabaseConnectionError(
                "DATABASE_CONNECTION_URL is not set. "
                "Please set it in your .env file or environment."
            )

        self._masked_url = mask_database_credentials(self.connection_url)
        self._pool = queue.Queue(maxsize=POOL_SIZE)
        
        # Pre-fill the pool
        logger.info(f"Initializing database connection pool with {POOL_SIZE} connections...")
        for _ in range(POOL_SIZE):
            conn = self._create_new_connection()
            self._pool.put(conn)

    def _create_new_connection(self) -> psycopg.Connection:
        try:
            return psycopg.connect(
                self.connection_url,
                autocommit=False,
                row_factory=dict_row,
                connect_timeout=self.connection_timeout_seconds,
                options=f"-c statement_timeout={self.statement_timeout_seconds * 1000}",
            )
        except psycopg.OperationalError as connection_error:
            safe_message = str(connection_error)
            if self.connection_url in safe_message:
                safe_message = safe_message.replace(
                    self.connection_url, self._masked_url
                )
            raise DatabaseConnectionError(
                f"Failed to connect to the database: {safe_message}"
            ) from connection_error
    
    def close(self):
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                if not conn.closed:
                    conn.close()
            except Exception:
                pass

    @contextmanager
    def get_connection(
        self, autocommit: bool = False
    ) -> Generator[psycopg.Connection, None, None]:
        """
        Open a database connection as a context manager.

        The connection is committed on successful exit and rolled back
        on exception. It is always closed when the context exits.

        Args:
            autocommit: If True, each statement is auto-committed.

        Yields:
            An open psycopg connection.
        """
        database_connection = None
        try:
            # Block until a connection is available in the pool
            database_connection = self._pool.get(timeout=30)
            
            # Reconnect if the connection is dead
            if database_connection.closed:
                database_connection = self._create_new_connection()
                
            database_connection.autocommit = autocommit
            
            yield database_connection
            
            if not autocommit:
                database_connection.commit()
                
            # Return to pool
            self._pool.put(database_connection)
            database_connection = None
            
        except psycopg.OperationalError as connection_error:
            safe_message = str(connection_error)
            if self.connection_url in safe_message:
                safe_message = safe_message.replace(
                    self.connection_url, self._masked_url
                )
            logger.error("Database connection error: %s", safe_message)
            if database_connection and not autocommit and not database_connection.closed:
                try:
                    database_connection.rollback()
                except Exception:
                    pass
            # Drop bad connection, create a new one to replace it in the pool
            new_conn = self._create_new_connection()
            self._pool.put(new_conn)
            
            raise DatabaseConnectionError(
                f"Failed to communicate with database: {safe_message}"
            ) from connection_error
        except Exception as unexpected_error:
            if database_connection and not autocommit and not database_connection.closed:
                try:
                    database_connection.rollback()
                    logger.warning("Transaction rolled back due to error.")
                except Exception:
                    pass
            if database_connection:
                self._pool.put(database_connection)
            raise

    @contextmanager
    def get_cursor(
        self, database_connection: psycopg.Connection
    ) -> Generator[psycopg.Cursor, None, None]:
        """
        Open a cursor as a context manager.

        Args:
            database_connection: An open database connection.

        Yields:
            A database cursor.
        """
        database_cursor = database_connection.cursor()
        try:
            yield database_cursor
        finally:
            database_cursor.close()

    def test_connection(self) -> bool:
        """
        Test that the database connection works.

        Returns:
            True if the connection test succeeds.

        Raises:
            DatabaseConnectionError: If the test fails.
        """
        try:
            with self.get_connection() as database_connection:
                with self.get_cursor(database_connection) as database_cursor:
                    database_cursor.execute("SELECT 1 AS connection_test")
                    test_result = database_cursor.fetchone()
                    if test_result and test_result.get("connection_test") == 1:
                        logger.info(
                            "Database connection test PASSED (%s).",
                            self._masked_url,
                        )
                        return True
                    raise DatabaseConnectionError(
                        "Connection test query returned unexpected result."
                    )
        except DatabaseConnectionError:
            raise
        except Exception as test_error:
            raise DatabaseConnectionError(
                f"Database connection test failed: {test_error}"
            ) from test_error
