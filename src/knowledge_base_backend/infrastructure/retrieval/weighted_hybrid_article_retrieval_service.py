from typing import List, Optional
from src.knowledge_base_backend.domain.services.hybrid_article_retrieval_service import HybridArticleRetrievalService
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch
from src.knowledge_base_backend.domain.repositories.article_repository import ArticleRepository
from src.knowledge_base_backend.domain.repositories.article_vector_search_repository import ArticleVectorSearchRepository
from src.knowledge_base_backend.domain.services.embedding_generation_service import EmbeddingGenerationService
from src.knowledge_base_backend.domain.value_objects.article_search_criteria import ArticleSearchCriteria

class WeightedHybridArticleRetrievalService(HybridArticleRetrievalService):
    def __init__(
        self, 
        article_repository: ArticleRepository,
        vector_repository: ArticleVectorSearchRepository,
        embedding_service: EmbeddingGenerationService
    ) -> None:
        self.article_repository = article_repository
        self.vector_repository = vector_repository
        self.embedding_service = embedding_service

    async def retrieve_relevant_articles(
        self, query: str, instrument_name: Optional[str], limit: int
    ) -> List[RelevantArticleMatch]:
        try:
            query_embedding = await self.embedding_service.generate_text_embedding(query)
            # Simulated return
            return []
        except Exception:
            # Fallback to full text
            criteria = ArticleSearchCriteria(search_query=query, instrument_name=instrument_name)
            articles = await self.article_repository.search_articles_by_full_text(criteria, limit)
            return [
                RelevantArticleMatch(
                    article=a,
                    matched_instruments=a.instruments,
                    full_text_score=1.0,
                    vector_similarity_score=0.0,
                    combined_relevance_score=1.0,
                    retrieval_method="full_text"
                ) for a in articles
            ]
