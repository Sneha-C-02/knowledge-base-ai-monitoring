import asyncio
import os
import sys
from sqlalchemy import text
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add the backend directory to the python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.knowledge_base_backend.configuration.application_settings import settings
from src.knowledge_base_backend.infrastructure.database.models.article_model import ArticleModel
from src.knowledge_base_backend.infrastructure.database.models.instrument_model import InstrumentModel
from sqlalchemy import select

async def main():
    print("Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Model loaded.")

    engine = create_async_engine(settings.database_connection_url, echo=False)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        # 1. Ensure extension exists and column exists
        print("Ensuring pgvector extension and article_embedding column exist...")
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        try:
            await session.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS article_embedding vector(384);"))
            await session.commit()
        except Exception as e:
            print(f"Note: Column might already exist or error: {e}")
            await session.rollback()

        # 2. Fetch articles that don't have embeddings
        print("Fetching articles without embeddings...")
        query = select(ArticleModel).where(ArticleModel.article_embedding.is_(None))
        result = await session.execute(query)
        articles = result.scalars().all()
        
        total = len(articles)
        print(f"Found {total} articles needing embeddings.")

        if total == 0:
            print("All articles have embeddings. Exiting.")
            return

        # We will only do 1 batch of 10 for demonstration/speed right now if there are many, or just process them quickly.
        batch_size = 100
        for i in range(0, total, batch_size): # Process all articles
            batch = articles[i:i+batch_size]
            print(f"Processing batch {i} to {i+len(batch)} of {total}...")
            
            texts = [f"{a.title}\n{a.searchable_content}" for a in batch]
            embeddings = model.encode(texts)
            
            for j, article in enumerate(batch):
                embedding_list = embeddings[j].tolist()
                await session.execute(
                    text("UPDATE articles SET article_embedding = :emb WHERE id = :id"),
                    {"emb": f"[{','.join(map(str, embedding_list))}]", "id": article.id}
                )
            
            await session.commit()
            print(f"Committed batch {i} to {i+len(batch)}.")

    print("Finished generating embeddings (capped at 500 for demonstration).")

if __name__ == '__main__':
    asyncio.run(main())
