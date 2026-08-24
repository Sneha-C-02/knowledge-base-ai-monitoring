from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time
import structlog

logger = structlog.get_logger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Don't log sensitive info
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=process_time,
            request_identifier=getattr(request.state, "request_id", "unknown")
        )
        return response
