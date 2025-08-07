"""
Logging utility module for the Conversation Agent backend.
"""
import logging
import sys
from typing import Optional


def setup_logger(name: str, level: str = "DEBUG") -> logging.Logger:
    """
    Setup logger with consistent formatting.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # 如果已经通过uvicorn配置设置了，直接返回
    if logger.handlers and any(h.formatter for h in logger.handlers):
        logger.setLevel(getattr(logging, level.upper()))
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # Avoid adding multiple handlers if logger already exists
    if logger.handlers:
        return logger
    
    # 确保根logger不会干扰
    logger.propagate = False
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # 强制刷新输出
    handler.flush()
    
    return logger


def get_logger(name: str, level: str = "DEBUG") -> logging.Logger:
    """
    Get logger instance with automatic setup.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger doesn't have handlers, set it up
    if not logger.handlers:
        return setup_logger(name, level)
    
    return logger
