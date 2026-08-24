from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class ApplicationSettings(BaseSettings):
    application_name: str = "Knowledge Base AI Support Backend"
    application_environment: str = "development"
    api_prefix: str = "/api"
    api_host: str = "0.0.0.0"
    api_port: int = 3000
    log_level: str = "INFO"

    database_connection_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_connection_timeout_seconds: int = 30

    jwt_secret_key: str
    jwt_signing_algorithm: str = "HS256"
    jwt_access_token_expiration_minutes: int = 60

    allowed_frontend_origins: str = "http://localhost:5173"
    maximum_article_page_size: int = 100
    default_article_page_size: int = 100

    maximum_log_file_count: int = 10
    maximum_log_file_size_bytes: int = 20971520
    allowed_log_file_extensions: str = ".log,.txt"

    ai_provider: str = "disabled"
    ai_provider_api_key: Optional[str] = None
    ai_model_name: Optional[str] = None
    ai_request_timeout_seconds: int = 60
    
    temporary_file_directory: str = "temporary_uploads"

    vector_search_enabled: bool = False
    article_embedding_column_name: str = "article_embedding"
    vector_distance_metric: str = "cosine"
    vector_similarity_threshold: float = 0.35
    vector_search_result_limit: int = 10

    full_text_search_weight: float = 0.35
    vector_search_weight: float = 0.65
    instrument_match_boost: float = 0.10
    exact_article_id_boost: float = 1.0
    entity_match_boost: float = 0.3
    intent_match_boost: float = 0.2
    minimum_hybrid_score_threshold: float = 0.30

    embedding_provider: str = "disabled"
    embedding_provider_api_key: Optional[str] = None
    embedding_model_name: Optional[str] = None
    embedding_dimension: Optional[int] = None

    answer_generation_provider: str = "disabled"
    answer_generation_provider_api_key: Optional[str] = None
    answer_generation_model_name: Optional[str] = None
    answer_generation_timeout_seconds: int = 60
    
    groq_rate_limit_calls_per_minute: int = 30

    monitoring_explanation_provider: str = "disabled"
    monitoring_explanation_model_name: Optional[str] = None

    maximum_model_context_articles: int = 5
    maximum_model_context_characters: int = 20000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_frontend_origins.split(",") if origin.strip()]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.allowed_log_file_extensions.split(",") if ext.strip()]

settings = ApplicationSettings()
