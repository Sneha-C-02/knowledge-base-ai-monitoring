from typing import Protocol, List
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch

class GroundingContextBuilder(Protocol):
    def build_context(self, articles: List[RelevantArticleMatch]) -> str: ...
