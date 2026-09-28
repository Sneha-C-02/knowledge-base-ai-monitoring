"""Coordinates the best-effort "learn error-related keywords" side effect
that runs alongside log analysis.

Both `AnalyzeUploadedLogsUseCase` and `AnalyzeLogsWithMemoryUseCase` need to
turn classified log events into persisted keyword-occurrence counts, and in
both cases a failure to do so must never abort the main analysis result.
Rather than duplicating that "extract candidates, persist them, and swallow
failures" policy in each use case, it lives here exactly once.
"""

import logging
from typing import List, Optional

from src.knowledge_base_backend.domain.repositories.learned_keyword_repository import LearnedKeywordRepository
from src.knowledge_base_backend.domain.services.log_keyword_extractor import ExtractedKeywordEvent, LogKeywordExtractor
from src.knowledge_base_backend.domain.services.log_keyword_learning_service import LogKeywordLearningService

logger = logging.getLogger(__name__)


class KeywordLearningCoordinator:
    """
    Single collaborator responsible for turning classified log events into
    persisted, error-related keyword suggestions.

    Keyword learning is always a best-effort side effect of log analysis,
    never part of its critical path: every public method here catches and
    logs its own failures instead of propagating them to the caller.
    """

    def __init__(
        self,
        keyword_learning_service: LogKeywordLearningService,
        learned_keyword_repository: Optional[LearnedKeywordRepository] = None,
        keyword_extractor: Optional[LogKeywordExtractor] = None,
    ) -> None:
        self._keyword_learning_service = keyword_learning_service
        self._learned_keyword_repository = learned_keyword_repository
        self._keyword_extractor = keyword_extractor or LogKeywordExtractor()

    async def learn_from_text(self, log_content: str, instrument_id: int) -> None:
        """
        Convenience entry point for callers that have not already extracted
        keyword events for another purpose. Extracts events first, then
        delegates to `learn_from_events`.
        """
        try:
            events = self._keyword_extractor.extract_from_text(log_content)
        except Exception as e:
            logger.warning(f"Keyword extraction failed for instrument {instrument_id}: {e}")
            return
        await self.learn_from_events(events, instrument_id)

    async def learn_from_events(self, events: List[ExtractedKeywordEvent], instrument_id: int) -> None:
        """
        Entry point for callers that already extracted keyword events for
        another purpose (e.g. vectorization), avoiding a redundant regex pass.
        """
        if self._learned_keyword_repository is None or not events:
            return
        try:
            candidates = self._keyword_learning_service.extract_candidates(events)
            if candidates:
                await self._learned_keyword_repository.record_occurrences(instrument_id, candidates)
        except Exception as e:
            logger.warning(f"Keyword learning failed for instrument {instrument_id}: {e}")
