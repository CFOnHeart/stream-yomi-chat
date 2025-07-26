"""
Math tools for the conversation agent.
Provides basic arithmetic operations for testing tool calling functionality.
"""
from typing import Any, Dict
from langchain.tools import tool
from utils.logger import get_logger

logger = get_logger(__name__)


@tool
def add(a: float, b: float) -> float:
    """Add two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The sum of a and b
    """
    result = a + b
    logger.info(f"Math tool: add({a}, {b}) = {result}")
    return result


@tool
def subtract(a: float, b: float) -> float:
    """Subtract the second number from the first.
    
    Args:
        a: First number (minuend)
        b: Second number (subtrahend)
        
    Returns:
        The difference of a and b
    """
    result = a - b
    logger.info(f"Math tool: subtract({a}, {b}) = {result}")
    return result


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The product of a and b
    """
    result = a * b
    logger.info(f"Math tool: multiply({a}, {b}) = {result}")
    return result


@tool
def divide(a: float, b: float) -> float:
    """Divide the first number by the second.
    
    Args:
        a: First number (dividend)
        b: Second number (divisor)
        
    Returns:
        The quotient of a and b
        
    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        error_msg = "Cannot divide by zero"
        logger.error(f"Math tool: divide({a}, {b}) - {error_msg}")
        raise ValueError(error_msg)
    
    result = a / b
    logger.info(f"Math tool: divide({a}, {b}) = {result}")
    return result


def get_math_tools():
    """Get all math tools as a list."""
    return [add, subtract, multiply, divide]
