from typing import Protocol, List, Optional
from src.knowledge_base_backend.domain.value_objects.text_embedding import TextEmbedding
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch

class ArticleSimilaritySearchService(Protocol):
    async def retrieve_semantically_similar_articles(
        self, 
        embedding: TextEmbedding, 
        instrument_name: Optional[str], 
        similarity_threshold: float, 
        result_limit: int
    ) -> List[RelevantArticleMatch]: ...
