import contextvars
from sqlalchemy.ext.asyncio import AsyncSession

session_context: contextvars.ContextVar[AsyncSession] = contextvars.ContextVar('session_context')

def get_current_session() -> AsyncSession:
    try:
        return session_context.get()
    except LookupError:
        raise RuntimeError('No AsyncSession found in the current context. Did you forget to add the DatabaseSessionMiddleware?')
