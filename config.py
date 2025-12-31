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
    
    # 🔥 NEW: Vector Search Configuration
    VECTOR_SEARCH_MODE: str = 'normal'  # 'strict', 'normal', 'lenient', 'debug'
    VECTOR_SEARCH_THRESHOLD: float = 0.40  # Default threshold (can be overridden by mode)
    ENABLE_FALLBACK_SEARCH: bool = True  # Enable automatic fallback to lenient threshold
    FALLBACK_THRESHOLD: float = 0.20  # Fallback threshold if initial search returns < 3 results
    MIN_RESULTS_FOR_FALLBACK: int = 3  # Trigger fallback if fewer than this many results
    
    # 🔥 NEW: Query Expansion Configuration
    ENABLE_QUERY_EXPANSION: bool = True  # Enable query expansion for generic queries
    EXPAND_WITH_RELATED_CONCEPTS: bool = True  # Add related concepts to search
    GENERATE_FALLBACK_SUGGESTIONS: bool = True  # Generate suggestions if no results
    
    # 🔥 NEW: LLM Configuration
    LLM_TIMEOUT_SECONDS: int = 30  # Timeout for LLM generation
    LLM_MAX_TOKENS: int = 300  # Maximum tokens in response
    LLM_TEMPERATURE: float = 0.1  # Temperature (lower = more deterministic)
    
    # Performance Settings
    BATCH_SIZE: int = 50
    EMBEDDING_BATCH_SIZE: int = 32
    DB_POOL_SIZE: int = 10
    CACHE_TTL_MINUTES: int = 30
    
    # 🔥 NEW: Logging & Monitoring
    DETAILED_LOGGING: bool = True  # Log detailed search info
    LOG_SIMILARITY_SCORES: bool = True  # Log similarity scores
    LOG_METADATA_QUALITY: bool = True  # Log metadata quality scores
    
    # 🔥 NEW: Feature Flags
    ENABLE_ARABIC_DETECTION: bool = True  # Auto-detect Arabic text in chunks
    ENABLE_METADATA_EXTRACTION: bool = True  # Extract and display full metadata
    ENABLE_SOURCE_RANKING: bool = True  # Rank sources by quality
    ENFORCE_SOURCE_VALIDATION: bool = True  # Validate source citations in answers
    
    class Config:
        env_file = ".env"

settings = Settings()