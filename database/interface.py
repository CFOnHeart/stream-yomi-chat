"""
Database interface module for chat history persistence.
Provides abstract interface for database operations.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import sqlite3
import json
from datetime import datetime
import os

from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseInterface(ABC):
    """Abstract interface for database operations."""
    
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


class SQLiteDatabase(DatabaseInterface):
    """SQLite implementation of the database interface."""
    
    def __init__(self, db_path: str = "database/chat_history.db"):
        self.db_path = db_path
        self._init_database()
        logger.info(f"SQLite database initialized at {db_path}")
    
    def _init_database(self):
        """Initialize the database and create tables if they don't exist."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    character_count INTEGER
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id ON chat_messages(session_id)
            """)
            conn.commit()
    
    def save_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Save a message to the database."""
        message_type = message.get("type", "unknown")
        content = message.get("content", "")
        metadata = json.dumps(message.get("metadata", {}))
        character_count = len(str(content))
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_messages 
                (session_id, message_type, content, metadata, character_count)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, message_type, content, metadata, character_count))
            conn.commit()
        
        logger.debug(f"Saved message for session {session_id}: {message_type}")
    
    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT message_type, content, metadata, timestamp, character_count
                FROM chat_messages 
                WHERE session_id = ? 
                ORDER BY timestamp ASC
            """, (session_id,))
            
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                message = {
                    "type": row["message_type"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "timestamp": row["timestamp"],
                    "character_count": row["character_count"]
                }
                messages.append(message)
            
        logger.debug(f"Retrieved {len(messages)} messages for session {session_id}")
        return messages
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            deleted_count = cursor.rowcount
            conn.commit()
        
        logger.info(f"Deleted {deleted_count} messages for session {session_id}")
    
    def get_total_characters(self, session_id: str) -> int:
        """Get total character count for a session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(character_count) as total 
                FROM chat_messages 
                WHERE session_id = ?
            """, (session_id,))
            result = cursor.fetchone()
            total = result[0] if result[0] is not None else 0
        
        return total


def get_database() -> DatabaseInterface:
    """Factory function to get database instance."""
    return SQLiteDatabase()
