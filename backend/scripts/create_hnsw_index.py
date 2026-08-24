import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.knowledge_base_backend.configuration.application_settings import settings

async def create_index():
    engine = create_async_engine(settings.database_connection_url, echo=False)
    # create_index concurrently requires execution outside of a transaction block in standard python drivers, 
    # so we must use isolation_level="AUTOCOMMIT"
    engine = engine.execution_options(isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        print("Creating HNSW Index...")
        await conn.execute(text("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_embedding_hnsw ON articles USING hnsw (article_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"))
        print("HNSW Index Created Successfully.")
        
        # Verify index exists
        res = await conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'articles' AND indexname = 'idx_articles_embedding_hnsw';"))
        for row in res:
            print(f"Verified: {row[0]} -> {row[1]}")

if __name__ == '__main__':
    asyncio.run(create_index())
