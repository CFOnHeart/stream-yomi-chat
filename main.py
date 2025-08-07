"""
Main entry point for the Conversation Agent backend service.
"""
import uvicorn
import logging.config
from api.routes import app
from uvicorn_log_config import LOGGING_CONFIG
from utils.logger import setup_logger

# 应用自定义日志配置
logging.config.dictConfig(LOGGING_CONFIG)
logger = setup_logger(__name__, "DEBUG")

if __name__ == "__main__":
    logger.info("Starting Conversation Agent backend service...")
    uvicorn.run(
        "api.routes:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=LOGGING_CONFIG,  # 使用自定义日志配置
        access_log=True,
        use_colors=True
    )
