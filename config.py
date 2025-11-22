from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str
    EMBEDDING_MODEL: str
    
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    SECRET_KEY: str
    
    MAX_UPLOAD_SIZE: int
    UPLOAD_DIR: str
    TOP_K_RESULTS: int
    SIMILARITY_THRESHOLD: float
    
    class Config:
        env_file = ".env"

settings = Settings()