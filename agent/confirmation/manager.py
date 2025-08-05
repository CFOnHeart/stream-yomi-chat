"""
Tool confirmation manager for handling user confirmations before tool execution.
Implements timeout and confirmation flow management.
"""
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable
from uuid import uuid4
from dataclasses import dataclass
from enum import Enum
import time

from utils.logger import get_logger

logger = get_logger(__name__)


class ConfirmationStatus(Enum):
    """Status of a tool confirmation request."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class ToolConfirmationRequest:
    """Tool confirmation request data."""
    id: str
    session_id: str
    tool_name: str
    tool_args: Dict[str, Any]
    tool_description: str
    tool_schema: Dict[str, Any]
    timestamp: float
    timeout_seconds: int = 15
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    
    def is_expired(self) -> bool:
        """Check if the confirmation request has expired."""
        return time.time() - self.timestamp > self.timeout_seconds


class ToolConfirmationManager:
    """Manages tool confirmation requests and user responses."""
    
    def __init__(self, default_timeout: int = 15):
        """
        Initialize the confirmation manager.
        
        Args:
            default_timeout: Default timeout in seconds for confirmations
        """
        self.default_timeout = default_timeout
        self._pending_requests: Dict[str, ToolConfirmationRequest] = {}
        self._confirmation_futures: Dict[str, asyncio.Future] = {}
        
        logger.info(f"Tool confirmation manager initialized with {default_timeout}s timeout")
    
    async def request_confirmation(
        self,
        session_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_description: str,
        tool_schema: Dict[str, Any],
        timeout_seconds: Optional[int] = None
    ) -> tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Request user confirmation for tool execution.
        
        Args:
            session_id: Session identifier
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
            tool_description: Description of the tool
            tool_schema: Schema of the tool parameters
            timeout_seconds: Timeout in seconds (uses default if None)
            
        Returns:
            Tuple of (confirmed, updated_args, error_message)
        """
        timeout = timeout_seconds or self.default_timeout
        request_id = str(uuid4())
        
        # Create confirmation request
        request = ToolConfirmationRequest(
            id=request_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_description=tool_description,
            tool_schema=tool_schema,
            timestamp=time.time(),
            timeout_seconds=timeout
        )
        
        # Store the request
        self._pending_requests[request_id] = request
        
        # Create future for the confirmation
        future = asyncio.Future()
        self._confirmation_futures[request_id] = future
        
        logger.info(f"Created confirmation request {request_id} for tool {tool_name} in session {session_id}")
        
        try:
            # Wait for confirmation with timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            
            # Get the updated request
            updated_request = self._pending_requests.get(request_id)
            if updated_request:
                confirmed = updated_request.status == ConfirmationStatus.CONFIRMED
                updated_args = updated_request.tool_args
                
                logger.info(f"Confirmation request {request_id} completed: {confirmed}")
                return confirmed, updated_args, None
            else:
                logger.error(f"Confirmation request {request_id} not found after completion")
                return False, tool_args, "Internal error: request not found"
                
        except asyncio.TimeoutError:
            # Handle timeout
            logger.warning(f"Confirmation request {request_id} timed out after {timeout}s")
            if request_id in self._pending_requests:
                self._pending_requests[request_id].status = ConfirmationStatus.TIMEOUT
            
            return False, tool_args, f"Tool confirmation timed out after {timeout} seconds"
            
        finally:
            # Cleanup
            self._cleanup_request(request_id)
    
    def confirm_tool(
        self,
        session_id: str,
        confirmed: bool,
        updated_args: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Confirm or reject a tool execution request.
        
        Args:
            session_id: Session identifier
            confirmed: Whether the tool execution is confirmed
            updated_args: Updated arguments for the tool (if confirmed)
            
        Returns:
            True if confirmation was processed successfully
        """
        # Find the pending request for this session
        request_id = None
        for req_id, request in self._pending_requests.items():
            if request.session_id == session_id and request.status == ConfirmationStatus.PENDING:
                request_id = req_id
                break
        
        if not request_id:
            logger.warning(f"No pending confirmation request found for session {session_id}")
            return False
        
        request = self._pending_requests[request_id]
        
        # Check if expired
        if request.is_expired():
            logger.warning(f"Confirmation request {request_id} has expired")
            request.status = ConfirmationStatus.TIMEOUT
            return False
        
        # Update request status and arguments
        request.status = ConfirmationStatus.CONFIRMED if confirmed else ConfirmationStatus.REJECTED
        if confirmed and updated_args:
            request.tool_args = updated_args
        
        # Resolve the future
        future = self._confirmation_futures.get(request_id)
        if future and not future.done():
            future.set_result(True)
        
        logger.info(f"Confirmation request {request_id} {'confirmed' if confirmed else 'rejected'}")
        return True
    
    def get_pending_request(self, session_id: str) -> Optional[ToolConfirmationRequest]:
        """
        Get the pending confirmation request for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Pending request or None if not found
        """
        for request in self._pending_requests.values():
            if request.session_id == session_id and request.status == ConfirmationStatus.PENDING:
                return request
        return None
    
    def has_pending_request(self, session_id: str) -> bool:
        """
        Check if there's a pending confirmation request for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if there's a pending request
        """
        return self.get_pending_request(session_id) is not None
    
    def _cleanup_request(self, request_id: str) -> None:
        """Clean up a completed confirmation request."""
        # Remove from pending requests
        if request_id in self._pending_requests:
            del self._pending_requests[request_id]
        
        # Remove from futures
        if request_id in self._confirmation_futures:
            future = self._confirmation_futures[request_id]
            if not future.done():
                future.cancel()
            del self._confirmation_futures[request_id]
        
        logger.debug(f"Cleaned up confirmation request {request_id}")
    
    def cleanup_expired_requests(self) -> int:
        """
        Clean up expired confirmation requests.
        
        Returns:
            Number of expired requests cleaned up
        """
        expired_ids = []
        
        for request_id, request in self._pending_requests.items():
            if request.is_expired():
                expired_ids.append(request_id)
        
        for request_id in expired_ids:
            self._cleanup_request(request_id)
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired confirmation requests")
        
        return len(expired_ids)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about confirmation requests."""
        return {
            "pending_requests": len(self._pending_requests),
            "active_futures": len(self._confirmation_futures),
            "default_timeout": self.default_timeout
        }
