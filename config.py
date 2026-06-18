from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ✅ Pydantic v2 config (pengganti class Config)
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",          # ✅ env var tambahan (mis. ONLY_DOCUMENT_ID) tidak bikin crash
        case_sensitive=False,
    )

    # ✅ Focus mode (optional)
    only_document_id: Optional[int] = None

    # Database
    DATABASE_URL: str

    # LLM & Embeddings
    OLLAMA_MODEL: str
    EMBEDDING_MODEL: str

    # Application
    APP_PORT: int = 8000
    SECRET_KEY: str
    UPLOAD_DIR: str = "uploads"

    # Search & Retrieval
    TOP_K_RESULTS: int = 5

    # 🔥 Vector Search Configuration
    VECTOR_SEARCH_MODE: str = "normal"
    VECTOR_SEARCH_THRESHOLD: float = 0.40
    ENABLE_FALLBACK_SEARCH: bool = True
    FALLBACK_THRESHOLD: float = 0.20
    MIN_RESULTS_FOR_FALLBACK: int = 3

    # 🔥 Query Expansion Configuration
    ENABLE_QUERY_EXPANSION: bool = True
    EXPAND_WITH_RELATED_CONCEPTS: bool = True
    GENERATE_FALLBACK_SUGGESTIONS: bool = True

    # 🔥 LLM Configuration (IMPROVED v2)
    LLM_TIMEOUT_SECONDS: int = 45
    LLM_MAX_TOKENS: int = 300
    LLM_TEMPERATURE: float = 0.15
    LLM_TOP_P: float = 0.7
    LLM_TOP_K: int = 20

    # 🔥 LLM Validation Configuration
    LLM_MIN_CONFIDENCE: float = 0.5
    LLM_MIN_ANSWER_LENGTH: int = 20
    LLM_MAX_ANSWER_LENGTH: int = 1500

    # Performance Settings
    BATCH_SIZE: int = 50
    EMBEDDING_BATCH_SIZE: int = 32
    DB_POOL_SIZE: int = 10
    CACHE_TTL_MINUTES: int = 30

    # 🔥 Logging & Monitoring
    DETAILED_LOGGING: bool = True
    LOG_SIMILARITY_SCORES: bool = True
    LOG_METADATA_QUALITY: bool = True

    # 🔥 Feature Flags
    ENABLE_ARABIC_DETECTION: bool = True
    ENABLE_METADATA_EXTRACTION: bool = True
    ENABLE_SOURCE_RANKING: bool = True
    ENFORCE_SOURCE_VALIDATION: bool = True

    # 🔥 Disclaimer Configuration
    SHOW_DISCLAIMER_ONLY_LOW_CONFIDENCE: bool = True
    DISCLAIMER_MIN_CONFIDENCE_THRESHOLD: float = 0.5

    # 🔥 Cache Configuration
    ENABLE_SESSION_ISOLATION: bool = True
    ENABLE_GLOBAL_CACHE: bool = True


settings = Settings()
