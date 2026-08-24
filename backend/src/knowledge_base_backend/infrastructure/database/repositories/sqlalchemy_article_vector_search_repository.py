from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from sqlalchemy import select, text
from src.knowledge_base_backend.domain.repositories.article_vector_search_repository import ArticleVectorSearchRepository
from src.knowledge_base_backend.domain.value_objects.text_embedding import TextEmbedding
from src.knowledge_base_backend.domain.value_objects.relevant_article_match import RelevantArticleMatch
from src.knowledge_base_backend.infrastructure.database.models.article_model import ArticleModel
from src.knowledge_base_backend.infrastructure.database.models.instrument_model import InstrumentModel
from src.knowledge_base_backend.domain.entities.knowledge_base_article import KnowledgeBaseArticle
from sqlalchemy.orm import selectinload

class SqlAlchemyArticleVectorSearchRepository(ArticleVectorSearchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        
    def _map_to_domain(self, model: ArticleModel) -> KnowledgeBaseArticle:
        instruments = [inst.name for inst in model.instruments] if model.instruments else []
        return KnowledgeBaseArticle(
            id=model.article_number,
            database_id=model.id,
            article_number=model.article_number,
            title=model.title,
            url=model.url,
            searchable_content=model.searchable_content,
            instruments=instruments,
            last_updated=model.source_updated_at
        )
        
    async def retrieve_articles_by_vector_similarity(
        self, 
        query_embedding: TextEmbedding, 
        instrument_name: Optional[str], 
        minimum_similarity: float, 
        maximum_result_count: int
    ) -> List[RelevantArticleMatch]:
        
        emb_list = list(query_embedding.values)
        
        query = select(
            ArticleModel,
            ArticleModel.article_embedding.cosine_distance(emb_list).label("distance")
        ).options(selectinload(ArticleModel.instruments))
        
        if instrument_name:
            query = query.join(ArticleModel.instruments).where(InstrumentModel.name == instrument_name)
            
        query = query.where(
            ArticleModel.article_embedding.cosine_distance(emb_list) <= (1.0 - minimum_similarity)
        ).order_by(
            ArticleModel.article_embedding.cosine_distance(emb_list)
        ).limit(maximum_result_count)
        
        try:
            await self.session.execute(text('SET LOCAL hnsw.ef_search = 200;'))
            result = await self.session.execute(query)
            rows = result.all()
            
            matches = []
            for row in rows:
                article_model = row[0]
                distance = row[1]
                similarity = 1.0 - float(distance) if distance is not None else 0.0
                
                domain_article = self._map_to_domain(article_model)
                
                matches.append(
                    RelevantArticleMatch(
                        article=domain_article,
                        matched_instruments=domain_article.instruments,
                        full_text_score=0.0,
                        vector_similarity_score=similarity,
                        combined_relevance_score=similarity,
                        retrieval_method="vector"
                    )
                )
            return matches
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
