from dependency_injector import providers
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.knowledge_base_backend.configuration.application_settings import settings
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer
from src.knowledge_base_backend.presentation.api.middleware.request_identifier_middleware import RequestIdentifierMiddleware
from src.knowledge_base_backend.presentation.api.middleware.request_logging_middleware import RequestLoggingMiddleware
from src.knowledge_base_backend.presentation.api.middleware.database_session_middleware import DatabaseSessionMiddleware
from src.knowledge_base_backend.infrastructure.database.database_session_factory import async_session_factory
from contextlib import asynccontextmanager

from src.knowledge_base_backend.presentation.api.exception_handlers.application_exception_handlers import add_exception_handlers

from src.knowledge_base_backend.presentation.api.routers import authentication_router
from src.knowledge_base_backend.presentation.api.routers import knowledge_base_router
from src.knowledge_base_backend.presentation.api.routers import support_router
from src.knowledge_base_backend.presentation.api.routers import monitoring_router
from src.knowledge_base_backend.presentation.api.routers import system_router
from src.knowledge_base_backend.presentation.api.routers import health_router
from src.knowledge_base_backend.presentation.api.routers import dashboard_router
from src.knowledge_base_backend.bootstrap.logging_configuration import configure_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup
    monitoring_service = app.container.continuous_monitoring_service()
    monitoring_service.start()
    
    yield
    
    # Teardown
    monitoring_service.stop()

def create_application() -> FastAPI:
    configure_logging()
    
    container = ApplicationContainer()
    container.continuous_monitoring_service.override(
        providers.Singleton(
            container.continuous_monitoring_service.cls,
            session_factory=async_session_factory,
            storage=container.persistent_file_storage,
            analyze_use_case_factory=container.analyze_logs_with_memory_use_case.provider,
            event_bus=container.event_bus,
            polling_interval_seconds=15
        )
    )
    
    app = FastAPI(
        title=settings.application_name,
        version="0.1.0",
        lifespan=lifespan
    )
    
    app.container = container
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(DatabaseSessionMiddleware)
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
    app.include_router(dashboard_router.router, prefix=api_prefix)
    
    return app
