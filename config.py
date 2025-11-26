from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    OLLAMA_MODEL: str
    EMBEDDING_MODEL: str
    APP_PORT: int = 8000
    SECRET_KEY: str
    UPLOAD_DIR: str = "uploads"
    TOP_K_RESULTS: int = 5
    
    # Performance settings
    BATCH_SIZE: int = 50
    EMBEDDING_BATCH_SIZE: int = 32
    DB_POOL_SIZE: int = 10
    
    class Config:
        env_file = ".env"

settings = Settings()