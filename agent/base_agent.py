"""
Base agent classes for creating extensible agent architectures.
Provides the foundation for building different types of agents with shared functionality.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, AsyncGenerator, Optional
from uuid import uuid4

from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.schema.language_model import BaseLanguageModel
from langchain.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import MessageGraph
from langgraph.prebuilt import ToolNode

from agent.models.loader import ModelLoader
from agent.memory import MemoryManager
from agent.confirmation.manager import ToolConfirmationManager
from database.chat_history_database import get_database
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all agents with shared functionality."""
    
    def __init__(self, config_path: str):
        """
        Initialize the base agent.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.model_loader = ModelLoader(config_path)
        self.llm = self.model_loader.load_llm()
        
        # Initialize database and memory
        self.db = get_database()
        self.memory = MemoryManager(self.db, self.llm)
        
        # Initialize tool confirmation manager
        self.confirmation_manager = ToolConfirmationManager(default_timeout=15)
        
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
        Stream response from the LangGraph with tool confirmation support.
        This method can be overridden by subclasses for custom streaming behavior.
        """
        try:
            logger.info(f"Starting LLM streaming with tool confirmation for {len(messages)} messages")
            logger.info(f"Available tools: {[tool.name for tool in self.tools]}")
            
            current_response = ""
            content_buffer = ""
            chunks_received = 0
            
            # 工具调用状态跟踪
            pending_tool_calls = {}
            tool_calls_detected = False
            
            # Stream directly from the LLM
            async for chunk in self.llm_with_tools.astream(messages):
                chunks_received += 1
                logger.debug(f"Chunk #{chunks_received}: {type(chunk)} - {chunk}")
                
                # Handle tool calls first
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    logger.info(f"Tool calls detected in chunk #{chunks_received}: {chunk.tool_calls}")
                    tool_calls_detected = True
                    # 发送缓冲区中的内容
                    if content_buffer.strip():
                        yield {
                            "type": "message",
                            "content": content_buffer,
                            "is_complete": False
                        }
                        content_buffer = ""
                    
                    for tool_call in chunk.tool_calls:
                        call_id = tool_call.get('id')
                        call_name = tool_call.get('name', '')
                        
                        if call_id and call_name:
                            tool_info = self._get_tool_info(call_name)
                            
                            pending_tool_calls[0] = {
                                'name': call_name,
                                'args_str': '',
                                'id': call_id,
                                'description': tool_info.get('description', ''),
                                'args_schema': tool_info.get('args_schema', {})
                            }
                            
                            yield {
                                "type": "tool_detected",
                                "name": call_name,
                                "args": {},
                                "id": call_id,
                                "description": tool_info.get('description', ''),
                                "args_schema": tool_info.get('args_schema', {})
                            }
                
                # Handle tool call chunks (参数构建)
                if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                    for tool_chunk in chunk.tool_call_chunks:
                        index = tool_chunk.get('index', 0)
                        args_part = tool_chunk.get('args', '')
                        
                        if index in pending_tool_calls and args_part:
                            pending_tool_calls[index]['args_str'] += args_part
                
                # Handle content streaming (常规消息内容)
                if hasattr(chunk, 'content') and chunk.content:
                    content = str(chunk.content)
                    current_response += content
                    content_buffer += content
                    logger.debug(f"Content chunk: '{content}'")
                    
                    # 立即发送内容
                    if content_buffer.strip():
                        yield {
                            "type": "message",
                            "content": content_buffer,
                            "is_complete": False
                        }
                        content_buffer = ""
            
            # 处理完成后的工具调用确认流程
            if pending_tool_calls and tool_calls_detected:
                logger.info(f"Processing {len(pending_tool_calls)} tool calls for confirmation")
                for index, tool_data in pending_tool_calls.items():
                    try:
                        # 解析完整的参数
                        import json
                        args_dict = json.loads(tool_data['args_str']) if tool_data['args_str'] else {}
                        logger.info(f"Tool call parsed: {tool_data['name']} with args: {args_dict}")
                        
                        # 获取session_id
                        session_id = None
                        for msg in messages:
                            if hasattr(msg, 'additional_kwargs') and 'session_id' in msg.additional_kwargs:
                                session_id = msg.additional_kwargs['session_id']
                                break
                        if not session_id:
                            session_id = 'default'
                        
                        # 发送工具确认请求事件
                        confirmation_event = {
                            "type": "tool_confirmation_required",
                            "tool_name": tool_data['name'],
                            "args": args_dict,
                            "description": tool_data['description'],
                            "args_schema": tool_data['args_schema'],
                            "session_id": session_id
                        }
                        yield confirmation_event
                        
                        # 等待用户确认
                        confirmed, updated_args, error_msg = await self.confirmation_manager.request_confirmation(
                            session_id=session_id,
                            tool_name=tool_data['name'],
                            tool_args=args_dict,
                            tool_description=tool_data['description'],
                            tool_schema=tool_data['args_schema']
                        )
                        
                        if error_msg:
                            yield {
                                "type": "tool_confirmation_timeout", 
                                "message": error_msg
                            }
                            continue
                        
                        if not confirmed:
                            yield {
                                "type": "tool_confirmation_rejected",
                                "message": f"用户取消了工具 {tool_data['name']} 的执行"
                            }
                            continue
                        
                        # 执行工具
                        call_data = {
                            'name': tool_data['name'],
                            'args': updated_args,
                            'id': tool_data['id']
                        }
                        
                        yield {
                            "type": "tool_execution_start",
                            "tool_name": tool_data['name'],
                            "args": updated_args
                        }
                        
                        tool_result = await self._execute_tool(call_data)
                        
                        yield {
                            "type": "tool_result",
                            "tool_name": tool_data['name'],
                            "result": str(tool_result),
                            "args": updated_args,
                            "description": tool_data.get('description', ''),
                            "args_schema": tool_data.get('args_schema', {})
                        }
                        
                    except Exception as tool_error:
                        logger.error(f"Tool confirmation/execution error: {tool_error}")
                        yield {
                            "type": "tool_error",
                            "tool_name": tool_data['name'],
                            "error": str(tool_error)
                        }
            
            # 发送剩余的缓冲内容
            if content_buffer.strip():
                yield {
                    "type": "message",
                    "content": content_buffer,
                    "is_complete": False
                }
            
            # 如果有任何响应内容，标记完成
            if current_response or not tool_calls_detected:
                yield {
                    "type": "message", 
                    "content": "",
                    "is_complete": True
                }
                        
            logger.info(f"LLM streaming completed. Total response length: {len(current_response)}")
            
        except Exception as e:
            logger.error(f"Error in LLM streaming: {e}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            yield {
                "type": "message",
                "content": error_msg,
                "is_complete": True
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