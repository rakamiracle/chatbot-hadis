from pydantic_settings import BaseSettings

class Settings(BaseSettings):
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
    VECTOR_SEARCH_MODE: str = 'normal'
    VECTOR_SEARCH_THRESHOLD: float = 0.40
    ENABLE_FALLBACK_SEARCH: bool = True
    FALLBACK_THRESHOLD: float = 0.20
    MIN_RESULTS_FOR_FALLBACK: int = 3
    
    # 🔥 Query Expansion Configuration
    ENABLE_QUERY_EXPANSION: bool = True
    EXPAND_WITH_RELATED_CONCEPTS: bool = True
    GENERATE_FALLBACK_SUGGESTIONS: bool = True
    
    # 🔥 LLM Configuration (IMPROVED v2)
    LLM_TIMEOUT_SECONDS: int = 45  # INCREASED: 30 → 45
    LLM_MAX_TOKENS: int = 300  # INCREASED: 200 → 300
    LLM_TEMPERATURE: float = 0.15  # INCREASED: 0.05 → 0.15 (lebih berani generate)
    LLM_TOP_P: float = 0.7  # INCREASED: 0.6 → 0.7
    LLM_TOP_K: int = 20  # INCREASED: 10 → 20
    
    # 🔥 LLM Validation Configuration
    LLM_MIN_CONFIDENCE: float = 0.5  # REDUCED: 0.6 → 0.5 (less strict)
    LLM_MIN_ANSWER_LENGTH: int = 20  # Minimum words required
    LLM_MAX_ANSWER_LENGTH: int = 1500  # INCREASED: 800 → 1500
    
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
    
    # 🔥 NEW: Disclaimer Configuration
    SHOW_DISCLAIMER_ONLY_LOW_CONFIDENCE: bool = True  # Show disclaimer hanya jika confidence < 0.5
    DISCLAIMER_MIN_CONFIDENCE_THRESHOLD: float = 0.5  # Threshold untuk show disclaimer
    
    class Config:
        env_file = ".env"

      # 🔥 NEW: Cache Configuration
    ENABLE_SESSION_ISOLATION: bool = True
    CACHE_TTL_MINUTES: int = 30  # Dikurangi dari 60 ke 30 untuk lebih fresh
    ENABLE_GLOBAL_CACHE: bool = True  # Allow common patterns to be shared

settings = Settings()