from typing import List, Protocol

from src.knowledge_base_backend.domain.entities.learned_keyword import LearnedKeyword
from src.knowledge_base_backend.domain.services.log_keyword_learning_service import LearnedKeywordCandidate


class LearnedKeywordRepository(Protocol):
    """Port for persisting and retrieving learned, error-related search keywords.

    `instrument_id` uses 0 as a sentinel for "global / not tied to one
    instrument", matching the convention already used by
    `LogEventVectorRepository` elsewhere in this codebase.
    """

    async def record_occurrences(self, instrument_id: int, candidates: List[LearnedKeywordCandidate]) -> None:
        """
        Upsert each candidate's occurrence count for the given instrument
        (bumping occurrence_count and last_seen_at, or inserting a new row).
        """
        ...

    async def get_top_keywords(self, instrument_id: int = 0, limit: int = 10) -> List[LearnedKeyword]:
        """
        Return the most frequently observed error-related keywords, ranked by
        occurrence_count descending. When instrument_id is non-zero, results
        are merged across that instrument's own history (instrument_id match)
        and the global history (instrument_id == 0).
        """
        ...
