from typing import Protocol, List, Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class GeneratedSupportAnswer:
    answer: str
    related_article_number: Optional[str]
    related_article_url: Optional[str]
    confidence_score: float

class GroundedAnswerGenerationService(Protocol):
    async def generate_grounded_support_answer(self, query: str, context: str) -> GeneratedSupportAnswer: ...
