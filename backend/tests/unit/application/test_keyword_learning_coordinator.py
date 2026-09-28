import pytest

from src.knowledge_base_backend.application.services.keyword_learning_coordinator import KeywordLearningCoordinator
from src.knowledge_base_backend.domain.services.log_keyword_extractor import LogKeywordExtractor
from src.knowledge_base_backend.domain.services.log_keyword_learning_service import LogKeywordLearningService


class RecordingRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[int, list]] = []

    async def record_occurrences(self, instrument_id: int, candidates: list) -> None:
        self.calls.append((instrument_id, candidates))

    async def get_top_keywords(self, instrument_id: int = 0, limit: int = 10) -> list:
        return []


class FailingRepository:
    async def record_occurrences(self, instrument_id: int, candidates: list) -> None:
        raise RuntimeError("database unavailable")

    async def get_top_keywords(self, instrument_id: int = 0, limit: int = 10) -> list:
        return []


@pytest.mark.asyncio
async def test_learn_from_text_persists_candidates_from_error_lines() -> None:
    repository = RecordingRepository()
    coordinator = KeywordLearningCoordinator(
        keyword_learning_service=LogKeywordLearningService(),
        learned_keyword_repository=repository,
        keyword_extractor=LogKeywordExtractor(),
    )

    await coordinator.learn_from_text("(EPC): Fatal error in pump controller", instrument_id=42)

    assert len(repository.calls) == 1
    instrument_id, candidates = repository.calls[0]
    assert instrument_id == 42
    assert len(candidates) > 0


@pytest.mark.asyncio
async def test_learn_from_events_skips_persistence_when_no_repository_configured() -> None:
    coordinator = KeywordLearningCoordinator(
        keyword_learning_service=LogKeywordLearningService(),
        learned_keyword_repository=None,
    )

    events = LogKeywordExtractor().extract_from_text("(EPC): Fatal error in pump controller")
    # Must not raise even though there's nowhere to persist candidates.
    await coordinator.learn_from_events(events, instrument_id=1)


@pytest.mark.asyncio
async def test_learn_from_text_never_raises_when_repository_fails() -> None:
    coordinator = KeywordLearningCoordinator(
        keyword_learning_service=LogKeywordLearningService(),
        learned_keyword_repository=FailingRepository(),
        keyword_extractor=LogKeywordExtractor(),
    )

    # A persistence failure must be swallowed: keyword learning is a
    # best-effort side effect and must never abort the caller's main flow.
    await coordinator.learn_from_text("(EPC): Fatal error in pump controller", instrument_id=1)


@pytest.mark.asyncio
async def test_learn_from_events_with_no_events_does_not_call_repository() -> None:
    repository = RecordingRepository()
    coordinator = KeywordLearningCoordinator(
        keyword_learning_service=LogKeywordLearningService(),
        learned_keyword_repository=repository,
    )

    await coordinator.learn_from_events([], instrument_id=1)

    assert repository.calls == []
