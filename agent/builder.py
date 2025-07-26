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
from database.interface import get_database
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
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build the graph using create_react_agent
        self.graph = self._build_graph()
        
        logger.info("Conversation agent initialized successfully")
    
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
            
            # Add current message
            current_messages = history + [HumanMessage(content=message)]
            
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
        """Stream response from the LangGraph."""
        try:
            # Convert messages to the format expected by the graph
            message_input = {"messages": messages}
            
            # Process through the graph
            result = self.graph.invoke(message_input)
            
            # Extract the final messages from the result
            if isinstance(result, dict) and "messages" in result:
                final_messages = result["messages"]
            else:
                final_messages = result if isinstance(result, list) else [result]
            
            # Get the last AI message
            last_ai_message = None
            tool_calls_info = []
            
            for msg in reversed(final_messages):
                if hasattr(msg, 'content') and msg.content:
                    # Check if this is an AI message
                    if hasattr(msg, 'type') and msg.type == 'ai':
                        last_ai_message = msg
                        break
                    elif hasattr(msg, '__class__') and 'AI' in msg.__class__.__name__:
                        last_ai_message = msg
                        break
                    elif not hasattr(msg, 'type'):  # Assume AI message if no type
                        last_ai_message = msg
                        break
            
            # Look for tool calls in the conversation
            for msg in final_messages:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_calls_info.append({
                            "name": tool_call.get("name", ""),
                            "args": tool_call.get("args", {}),
                            "id": tool_call.get("id", "")
                        })
                        yield {
                            "type": "tool_call",
                            "name": tool_call.get("name", ""),
                            "args": tool_call.get("args", {}),
                            "id": tool_call.get("id", "")
                        }
                
                # Look for tool results
                if hasattr(msg, 'content') and hasattr(msg, 'type'):
                    if msg.type == 'tool':
                        yield {
                            "type": "tool_result",
                            "tool_name": getattr(msg, 'name', 'unknown'),
                            "result": str(msg.content)
                        }
            
            # Stream the final AI response content
            if last_ai_message and hasattr(last_ai_message, 'content'):
                content = last_ai_message.content
                
                # Simulate character-by-character streaming
                for i, char in enumerate(content):
                    yield {
                        "type": "message",
                        "content": char,
                        "is_complete": i == len(content) - 1
                    }
                    await asyncio.sleep(0.01)  # Small delay for streaming effect
            else:
                # Fallback response
                fallback_msg = "I processed your request, but couldn't generate a proper response."
                for i, char in enumerate(fallback_msg):
                    yield {
                        "type": "message",
                        "content": char,
                        "is_complete": i == len(fallback_msg) - 1
                    }
                    await asyncio.sleep(0.01)
            
        except Exception as e:
            logger.error(f"Error in graph streaming: {e}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            for i, char in enumerate(error_msg):
                yield {
                    "type": "message",
                    "content": char,
                    "is_complete": i == len(error_msg) - 1
                }
                await asyncio.sleep(0.01)
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session."""
        return self.memory.get_session_stats(session_id)
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session."""
        self.memory.clear_session(session_id)
