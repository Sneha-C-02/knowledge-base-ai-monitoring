from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import AuthenticationError
from src.knowledge_base_backend.domain.exceptions.article_exceptions import ArticleNotFoundError
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError
from src.knowledge_base_backend.domain.exceptions.monitoring_exceptions import MonitoringError
import logging

logger = logging.getLogger(__name__)

def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": str(exc) or "Authentication failed.",
                    "request_identifier": getattr(request.state, "request_id", "unknown"),
                    "details": None
                }
            }
        )

    @app.exception_handler(ArticleNotFoundError)
    async def not_found_handler(request: Request, exc: ArticleNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "ARTICLE_NOT_FOUND",
                    "message": str(exc),
                    "request_identifier": getattr(request.state, "request_id", "unknown"),
                    "details": None
                }
            }
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(exc),
                    "request_identifier": getattr(request.state, "request_id", "unknown"),
                    "details": None
                }
            }
        )
        
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                    "request_identifier": getattr(request.state, "request_id", "unknown"),
                    "details": None
                }
            }
        )
