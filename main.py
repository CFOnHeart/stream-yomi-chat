"""
Main entry point for the Conversation Agent backend service.
"""
import uvicorn
from api.routes import app
from utils.logger import setup_logger

logger = setup_logger(__name__)

if __name__ == "__main__":
    logger.info("Starting Conversation Agent backend service...")
    uvicorn.run(
        "api.routes:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
