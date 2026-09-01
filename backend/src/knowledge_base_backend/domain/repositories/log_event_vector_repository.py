from typing import Protocol, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LogEventVectorRecord:
    """Data object used when saving a vectorised log event."""
    instrument_id: int
    log_filename: str
    severity: str                          # "critical" | "warning" | "info"
    component: str
    cleaned_text: str
    raw_log_line: str
    matched_patterns: List[str]
    event_embedding: List[float]           # 384-dim vector


@dataclass
class LogEventVectorMatch:
    """Data object returned from a vector similarity search."""
    id: int
    instrument_id: int
    log_filename: str
    severity: str
    component: str
    cleaned_text: str
    raw_log_line: str
    matched_patterns: List[str]
    similarity_score: float
    captured_at: datetime


class LogEventVectorRepository(Protocol):
    """Port for storing and searching keyword-distilled log event vectors."""

    async def save_batch(self, records: List[LogEventVectorRecord]) -> int:
        """
        Bulk-insert a list of log event vectors.
        Returns the number of rows inserted.
        """
        ...

    async def search_by_vector(
        self,
        query_embedding: List[float],
        min_similarity: float = 0.6,
        limit: int = 5,
        instrument_id: int | None = None,
        severity_filter: str | None = None,
    ) -> List[LogEventVectorMatch]:
        """
        Cosine-similarity search against stored log event vectors.

        Args:
            query_embedding: The embedding of the user's support query.
            min_similarity:  Minimum cosine similarity (0-1) to include.
            limit:           Max results to return.
            instrument_id:   Optional filter to one instrument.
            severity_filter: Optional filter by severity ("critical", "warning", "info").

        Returns:
            List of matches sorted by similarity descending.
        """
        ...
