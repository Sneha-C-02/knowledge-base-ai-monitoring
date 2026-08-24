from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from src.knowledge_base_backend.infrastructure.database.database_session_factory import async_session_factory
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/live")
async def get_live():
    return {"status": "healthy"}

@router.get("/ready")
async def get_ready():
    # Execute lightweight db query
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "available"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database unavailable")
