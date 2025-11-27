from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.database.connection import init_db
from app.utils.logger import logger

app = FastAPI(title="Chatbot Hadis")

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

app.include_router(router, prefix="/api")

@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("✓ Database initialized")
    
    # Warm-up: Pre-load embedding model
    try:
        from app.services.embedding_service import EmbeddingService
        embed = EmbeddingService()
        await embed.generate_embedding("test")
        logger.info("✓ Embedding model warmed up")
    except Exception as e:
        logger.warning(f"Warm-up failed: {e}")

@app.get("/")
async def root():
    return {"status": "running", "version": "1.0.0"}