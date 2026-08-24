from typing import List, Optional
from src.knowledge_base_backend.domain.services.article_similarity_search_service import ArticleSimilaritySearchService
from src.knowledge_base_backend.domain.value_objects.text_embedding import TextEmbedding
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch
from src.knowledge_base_backend.domain.repositories.article_vector_search_repository import ArticleVectorSearchRepository

class PgVectorArticleSimilaritySearchService(ArticleSimilaritySearchService):
    def __init__(self, vector_repository: ArticleVectorSearchRepository) -> None:
        self.vector_repository = vector_repository
        
    async def retrieve_semantically_similar_articles(
        self, 
        embedding: TextEmbedding, 
        instrument_name: Optional[str], 
        similarity_threshold: float, 
        result_limit: int
    ) -> List[RelevantArticleMatch]:
        return await self.vector_repository.retrieve_articles_by_vector_similarity(
            query_embedding=embedding,
            instrument_name=instrument_name,
            minimum_similarity=similarity_threshold,
            maximum_result_count=result_limit
        )
