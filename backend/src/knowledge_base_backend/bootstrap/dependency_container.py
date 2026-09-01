from dependency_injector import containers, providers
from src.knowledge_base_backend.infrastructure.database.database_session_factory import async_session_factory
from src.knowledge_base_backend.infrastructure.database.session_context import get_current_session
from sqlalchemy.ext.asyncio import async_sessionmaker


from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_article_repository import SqlAlchemyArticleRepository
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_article_vector_search_repository import SqlAlchemyArticleVectorSearchRepository
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_instrument_repository import SqlAlchemyInstrumentRepository
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_activity_repository import SqlAlchemyActivityRepository
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_notification_repository import SqlAlchemyNotificationRepository
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_monitoring_repository import SqlAlchemyMonitoringRepository
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_instrument_memory_repository import SqlAlchemyInstrumentMemoryRepository
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_monitored_log_file_repository import SqlAlchemyMonitoredLogFileRepository
from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_log_event_vector_repository import SqlAlchemyLogEventVectorRepository

from src.knowledge_base_backend.domain.services.log_keyword_extractor import LogKeywordExtractor

from src.knowledge_base_backend.infrastructure.authentication.jwt_authentication_token_service import JwtAuthenticationTokenService
from src.knowledge_base_backend.infrastructure.authentication.argon2_password_hashing_service import Argon2PasswordHashingService

from src.knowledge_base_backend.infrastructure.artificial_intelligence.disabled_embedding_generation_service import DisabledEmbeddingGenerationService
from src.knowledge_base_backend.infrastructure.artificial_intelligence.disabled_answer_generation_service import DisabledAnswerGenerationService
from src.knowledge_base_backend.infrastructure.artificial_intelligence.secure_grounding_context_builder import SecureGroundingContextBuilder
from src.knowledge_base_backend.infrastructure.artificial_intelligence.configurable_monitoring_explanation_generator import ConfigurableMonitoringExplanationGenerator
from src.knowledge_base_backend.infrastructure.artificial_intelligence.configurable_grounded_answer_generator import ConfigurableGroundedAnswerGenerator
from src.knowledge_base_backend.infrastructure.artificial_intelligence.groq_answer_generation_service import GroqAnswerGenerationService
from src.knowledge_base_backend.infrastructure.artificial_intelligence.configurable_embedding_generation_service import ConfigurableEmbeddingGenerationService

from src.knowledge_base_backend.infrastructure.retrieval.pgvector_article_similarity_search_service import PgVectorArticleSimilaritySearchService
from src.knowledge_base_backend.infrastructure.retrieval.weighted_hybrid_article_retrieval_service import WeightedHybridArticleRetrievalService
from src.knowledge_base_backend.infrastructure.retrieval.full_text_article_retrieval_service import FullTextArticleRetrievalService
from src.knowledge_base_backend.infrastructure.retrieval.standard_instrument_recognition_service import StandardInstrumentRecognitionService

from src.knowledge_base_backend.infrastructure.monitoring.standard_log_file_validator import StandardLogFileValidator
from src.knowledge_base_backend.infrastructure.monitoring.plain_text_log_content_parser import PlainTextLogContentParser
from src.knowledge_base_backend.infrastructure.monitoring.rule_based_log_analysis_service import RuleBasedLogAnalysisService
from src.knowledge_base_backend.infrastructure.artificial_intelligence.groq_log_analysis_service import GroqLogAnalysisService
from src.knowledge_base_backend.infrastructure.artificial_intelligence.groq_dashboard_analysis_service import GroqDashboardAnalysisService
from src.knowledge_base_backend.infrastructure.monitoring.local_temporary_file_storage import LocalTemporaryFileStorage
from src.knowledge_base_backend.infrastructure.monitoring.local_persistent_file_storage import LocalPersistentFileStorage
from src.knowledge_base_backend.infrastructure.events.event_bus import EventBus
from src.knowledge_base_backend.infrastructure.system.utc_date_time_provider import UtcDateTimeProvider

from src.knowledge_base_backend.application.use_cases.authenticate_user import AuthenticateUserUseCase
from src.knowledge_base_backend.application.use_cases.list_knowledge_base_articles import ListKnowledgeBaseArticlesUseCase
from src.knowledge_base_backend.application.use_cases.get_knowledge_base_article import GetKnowledgeBaseArticleUseCase
from src.knowledge_base_backend.application.use_cases.submit_support_query import SubmitSupportQueryUseCase
from src.knowledge_base_backend.application.use_cases.analyze_uploaded_logs import AnalyzeUploadedLogsUseCase
from src.knowledge_base_backend.application.use_cases.analyze_logs_with_memory import AnalyzeLogsWithMemoryUseCase
from src.knowledge_base_backend.application.use_cases.get_dashboard_statistics import GetDashboardStatisticsUseCase
from src.knowledge_base_backend.application.use_cases.list_activities import ListActivitiesUseCase
from src.knowledge_base_backend.application.use_cases.create_activity import CreateActivityUseCase
from src.knowledge_base_backend.application.use_cases.list_notifications import ListNotificationsUseCase
from src.knowledge_base_backend.application.services.continuous_monitoring_service import ContinuousMonitoringService

from src.knowledge_base_backend.configuration.application_settings import settings

class ApplicationContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["src.knowledge_base_backend.presentation.api.routers"])
    
    # Session
    db_session = providers.Callable(get_current_session)
    
    # Repositories
    article_repository = providers.Factory(SqlAlchemyArticleRepository, session=db_session)
    article_vector_repository = providers.Factory(SqlAlchemyArticleVectorSearchRepository, session=db_session)
    instrument_repository = providers.Factory(SqlAlchemyInstrumentRepository, session=db_session)
    user_repository = providers.Factory(SqlAlchemyUserRepository, session=db_session)
    activity_repository = providers.Factory(SqlAlchemyActivityRepository, session=db_session)
    notification_repository = providers.Factory(SqlAlchemyNotificationRepository, session=db_session)
    monitoring_repository = providers.Factory(SqlAlchemyMonitoringRepository, session=db_session)
    instrument_memory_repository = providers.Factory(SqlAlchemyInstrumentMemoryRepository, session=db_session)
    monitored_log_file_repository = providers.Factory(SqlAlchemyMonitoredLogFileRepository, session=db_session)
    log_event_vector_repository = providers.Factory(SqlAlchemyLogEventVectorRepository, session=db_session)

    # Core Services
    date_time_provider = providers.Singleton(UtcDateTimeProvider)
    password_hashing_service = providers.Singleton(Argon2PasswordHashingService)
    token_service = providers.Singleton(JwtAuthenticationTokenService)
    event_bus = providers.Singleton(EventBus)
    
    # AI Providers Configuration
    if settings.embedding_provider == "disabled":
        embedding_generation_service = providers.Singleton(DisabledEmbeddingGenerationService)
    else:
        embedding_generation_service = providers.Singleton(
            ConfigurableEmbeddingGenerationService, 
            api_key=settings.embedding_provider_api_key, 
            model_name=settings.embedding_model_name, 
            dimension=settings.embedding_dimension
        )

    if settings.answer_generation_provider == "disabled":
        answer_generation_service = providers.Singleton(DisabledAnswerGenerationService)
    elif settings.answer_generation_provider == "groq":
        answer_generation_service = providers.Singleton(
            GroqAnswerGenerationService,
            api_key=settings.answer_generation_provider_api_key,
            model_name=settings.answer_generation_model_name,
            timeout=settings.answer_generation_timeout_seconds,
            calls_per_minute=settings.groq_rate_limit_calls_per_minute
        )
    else:
        answer_generation_service = providers.Singleton(
            ConfigurableGroundedAnswerGenerator,
            api_key=settings.answer_generation_provider_api_key,
            model_name=settings.answer_generation_model_name,
            timeout=settings.answer_generation_timeout_seconds
        )
        
    monitoring_explanation_service = providers.Singleton(ConfigurableMonitoringExplanationGenerator)
    
    # Retrieval Services
    article_similarity_search_service = providers.Singleton(
        PgVectorArticleSimilaritySearchService, vector_repository=article_vector_repository
    )
    
    if settings.vector_search_enabled:
        hybrid_retrieval_service = providers.Singleton(
            WeightedHybridArticleRetrievalService,
            article_repository=article_repository,
            vector_repository=article_vector_repository,
            embedding_service=embedding_generation_service,
            log_event_vector_repository=log_event_vector_repository
        )
    else:
        hybrid_retrieval_service = providers.Singleton(
            FullTextArticleRetrievalService,
            article_repository=article_repository
        )
        
    instrument_recognition_service = providers.Singleton(
        StandardInstrumentRecognitionService, instrument_repository=instrument_repository
    )
    grounding_context_builder = providers.Singleton(SecureGroundingContextBuilder)
    
    # Monitoring Services
    log_validator = providers.Singleton(StandardLogFileValidator)
    temporary_file_storage = providers.Singleton(LocalTemporaryFileStorage)
    persistent_file_storage = providers.Singleton(LocalPersistentFileStorage)
    log_parser = providers.Singleton(PlainTextLogContentParser)
    log_keyword_extractor = providers.Singleton(LogKeywordExtractor)
    
    if settings.answer_generation_provider == "groq":
        log_analysis_service = providers.Singleton(
            GroqLogAnalysisService,
            api_key=settings.answer_generation_provider_api_key,
            model_name=settings.answer_generation_model_name,
            timeout=settings.answer_generation_timeout_seconds,
            calls_per_minute=settings.groq_rate_limit_calls_per_minute,
            parser=log_parser,
            date_time_provider=date_time_provider,
            retrieval_service=hybrid_retrieval_service
        )
    else:
        log_analysis_service = providers.Singleton(
            RuleBasedLogAnalysisService, parser=log_parser, date_time_provider=date_time_provider
        )
    
    # Dashboard Analysis Service (Groq-powered, reads full logs with memory)
    if settings.answer_generation_provider == "groq":
        dashboard_analysis_service = providers.Singleton(
            GroqDashboardAnalysisService,
            api_key=settings.answer_generation_provider_api_key,
            model_name=settings.answer_generation_model_name,
            timeout=settings.answer_generation_timeout_seconds,
            calls_per_minute=settings.groq_rate_limit_calls_per_minute,
            tokens_per_minute=settings.groq_rate_limit_tokens_per_minute,
            max_analyzed_log_lines=settings.max_analyzed_log_lines,
            max_ai_chunks=settings.max_ai_chunks,
            log_reduction_context_lines=settings.log_reduction_context_lines,
            log_reduction_tail_lines=settings.log_reduction_tail_lines
        )
    else:
        dashboard_analysis_service = providers.Singleton(
            GroqDashboardAnalysisService,
            api_key=settings.answer_generation_provider_api_key or "",
            model_name=settings.answer_generation_model_name or "llama3-8b-8192",
            timeout=settings.answer_generation_timeout_seconds,
            calls_per_minute=settings.groq_rate_limit_calls_per_minute,
            tokens_per_minute=settings.groq_rate_limit_tokens_per_minute,
            max_analyzed_log_lines=settings.max_analyzed_log_lines,
            max_ai_chunks=settings.max_ai_chunks,
            log_reduction_context_lines=settings.log_reduction_context_lines,
            log_reduction_tail_lines=settings.log_reduction_tail_lines
        )
    
    # Use Cases
    authenticate_user_use_case = providers.Factory(
        AuthenticateUserUseCase,
        user_repository=user_repository,
        password_hashing_service=password_hashing_service,
        token_service=token_service,
        activity_repository=activity_repository,
        date_time_provider=date_time_provider
    )
    
    list_knowledge_base_articles_use_case = providers.Factory(
        ListKnowledgeBaseArticlesUseCase, article_repository=article_repository
    )
    
    get_knowledge_base_article_use_case = providers.Factory(
        GetKnowledgeBaseArticleUseCase, article_repository=article_repository
    )
    
    submit_support_query_use_case = providers.Factory(
        SubmitSupportQueryUseCase,
        retrieval_service=hybrid_retrieval_service,
        answer_generator=answer_generation_service,
        context_builder=grounding_context_builder,
        instrument_recognition=instrument_recognition_service
    )
    
    analyze_uploaded_logs_use_case = providers.Factory(
        AnalyzeUploadedLogsUseCase,
        validator=log_validator,
        storage=temporary_file_storage,
        analysis_service=log_analysis_service,
        repository=monitoring_repository,
        notification_repository=notification_repository,
        keyword_extractor=log_keyword_extractor,
        embedding_service=embedding_generation_service,
        log_event_vector_repository=log_event_vector_repository
    )
    
    analyze_logs_with_memory_use_case = providers.Factory(
        AnalyzeLogsWithMemoryUseCase,
        validator=log_validator,
        storage=persistent_file_storage,
        ai_service=dashboard_analysis_service,
        memory_repository=instrument_memory_repository,
        instrument_repository=instrument_repository,
        notification_repository=notification_repository,
        monitored_file_repository=monitored_log_file_repository,
        date_time_provider=date_time_provider
    )
    
    get_dashboard_statistics_use_case = providers.Factory(
        GetDashboardStatisticsUseCase,
        article_repository=article_repository,
        monitoring_repository=monitoring_repository,
        activity_repository=activity_repository
    )
    
    create_activity_use_case = providers.Factory(
        CreateActivityUseCase,
        activity_repository=activity_repository,
        date_time_provider=date_time_provider
    )

    list_activities_use_case = providers.Factory(
        ListActivitiesUseCase, activity_repository=activity_repository
    )
    
    list_notifications_use_case = providers.Factory(
        ListNotificationsUseCase, notification_repository=notification_repository
    )

    # Background Services
    continuous_monitoring_service = providers.Singleton(
        ContinuousMonitoringService,
        session_factory=providers.Object(None), # Will be set in application factory
        storage=persistent_file_storage,
        analyze_use_case_factory=analyze_logs_with_memory_use_case.provider,
        event_bus=event_bus,
        polling_interval_seconds=15
    )
