from typing import Protocol, List, Optional
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch

class HybridArticleRetrievalService(Protocol):
    async def retrieve_relevant_articles(
        self, 
        query: str, 
        instrument_name: Optional[str], 
        limit: int
    ) -> List[RelevantArticleMatch]: ...
