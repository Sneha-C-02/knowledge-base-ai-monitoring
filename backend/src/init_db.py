import asyncio
import os
import sys
from sqlalchemy import text
from datetime import datetime, timezone

sys.path.insert(0, '/app')

from src.knowledge_base_backend.infrastructure.database.database_session_factory import engine, async_session_factory
from src.knowledge_base_backend.infrastructure.database.models.activity_model import *
from src.knowledge_base_backend.infrastructure.database.models.article_model import *
from src.knowledge_base_backend.infrastructure.database.models.instrument_model import *
from src.knowledge_base_backend.infrastructure.database.models.monitoring_model import *
from src.knowledge_base_backend.infrastructure.database.models.notification_model import *
from src.knowledge_base_backend.infrastructure.database.models.user_model import UserModel

Base = UserModel.metadata

async def init_db():
    print("Connecting to database...")
    async with engine.begin() as conn:
        print("Creating tables...")
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            print(f"Vector extension skipped: {e}")
            pass
        await conn.run_sync(Base.create_all)
        print("Tables created.")
    
    from passlib.context import CryptContext
    from sqlalchemy import select
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async with async_session_factory() as session:
        result = await session.execute(select(UserModel).where(UserModel.username == 'admin'))
        user = result.scalars().first()
        if not user:
            print("Creating admin user...")
            new_user = UserModel(
                username='admin',
                display_name='Admin User',
                password_hash=pwd_context.hash('password123'),
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(new_user)
            await session.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")

if __name__ == "__main__":
    asyncio.run(init_db())
