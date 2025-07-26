"""
Chat history database interface module.
Provides abstract interface for database operations.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class ChatHistoryDatabaseInterface(ABC):
    """Abstract interface for chat history database operations."""
    
    @abstractmethod
    def save_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Save a message to the database."""
        pass
    
    @abstractmethod
    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        pass
    
    @abstractmethod
    def get_total_characters(self, session_id: str) -> int:
        """Get total character count for a session."""
        pass


def get_database() -> ChatHistoryDatabaseInterface:
    """Factory function to get database instance."""
    from database.sqlite_chat_history_database import SQLiteChatHistoryDatabase
    return SQLiteChatHistoryDatabase()
