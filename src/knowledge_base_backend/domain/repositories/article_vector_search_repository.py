from typing import Protocol, List, Optional
from src.knowledge_base_backend.domain.value_objects.text_embedding import TextEmbedding
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch

class ArticleVectorSearchRepository(Protocol):
    async def retrieve_articles_by_vector_similarity(
        self, 
        query_embedding: TextEmbedding, 
        instrument_name: Optional[str], 
        minimum_similarity: float, 
        maximum_result_count: int
    ) -> List[RelevantArticleMatch]: ...
