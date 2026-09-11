from dataclasses import dataclass
from typing import List

from src.knowledge_base_backend.domain.repositories.learned_keyword_repository import LearnedKeywordRepository


@dataclass
class KeywordSuggestionDto:
    keyword: str
    severity: str
    occurrence_count: int


class GetLearnedKeywordSuggestionsUseCase:
    """
    Returns the keywords the system has learned from error/warning lines in
    previously analyzed logs, most frequent first — for use as suggestions
    in the keyword-focused search UI.
    """

    def __init__(self, learned_keyword_repository: LearnedKeywordRepository) -> None:
        self.learned_keyword_repository = learned_keyword_repository

    async def execute(self, instrument_id: int = 0, limit: int = 10) -> List[KeywordSuggestionDto]:
        keywords = await self.learned_keyword_repository.get_top_keywords(instrument_id=instrument_id, limit=limit)
        return [
            KeywordSuggestionDto(
                keyword=keyword.keyword,
                severity=keyword.severity,
                occurrence_count=keyword.occurrence_count,
            )
            for keyword in keywords
        ]
