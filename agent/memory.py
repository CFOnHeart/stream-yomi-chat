"""
Memory management module for chat history and context.
Handles chat history compression when context exceeds limits.
"""
from typing import List, Dict, Any, Tuple
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.schema.language_model import BaseLanguageModel

from database.interface import DatabaseInterface
from utils.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """Manages chat history and memory compression."""
    
    def __init__(self, 
                 db: DatabaseInterface, 
                 llm: BaseLanguageModel,
                 max_characters: int = 3200):
        """
        Initialize memory manager.
        
        Args:
            db: Database interface for persistence
            llm: Language model for summarization
            max_characters: Maximum characters before compression
        """
        self.db = db
        self.llm = llm
        self.max_characters = max_characters
        logger.info(f"Memory manager initialized with max_characters={max_characters}")
    
    def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Add a message to the session.
        
        Args:
            session_id: Session identifier
            message: Message data
        """
        # Save to database (excluding summarized content)
        if not message.get("is_summary", False):
            self.db.save_message(session_id, message)
        
        logger.debug(f"Added message to session {session_id}: {message.get('type', 'unknown')}")
    
    def get_chat_history(self, session_id: str) -> Tuple[List[BaseMessage], bool]:
        """
        Get chat history for a session with compression if needed.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (messages, was_compressed)
        """
        # Get raw history from database
        raw_messages = self.db.get_chat_history(session_id)
        
        # Check if compression is needed
        total_chars = sum(len(str(msg.get("content", ""))) for msg in raw_messages)
        
        if total_chars <= self.max_characters:
            # No compression needed
            messages = self._convert_to_langchain_messages(raw_messages)
            return messages, False
        else:
            # Compression needed
            logger.info(f"Compressing history for session {session_id} ({total_chars} chars > {self.max_characters})")
            compressed_messages = self._compress_history(raw_messages)
            return compressed_messages, True
    
    def _convert_to_langchain_messages(self, raw_messages: List[Dict[str, Any]]) -> List[BaseMessage]:
        """Convert raw messages to LangChain message format."""
        messages = []
        
        for msg in raw_messages:
            msg_type = msg.get("type", "unknown")
            content = msg.get("content", "")
            
            if msg_type == "human":
                messages.append(HumanMessage(content=content))
            elif msg_type == "ai":
                messages.append(AIMessage(content=content))
            elif msg_type == "system":
                messages.append(SystemMessage(content=content))
            elif msg_type == "tool_call":
                # Handle tool call messages
                tool_name = msg.get("metadata", {}).get("tool_name", "unknown")
                tool_args = msg.get("metadata", {}).get("tool_args", {})
                tool_content = f"Tool: {tool_name}\nArguments: {tool_args}\nResult: {content}"
                messages.append(AIMessage(content=tool_content))
        
        return messages
    
    def _compress_history(self, raw_messages: List[Dict[str, Any]]) -> List[BaseMessage]:
        """
        Compress chat history using LLM summarization.
        
        Args:
            raw_messages: Raw message data from database
            
        Returns:
            Compressed messages including summary
        """
        if not raw_messages:
            return []
        
        # Convert to text for summarization
        history_text = self._messages_to_text(raw_messages)
        
        # Create summarization prompt
        summary_prompt = f"""Please summarize the following conversation history in a concise manner, preserving key context and information:

{history_text}

Summary:"""
        
        try:
            # Get summary from LLM
            summary_response = self.llm.invoke([HumanMessage(content=summary_prompt)])
            summary = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
            
            # Keep recent messages (last few) + summary
            recent_messages = raw_messages[-3:] if len(raw_messages) > 3 else raw_messages
            
            # Create compressed message list
            compressed = [SystemMessage(content=f"Previous conversation summary: {summary}")]
            compressed.extend(self._convert_to_langchain_messages(recent_messages))
            
            logger.info(f"Compressed {len(raw_messages)} messages to {len(compressed)} messages")
            return compressed
            
        except Exception as e:
            logger.error(f"Failed to compress history: {e}")
            # Fall back to recent messages only
            recent_messages = raw_messages[-5:] if len(raw_messages) > 5 else raw_messages
            return self._convert_to_langchain_messages(recent_messages)
    
    def _messages_to_text(self, messages: List[Dict[str, Any]]) -> str:
        """Convert messages to text format for summarization."""
        text_parts = []
        
        for msg in messages:
            msg_type = msg.get("type", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            if msg_type == "human":
                text_parts.append(f"User: {content}")
            elif msg_type == "ai":
                text_parts.append(f"Assistant: {content}")
            elif msg_type == "tool_call":
                tool_name = msg.get("metadata", {}).get("tool_name", "unknown")
                text_parts.append(f"Tool ({tool_name}): {content}")
        
        return "\n".join(text_parts)
    
    def clear_session(self, session_id: str) -> None:
        """Clear all messages for a session."""
        self.db.delete_session(session_id)
        logger.info(f"Cleared session {session_id}")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        total_chars = self.db.get_total_characters(session_id)
        message_count = len(self.db.get_chat_history(session_id))
        needs_compression = total_chars > self.max_characters
        
        return {
            "total_characters": total_chars,
            "message_count": message_count,
            "needs_compression": needs_compression,
            "max_characters": self.max_characters
        }
