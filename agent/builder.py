"""
Agent builder module for creating conversation agents with LangGraph.
Provides the main agent implementation with tool calling and streaming support.
"""
import asyncio
from typing import Dict, Any, List, AsyncGenerator, Optional
from uuid import uuid4

from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.schema.language_model import BaseLanguageModel
from langchain.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import MessageGraph
from langgraph.prebuilt import ToolNode, create_react_agent

from agent.models.loader import ModelLoader
from agent.tools.math_tools import get_math_tools
from agent.memory import MemoryManager
from agent.confirmation.manager import ToolConfirmationManager
from database.chat_history_database import get_database
from utils.logger import get_logger

logger = get_logger(__name__)


class ConversationAgent:
    """Main conversation agent with LangGraph integration."""
    
    def __init__(self, config_path: str):
        """
        Initialize the conversation agent.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.model_loader = ModelLoader(config_path)
        self.llm = self.model_loader.load_llm()
        self.tools = get_math_tools()
        self.tool_node = ToolNode(self.tools)
        
        # Initialize database and memory
        self.db = get_database()
        self.memory = MemoryManager(self.db, self.llm)
        
        # Initialize tool confirmation manager
        self.confirmation_manager = ToolConfirmationManager(default_timeout=15)
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build the graph using create_react_agent
        self.graph = self._build_graph()
        
        logger.info("Conversation agent initialized successfully")
        logger.info(f"Loaded {len(self.tools)} tools: {[tool.name for tool in self.tools]}")
        logger.info(f"LLM with tools type: {type(self.llm_with_tools)}")
        logger.info(f"LLM tools bound: {hasattr(self.llm_with_tools, 'kwargs') and 'tools' in getattr(self.llm_with_tools, 'kwargs', {})}")
    
    def _build_graph(self):
        """Build the LangGraph conversation graph using create_react_agent."""
        try:
            # Use the built-in create_react_agent which handles tool calling automatically
            graph = create_react_agent(self.llm, self.tools)
            return graph
        except Exception as e:
            logger.error(f"Failed to create react agent: {e}")
            # Fallback to manual graph construction
            return self._build_manual_graph()
    
    def _build_manual_graph(self):
        """Build manual graph as fallback."""
        from langgraph.graph import MessageGraph
        
        def should_continue(messages):
            """Determine if we should continue to tool calling or end."""
            last_message = messages[-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            return END
        
        def call_model(messages):
            """Call the LLM with messages."""
            response = self.llm_with_tools.invoke(messages)
            return response
        
        def call_tools(messages):
            """Execute tool calls using ToolNode."""
            return self.tool_node.invoke({"messages": messages})
        
        # Create the graph
        workflow = MessageGraph()
        
        # Add nodes
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", call_tools)
        
        # Add edges
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    async def chat_stream(self, 
                         message: str, 
                         session_id: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a chat message with streaming response.
        
        Args:
            message: User message
            session_id: Session identifier (optional)
            
        Yields:
            Stream of response chunks
        """
        if session_id is None:
            session_id = str(uuid4())
        
        logger.info(f"Processing message for session {session_id}")
        
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
                "was_compressed": was_compressed
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
                    "tool_calls": tool_calls_made
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
                        "tool_id": tool_call.get("id", "")
                    }
                }
                self.memory.add_message(session_id, tool_message)
            
            yield {
                "type": "complete",
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            yield {
                "type": "error",
                "content": f"An error occurred: {str(e)}"
            }
    
    async def _stream_graph_response(self, messages: List[BaseMessage]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response from the LangGraph with tool confirmation support."""
        try:
            logger.info(f"Starting LLM streaming with tool confirmation for {len(messages)} messages")
            logger.info(f"Available tools: {[tool.name for tool in self.tools]}")
            logger.info(f"LLM with tools type: {type(self.llm_with_tools)}")
            
            # 强制打印调试信息
            print(f"[DEBUG] Starting LLM streaming with {len(messages)} messages")
            print(f"[DEBUG] Available tools: {[tool.name for tool in self.tools]}")
            
            # 测试工具绑定
            if hasattr(self.llm_with_tools, 'bound'):
                logger.info(f"LLM bound tools: {getattr(self.llm_with_tools, 'bound', 'None')}")
            
            current_response = ""
            content_buffer = ""
            chunks_received = 0
            
            # 工具调用状态跟踪
            pending_tool_calls = {}
            tool_calls_detected = False
            
            # Stream directly from the LLM
            async for chunk in self.llm_with_tools.astream(messages):
                chunks_received += 1
                print(f"[DEBUG] Chunk #{chunks_received}: {type(chunk)}")
                
                logger.debug(f"Chunk #{chunks_received}: {type(chunk)} - {chunk}")
                
                # 检查chunk的所有属性
                chunk_attrs = [attr for attr in dir(chunk) if not attr.startswith('_')]
                logger.debug(f"Chunk attributes: {chunk_attrs}")
                
                # Handle tool calls first
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    print(f"[DEBUG] TOOL CALLS DETECTED in chunk #{chunks_received}: {chunk.tool_calls}")
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
                            
                            print(f"[DEBUG] Added tool call to pending: {pending_tool_calls[0]}")
                            
                            yield {
                                "type": "tool_detected",
                                "name": call_name,
                                "args": {},
                                "id": call_id,
                                "description": tool_info.get('description', ''),
                                "args_schema": tool_info.get('args_schema', {})
                            }
                            print(f"[DEBUG] Just yielded tool_detected event for {call_name}")
                
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
                    print(f"[DEBUG] Content chunk: '{content}'")
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
            print(f"[DEBUG] After streaming: tool_calls_detected={tool_calls_detected}, pending_tool_calls={pending_tool_calls}")
            if pending_tool_calls and tool_calls_detected:
                print(f"[DEBUG] Processing {len(pending_tool_calls)} tool calls for confirmation")
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
                        
                        logger.info(f"Sending tool confirmation request for session: {session_id}")
                        # 发送工具确认请求事件
                        confirmation_event = {
                            "type": "tool_confirmation_required",
                            "tool_name": tool_data['name'],
                            "args": args_dict,
                            "description": tool_data['description'],
                            "args_schema": tool_data['args_schema'],
                            "session_id": session_id
                        }
                        logger.info(f"Yielding confirmation event: {confirmation_event}")
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
        logger.info(f"Tool call structure: {tool_call}")
        
        # Find the tool by name
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    # Execute the tool with the provided arguments
                    result = await tool.ainvoke(tool_args) if hasattr(tool, 'ainvoke') else tool.invoke(tool_args)
                    return str(result)
                except Exception as e:
                    logger.error(f"Tool {tool_name} execution failed: {e}")
                    logger.error(f"Failed args: {tool_args}")
                    logger.error(f"Tool signature: {tool.args_schema}")
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

    async def _process_message_for_streaming(self, message) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a single message and yield streaming chunks."""
        try:
            # Handle tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    yield {
                        "type": "tool_call",
                        "name": tool_call.get("name", ""),
                        "args": tool_call.get("args", {}),
                        "id": tool_call.get("id", "")
                    }
            
            # Handle message content
            if hasattr(message, 'content') and message.content:
                content = str(message.content)
                
                # Check if this is an AI message by class name or type
                is_ai_message = (
                    (hasattr(message, 'type') and message.type == 'ai') or
                    (hasattr(message, '__class__') and 'AI' in message.__class__.__name__) or
                    (not hasattr(message, 'type'))  # Default to AI if no type specified
                )
                
                if is_ai_message:
                    # Stream character by character for AI messages
                    for i, char in enumerate(content):
                        yield {
                            "type": "message",
                            "content": char,
                            "is_complete": i == len(content) - 1
                        }
                        await asyncio.sleep(0.01)  # Small delay for streaming effect
                
        except Exception as e:
            logger.error(f"Error processing message chunk: {e}")
    
    async def _process_message_chunk(self, message, tool_calls_made, current_response):
        """Process message chunk and update tracking variables."""
        # This is a helper method for tracking, not streaming
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_calls_made.append({
                    "name": tool_call.get("name", ""),
                    "args": tool_call.get("args", {}),
                    "id": tool_call.get("id", "")
                })
        
        if hasattr(message, 'content') and message.content:
            current_response += str(message.content)
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session."""
        return self.memory.get_session_stats(session_id)
    
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
                "timeout_seconds": request.timeout_seconds
            }
        return None
