"""
Base agent classes for creating extensible agent architectures.
Provides the foundation for building different types of agents with shared functionality.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, AsyncGenerator, Optional
from uuid import uuid4

from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_core.messages import ToolMessage
from langchain.schema.language_model import BaseLanguageModel
from langchain.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import MessageGraph
from langgraph.prebuilt import ToolNode

from agent.models.loader import ModelLoader
from agent.memory import MemoryManager
from agent.confirmation.manager import ToolConfirmationManager
from database.chat_history_database import get_database
from utils.logger import setup_logger

logger = setup_logger(__name__, "DEBUG")  # 明确设置为DEBUG级别并初始化


class BaseAgent(ABC):
    """Base class for all agents with shared functionality."""
    
    def __init__(self, config_path: str, streaming_config: Dict[str, Any] = None):
        """
        Initialize the base agent.
        
        Args:
            config_path: Path to configuration file
            streaming_config: Configuration for streaming behavior
        """
        self.config_path = config_path
        self.model_loader = ModelLoader(config_path)
        self.llm = self.model_loader.load_llm()
        
        # Initialize database and memory
        self.db = get_database()
        self.memory = MemoryManager(self.db, self.llm)
        
        # Initialize tool confirmation manager
        self.confirmation_manager = ToolConfirmationManager(default_timeout=15)
        
        # Streaming configuration
        self.streaming_config = streaming_config or self._get_default_streaming_config()
        
        # These will be set by subclasses
        self.tools = []
        self.tool_node = None
        self.llm_with_tools = None
        self.graph = None
        
        # Initialize specific agent implementation
        self._initialize_agent()
        
        logger.info(f"{self.__class__.__name__} initialized successfully")
        if self.tools:
            logger.info(f"Loaded {len(self.tools)} tools: {[tool.name for tool in self.tools]}")
    
    def _get_default_streaming_config(self) -> Dict[str, Any]:
        """Get default streaming configuration. Can be overridden by subclasses."""
        return {
            "require_tool_confirmation": True,  # 是否需要工具确认
            "auto_execute_tools": False,        # 是否自动执行工具
            "stream_mode": "values",             # LangGraph stream mode
            "process_tool_calls": True,          # 是否处理工具调用
            "deduplicate_events": False          # 是否去重事件
        }
    
    @abstractmethod
    def _initialize_agent(self):
        """Initialize agent-specific components. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _get_tools(self) -> List[BaseTool]:
        """Get tools specific to this agent type. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _build_graph(self):
        """Build the LangGraph for this agent type. Must be implemented by subclasses."""
        pass
    
    async def chat_stream(self, 
                         message: str, 
                         session_id: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a chat message with streaming response.
        This is the core shared functionality across all agents.
        
        Args:
            message: User message
            session_id: Session identifier (optional)
            
        Yields:
            Stream of response chunks
        """
        if session_id is None:
            session_id = str(uuid4())
        
        logger.info(f"Processing message for session {session_id} with {self.__class__.__name__}")
        
        try:
            # Add user message to memory
            user_message = {
                "type": "human",
                "content": message,
                "metadata": {}
            }
            self.memory.add_message(session_id, user_message)
            
            # Get chat history
            history, was_compressed = self.memory.get_chat_history(session_id)
            
            # Add current message with session_id in additional_kwargs
            current_message = HumanMessage(
                content=message, 
                additional_kwargs={"session_id": session_id}
            )
            current_messages = history + [current_message]
            
            # Yield session info
            yield {
                "type": "session_info",
                "session_id": session_id,
                "was_compressed": was_compressed,
                "agent_type": self.__class__.__name__
            }
            
            # Process with the graph
            response_content = ""
            tool_calls_made = []
            
            async for chunk in self._stream_graph_response(current_messages):
                if chunk["type"] == "message":
                    response_content += chunk["content"]
                    yield chunk
                elif chunk["type"] == "tool_call":
                    tool_calls_made.append(chunk)
                    yield chunk
                elif chunk["type"] == "tool_result":
                    yield chunk
                elif chunk["type"] == "tool_detected":
                    # Forward tool detection events to frontend
                    yield chunk
                elif chunk["type"] in ["tool_confirmation_required", "tool_confirmation_timeout", 
                                       "tool_confirmation_rejected", "tool_execution_start", "tool_error"]:
                    # Forward all tool confirmation related events
                    yield chunk
            
            # Save AI response to memory
            ai_message = {
                "type": "ai",
                "content": response_content,
                "metadata": {
                    "tool_calls": tool_calls_made,
                    "agent_type": self.__class__.__name__
                }
            }
            self.memory.add_message(session_id, ai_message)
            
            # Save tool calls to memory
            for tool_call in tool_calls_made:
                tool_message = {
                    "type": "tool_call",
                    "content": tool_call.get("result", ""),
                    "metadata": {
                        "tool_name": tool_call.get("name", ""),
                        "tool_args": tool_call.get("args", {}),
                        "tool_id": tool_call.get("id", ""),
                        "agent_type": self.__class__.__name__
                    }
                }
                self.memory.add_message(session_id, tool_message)
            
            yield {
                "type": "complete",
                "session_id": session_id,
                "agent_type": self.__class__.__name__
            }
            
        except Exception as e:
            logger.error(f"Error processing message in {self.__class__.__name__}: {e}")
            yield {
                "type": "error",
                "content": f"An error occurred: {str(e)}",
                "agent_type": self.__class__.__name__
            }
    
    async def _stream_graph_response(self, messages: List[BaseMessage]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response from the LangGraph with configurable behavior.
        This method is now generic and configurable via streaming_config.
        """
        try:
            logger.info(f"Starting graph streaming for {len(messages)} messages")
            logger.info(f"Available tools: {[tool.name for tool in self.tools]}")
            logger.info(f"Streaming config: {self.streaming_config}")
            
            current_response = ""
            tool_calls_made = []
            last_processed_event = None if self.streaming_config["deduplicate_events"] else "no_dedup"
            
            # Use graph for streaming processing
            async for event in self.graph.astream(messages, stream_mode=self.streaming_config["stream_mode"]):
                logger.debug(f"Graph event: {type(event)} - length: {len(event) if isinstance(event, list) else 'N/A'}")
                
                # Process message list
                if isinstance(event, list) and event:
                    last_message = event[-1]
                    
                    # Skip duplicate events if configured
                    if self.streaming_config["deduplicate_events"] and last_processed_event == event:
                        continue
                    last_processed_event = event
                    
                    # Process AI message content
                    if hasattr(last_message, 'content') and last_message.content:
                        content = str(last_message.content)
                        if content and content != current_response:
                            # Stream new content
                            new_content = content[len(current_response):] if current_response in content else content
                            current_response = content
                            
                            if new_content.strip():
                                logger.debug(f"Streaming content: {new_content[:100]}...")
                                yield {
                                    "type": "message",
                                    "content": new_content,
                                    "is_complete": False
                                }
                    
                    # Process tool calls based on configuration
                    if (self.streaming_config["process_tool_calls"] and 
                        hasattr(last_message, 'tool_calls') and last_message.tool_calls):
                        
                        async for tool_event in self._process_tool_calls(last_message.tool_calls, messages):
                            yield tool_event
                            if tool_event["type"] == "tool_call":
                                tool_calls_made.append(tool_event)
                    
                    # Process tool result messages
                    if isinstance(last_message, ToolMessage):
                        async for result_event in self._process_tool_result(last_message, tool_calls_made):
                            yield result_event
            
            # Mark completion
            if current_response:
                yield {
                    "type": "message", 
                    "content": "",
                    "is_complete": True
                }
                        
            logger.info(f"Graph streaming completed. Total response length: {len(current_response)}")
            
        except Exception as e:
            logger.error(f"Error in graph streaming: {e}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            yield {
                "type": "message",
                "content": error_msg,
                "is_complete": True
            }
    
    async def _process_tool_calls(self, tool_calls: List[Dict], messages: List[BaseMessage]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process tool calls based on streaming configuration.
        Can be overridden by subclasses for custom behavior.
        """
        for tool_call in tool_calls:
            call_name = tool_call.get('name', '')
            call_args = tool_call.get('args', {})
            call_id = tool_call.get('id', '')
            
            logger.info(f"Tool call detected: {call_name} with args: {call_args}")
            
            tool_info = self._get_tool_info(call_name)
            
            # Always yield tool detection event
            yield {
                "type": "tool_detected",
                "name": call_name,
                "args": call_args,
                "id": call_id,
                "description": tool_info.get('description', ''),
                "args_schema": tool_info.get('args_schema', {})
            }
            
            # Handle tool execution based on configuration
            if self.streaming_config["auto_execute_tools"]:
                # Auto-execute without confirmation
                yield {
                    "type": "tool_execution_start",
                    "tool_name": call_name,
                    "args": call_args
                }
                
                try:
                    tool_result = await self._execute_tool({
                        'name': call_name,
                        'args': call_args,
                        'id': call_id
                    })
                    
                    yield {
                        "type": "tool_result",
                        "tool_name": call_name,
                        "result": str(tool_result),
                        "args": call_args,
                        "description": tool_info.get('description', ''),
                        "args_schema": tool_info.get('args_schema', {})
                    }
                    
                    yield {
                        "type": "tool_call",
                        "name": call_name,
                        "args": call_args,
                        "result": str(tool_result),
                        "id": call_id
                    }
                    
                except Exception as tool_error:
                    logger.error(f"Tool execution error: {tool_error}")
                    yield {
                        "type": "tool_error",
                        "tool_name": call_name,
                        "error": str(tool_error)
                    }
                    
            elif self.streaming_config["require_tool_confirmation"]:
                # Use confirmation workflow
                async for confirmation_event in self._handle_tool_confirmation(tool_call, tool_info, messages):
                    yield confirmation_event
    
    async def _process_tool_result(self, tool_message: ToolMessage, tool_calls_made: List[Dict]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process tool result messages. Can be overridden by subclasses.
        """
        logger.info(f"Tool result message received: {tool_message.content[:100]}...")
        
        # Find the corresponding tool call and update result
        for tool_call in tool_calls_made:
            if tool_call.get("result") == "executing...":
                tool_call["result"] = str(tool_message.content)
                
                yield {
                    "type": "tool_result",
                    "tool_name": tool_call["name"],
                    "result": str(tool_message.content),
                    "args": tool_call["args"],
                    "description": "",
                    "args_schema": {}
                }
                break
    
    async def _handle_tool_confirmation(self, tool_call: Dict, tool_info: Dict, messages: List[BaseMessage]) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle tool confirmation workflow."""
        call_name = tool_call.get('name', '')
        call_args = tool_call.get('args', {})
        call_id = tool_call.get('id', '')
        
        # Get session_id
        session_id = None
        for msg in messages:
            if hasattr(msg, 'additional_kwargs') and 'session_id' in msg.additional_kwargs:
                session_id = msg.additional_kwargs['session_id']
                break
        if not session_id:
            session_id = 'default'
        
        # Send tool confirmation request
        yield {
            "type": "tool_confirmation_required",
            "tool_name": call_name,
            "args": call_args,
            "description": tool_info.get('description', ''),
            "args_schema": tool_info.get('args_schema', {}),
            "session_id": session_id
        }
        
        # Wait for user confirmation
        confirmed, updated_args, error_msg = await self.confirmation_manager.request_confirmation(
            session_id=session_id,
            tool_name=call_name,
            tool_args=call_args,
            tool_description=tool_info.get('description', ''),
            tool_schema=tool_info.get('args_schema', {})
        )
        
        if error_msg:
            yield {
                "type": "tool_confirmation_timeout", 
                "message": error_msg
            }
            return
        
        if not confirmed:
            yield {
                "type": "tool_confirmation_rejected",
                "message": f"用户取消了工具 {call_name} 的执行"
            }
            return
        
        # Execute tool
        yield {
            "type": "tool_execution_start",
            "tool_name": call_name,
            "args": updated_args
        }
        
        try:
            tool_result = await self._execute_tool({
                'name': call_name,
                'args': updated_args,
                'id': call_id
            })
            
            yield {
                "type": "tool_result",
                "tool_name": call_name,
                "result": str(tool_result),
                "args": updated_args,
                "description": tool_info.get('description', ''),
                "args_schema": tool_info.get('args_schema', {})
            }
            
            yield {
                "type": "tool_call",
                "name": call_name,
                "args": updated_args,
                "result": str(tool_result),
                "id": call_id
            }
            
        except Exception as tool_error:
            logger.error(f"Tool execution error: {tool_error}")
            yield {
                "type": "tool_error",
                "tool_name": call_name,
                "error": str(tool_error)
            }
    
    async def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """Execute a single tool call."""
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})
        
        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
        
        # Find the tool by name
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    # Execute the tool with the provided arguments
                    result = await tool.ainvoke(tool_args) if hasattr(tool, 'ainvoke') else tool.invoke(tool_args)
                    return str(result)
                except Exception as e:
                    logger.error(f"Tool {tool_name} execution failed: {e}")
                    return f"Tool execution failed: {str(e)}"
        
        return f"Tool {tool_name} not found"

    def _get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed information about a tool."""
        for tool in self.tools:
            if tool.name == tool_name:
                tool_info = {
                    'name': tool.name,
                    'description': tool.description,
                    'args_schema': {}
                }
                
                # 获取参数 schema
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    schema = tool.args_schema
                    if hasattr(schema, 'model_fields'):
                        # Pydantic v2
                        tool_info['args_schema'] = {
                            field_name: {
                                'type': str(field_info.annotation),
                                'description': field_info.description or '',
                                'required': field_info.is_required()
                            }
                            for field_name, field_info in schema.model_fields.items()
                        }
                    elif hasattr(schema, '__fields__'):
                        # Pydantic v1
                        tool_info['args_schema'] = {
                            field_name: {
                                'type': str(field_info.type_),
                                'description': field_info.field_info.description or '',
                                'required': field_info.required
                            }
                            for field_name, field_info in schema.__fields__.items()
                        }
                
                return tool_info
        
        return {'name': tool_name, 'description': '', 'args_schema': {}}
    
    # Common utility methods that all agents can use
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session."""
        info = self.memory.get_session_stats(session_id)
        info['agent_type'] = self.__class__.__name__
        return info
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session."""
        self.memory.clear_session(session_id)
    
    def confirm_tool_execution(self, session_id: str, confirmed: bool, updated_args: Optional[Dict[str, Any]] = None) -> bool:
        """
        Confirm or reject a tool execution request.
        
        Args:
            session_id: Session identifier
            confirmed: Whether the tool execution is confirmed
            updated_args: Updated arguments for the tool (if confirmed)
            
        Returns:
            True if confirmation was processed successfully
        """
        return self.confirmation_manager.confirm_tool(session_id, confirmed, updated_args)
    
    def get_pending_tool_confirmation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get pending tool confirmation request for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Pending request data or None
        """
        request = self.confirmation_manager.get_pending_request(session_id)
        if request:
            return {
                "id": request.id,
                "tool_name": request.tool_name,
                "tool_args": request.tool_args,
                "tool_description": request.tool_description,
                "tool_schema": request.tool_schema,
                "timestamp": request.timestamp,
                "timeout_seconds": request.timeout_seconds,
                "agent_type": self.__class__.__name__
            }
        return None