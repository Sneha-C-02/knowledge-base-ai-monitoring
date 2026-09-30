from fastapi import Request, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import (
    AuthenticationError,
    InactiveUserError,
    UserNotFoundError,
    InvalidResetTokenError,
    ExpiredResetTokenError,
    PasswordValidationError,
)
from src.knowledge_base_backend.domain.exceptions.article_exceptions import ArticleNotFoundError
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError
from src.knowledge_base_backend.domain.exceptions.monitoring_exceptions import MonitoringError
import logging

logger = logging.getLogger(__name__)

def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InactiveUserError)
    async def inactive_user_handler(request: Request, exc: InactiveUserError):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "USER_INACTIVE",
                    "message": str(exc),
                    "request_identifier": getattr(request.state, "request_id", "unknown"),
                    "details": None,
                }
            },
        )

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(request: Request, exc: UserNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": str(exc),
                    "request_identifier": getattr(request.state, "request_id", "unknown"),
                    "details": None,
                }
            },
        )

    @app.exception_handler(InvalidResetTokenError)
    async def invalid_reset_token_handler(request: Request, exc: InvalidResetTokenError):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_RESET_TOKEN",
                    "message": str(exc),
                    "request_identifier": getattr(request.state, "request_id", "unknown"),
                    "details": None,
                }
            },
        )

    @app.exception_handler(ExpiredResetTokenError)
    async def expired_reset_token_handler(request: Request, exc: ExpiredResetTokenError):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "EXPIRED_RESET_TOKEN",
                    "message": str(exc),
                    "request_identifier": getattr(request.state, "request_id", "unknown"),
                    "details": None,
                }
            },
        )

    @app.exception_handler(PasswordValidationError)
    async def password_validation_error_handler(request: Request, exc: PasswordValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "PASSWORD_VALIDATION_ERROR",
                    "message": str(exc),
                    "request_identifier": getattr(request.state, "request_id", "unknown"),
                    "details": None,
                }
            },
        )

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

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        message = "; ".join(f"{'.'.join(str(loc) for loc in err.get('loc', []))}: {err.get('msg', 'Validation error')}" for err in errors)
        if any("logs" in str(err.get("loc", [])) for err in errors):
            message = "No log files or folder uploaded. At least one log file or folder is required for incident investigation."
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": message,
                    "request_identifier": getattr(request.state, "request_id", "unknown"),
                    "details": jsonable_encoder(errors)
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
