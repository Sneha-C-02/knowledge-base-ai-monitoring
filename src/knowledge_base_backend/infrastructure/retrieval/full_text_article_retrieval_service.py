from typing import List, Optional
from src.knowledge_base_backend.domain.services.hybrid_article_retrieval_service import HybridArticleRetrievalService
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch
from src.knowledge_base_backend.domain.repositories.article_repository import ArticleRepository
from src.knowledge_base_backend.domain.value_objects.article_search_criteria import ArticleSearchCriteria
import math

class FullTextArticleRetrievalService(HybridArticleRetrievalService):
    def __init__(self, article_repository: ArticleRepository) -> None:
        self.article_repository = article_repository

    async def retrieve_relevant_articles(
        self, query: str, instrument_name: Optional[str], limit: int
    ) -> List[RelevantArticleMatch]:
        criteria = ArticleSearchCriteria(search_query=query, instrument_name=instrument_name)
        articles = await self.article_repository.search_articles_by_full_text(criteria, limit)
        
        matches = []
        for a in articles:
            matches.append(RelevantArticleMatch(
                article=a,
                matched_instruments=a.instruments,
                full_text_score=1.0,
                vector_similarity_score=0.0,
                combined_relevance_score=1.0,
                retrieval_method="full_text"
            ))
        return matches
