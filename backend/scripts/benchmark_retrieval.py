import asyncio
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from src.knowledge_base_backend.configuration.application_settings import settings
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_article_repository import SqlAlchemyArticleRepository
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_article_vector_search_repository import SqlAlchemyArticleVectorSearchRepository
from src.knowledge_base_backend.infrastructure.artificial_intelligence.configurable_embedding_generation_service import ConfigurableEmbeddingGenerationService
from src.knowledge_base_backend.domain.value_objects.article_search_criteria import ArticleSearchCriteria

async def benchmark():
    engine = create_async_engine(settings.database_connection_url, echo=False)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    embedding_service = ConfigurableEmbeddingGenerationService()
    
    query = "What is the procedure for the Waters P-200A PM Kit?"
    
    # Warmup connection
    async with async_session() as session:
        await session.execute(text("SELECT 1"))
        
    runs = 3
    emb_times = []
    ft_times = []
    vec_times = []
    
    async with async_session() as session:
        article_repo = SqlAlchemyArticleRepository(session)
        vector_repo = SqlAlchemyArticleVectorSearchRepository(session)
        
        for _ in range(runs):
            # 1. Query Embedding
            t0 = time.perf_counter()
            query_embedding = await embedding_service.generate_text_embedding(query)
            t1 = time.perf_counter()
            emb_times.append((t1 - t0) * 1000)
            
            # 2. Full Text
            criteria = ArticleSearchCriteria(search_query=query, instrument_name=None)
            t2 = time.perf_counter()
            ft_results = await article_repo.search_articles_by_full_text(criteria, limit=15)
            t3 = time.perf_counter()
            ft_times.append((t3 - t2) * 1000)
            
            # 3. Vector
            t4 = time.perf_counter()
            vec_results = await vector_repo.retrieve_articles_by_vector_similarity(
                query_embedding=query_embedding,
                instrument_name=None,
                minimum_similarity=settings.vector_similarity_threshold,
                maximum_result_count=15
            )
            t5 = time.perf_counter()
            vec_times.append((t5 - t4) * 1000)
            
    print("=== BENCHMARK ===")
    print(f"Query embedding: {sum(emb_times)/runs:.2f} ms")
    print(f"Full-text search: {sum(ft_times)/runs:.2f} ms")
    print(f"Vector search: {sum(vec_times)/runs:.2f} ms")

if __name__ == '__main__':
    asyncio.run(benchmark())
