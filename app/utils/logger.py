from loguru import logger
import sys
from pathlib import Path
from datetime import datetime

# Create logs directory
log_dir = Path("data/logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Remove default handler
logger.remove()

# Console handler (INFO level)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
    level="INFO",
    colorize=True
)

# File handler - All logs
logger.add(
    log_dir / "app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="00:00",  # Rotate at midnight
    retention="30 days",
    compression="zip"
)

# File handler - Errors only
logger.add(
    log_dir / "errors_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
    level="ERROR",
    rotation="00:00",
    retention="90 days",
    compression="zip"
)

# File handler - User queries
logger.add(
    log_dir / "queries_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {extra[session_id]} | {extra[query]} | {extra[response_time]}ms",
    level="INFO",
    filter=lambda record: "query" in record["extra"],
    rotation="00:00",
    retention="60 days"
)

def log_query(session_id: str, query: str, response_time: float):
    """Log user query"""
    logger.bind(session_id=session_id, query=query, response_time=response_time).info("User query")

def log_upload(filename: str, status: str, duration: float, error: str = None):
    """Log file upload"""
    logger.bind(filename=filename, status=status, duration=duration, error=error).info("File upload")   