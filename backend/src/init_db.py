import asyncio
import os
import sys
from sqlalchemy import text
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, '/app')

from src.knowledge_base_backend.infrastructure.database.database_session_factory import engine, async_session_factory
from src.knowledge_base_backend.infrastructure.database.sqlalchemy_base import Base
from src.knowledge_base_backend.infrastructure.database.models.activity_model import *
from src.knowledge_base_backend.infrastructure.database.models.article_model import *
from src.knowledge_base_backend.infrastructure.database.models.instrument_model import InstrumentModel
from src.knowledge_base_backend.infrastructure.database.models.monitoring_model import *
from src.knowledge_base_backend.infrastructure.database.models.notification_model import *
from src.knowledge_base_backend.infrastructure.database.models.instrument_memory_model import InstrumentMemoryModel
from src.knowledge_base_backend.infrastructure.database.models.monitored_log_file_model import MonitoredLogFileModel
from src.knowledge_base_backend.infrastructure.database.models.user_model import UserModel


async def init_db():
    print("Connecting to database...")
    async with engine.begin() as conn:
        print("Creating tables...")
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            print(f"Vector extension skipped: {e}")
            pass
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created.")
    
    import bcrypt
    from sqlalchemy import select
    
    admin_password_hash = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode('utf-8')
    
    async with async_session_factory() as session:
        result = await session.execute(select(UserModel).where(UserModel.username == 'admin'))
        user = result.scalars().first()
        if not user:
            print("Creating admin user...")
            new_user = UserModel(
                username='admin',
                display_name='Admin User',
                password_hash=admin_password_hash,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(new_user)
            await session.commit()
            print("Admin user created.")
        # Seed default instruments if none exist
        inst_res = await session.execute(select(InstrumentModel))
        if not inst_res.scalars().first():
            print("Creating sample instruments...")
            instruments = [
                InstrumentModel(id=1, name="Instrument Alpha (Core Server)"),
                InstrumentModel(id=2, name="Instrument Beta (Data Pipeline)"),
                InstrumentModel(id=3, name="Instrument Gamma (Auth Service)"),
            ]
            session.add_all(instruments)
            await session.commit()
            print("Sample instruments created.")
        else:
            print("Instruments already exist.")

if __name__ == "__main__":
    asyncio.run(init_db())
