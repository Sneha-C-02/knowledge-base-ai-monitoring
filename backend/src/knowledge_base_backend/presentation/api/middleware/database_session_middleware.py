from starlette.middleware.base import BaseHTTPMiddleware
from src.knowledge_base_backend.infrastructure.database.database_session_factory import async_session_factory
from src.knowledge_base_backend.infrastructure.database.session_context import session_context

class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        async with async_session_factory() as session:
            token = session_context.set(session)
            try:
                response = await call_next(request)
                await session.commit()
                return response
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                session_context.reset(token)
