import asyncio
import os
import sys
from sqlalchemy import text

sys.path.insert(0, '/app')

from src.knowledge_base_backend.infrastructure.database.database_session_factory import engine

async def migrate():
    print("Migrating activities table...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE system_activities ADD COLUMN severity VARCHAR"))
            print("Added severity column.")
        except Exception as e:
            print(f"Skipped severity: {e}")
        try:
            await conn.execute(text("ALTER TABLE system_activities ADD COLUMN metadata_payload JSON"))
            print("Added metadata_payload column.")
        except Exception as e:
            print(f"Skipped metadata: {e}")

asyncio.run(migrate())
