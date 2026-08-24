from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.knowledge_base_backend.configuration.application_settings import settings
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer
from src.knowledge_base_backend.presentation.api.middleware.request_identifier_middleware import RequestIdentifierMiddleware
from src.knowledge_base_backend.presentation.api.middleware.request_logging_middleware import RequestLoggingMiddleware
from src.knowledge_base_backend.presentation.api.exception_handlers.application_exception_handlers import add_exception_handlers

from src.knowledge_base_backend.presentation.api.routers import authentication_router
from src.knowledge_base_backend.presentation.api.routers import knowledge_base_router
from src.knowledge_base_backend.presentation.api.routers import support_router
from src.knowledge_base_backend.presentation.api.routers import monitoring_router
from src.knowledge_base_backend.presentation.api.routers import system_router
from src.knowledge_base_backend.presentation.api.routers import health_router
from src.knowledge_base_backend.bootstrap.logging_configuration import configure_logging

def create_application() -> FastAPI:
    configure_logging()
    
    container = ApplicationContainer()
    
    app = FastAPI(
        title=settings.application_name,
        version="0.1.0"
    )
    
    app.container = container
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdentifierMiddleware)
    
    add_exception_handlers(app)
    
    api_prefix = settings.api_prefix
    app.include_router(authentication_router.router, prefix=api_prefix)
    app.include_router(knowledge_base_router.router, prefix=api_prefix)
    app.include_router(support_router.router, prefix=api_prefix)
    app.include_router(monitoring_router.router, prefix=api_prefix)
    app.include_router(system_router.router, prefix=api_prefix)
    app.include_router(health_router.router, prefix=api_prefix)
    
    return app
