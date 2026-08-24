from src.knowledge_base_backend.domain.services.hybrid_article_retrieval_service import HybridArticleRetrievalService
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch
from typing import List, Optional

class RetrieveRelevantArticlesUseCase:
    def __init__(self, retrieval_service: HybridArticleRetrievalService) -> None:
        self.retrieval_service = retrieval_service
        
    async def execute(self, query: str, instrument: Optional[str] = None, limit: int = 5) -> List[RelevantArticleMatch]:
        return await self.retrieval_service.retrieve_relevant_articles(query, instrument, limit)
