"""
Conversation agent implementation extending the base agent.
Provides conversation-focused functionality with tool calling support.
"""
from typing import List, Dict, Any, AsyncGenerator
from langchain.tools import BaseTool
from langchain.schema import BaseMessage, AIMessage
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import MessageGraph
from langgraph.graph import StateGraph, END

from agent.base_agent import BaseAgent
from agent.tools.math_tools import add, subtract, multiply, divide
from agent.tools.web_search import BigModelSearchTool
from utils.logger import setup_logger

logger = setup_logger(__name__, "DEBUG")


class ConversationAgent(BaseAgent):
    """Conversation agent with LangGraph integration and tool calling."""
    
    def __init__(self, *args, **kwargs):
        """Initialize ConversationAgent with auto-execution streaming config."""
        # Configure streaming for conversation agent: auto-execute tools without confirmation
        streaming_config = {
            "require_tool_confirmation": True,
            "auto_execute_tools": False,
            "stream_mode": "values",
            "process_tool_calls": True,
            "deduplicate_events": True
        }
        super().__init__(*args, streaming_config=streaming_config, **kwargs)
    
    def _initialize_agent(self):
        """Initialize conversation-specific components."""
        # Get tools specific to conversation agent
        self.tools = self._get_tools()
        self.tool_node = ToolNode(self.tools)
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build the graph
        self.graph = self._build_graph()
        
        logger.info(f"LLM with tools type: {type(self.llm_with_tools)}")
        logger.info(f"LLM tools bound: {hasattr(self.llm_with_tools, 'kwargs') and 'tools' in getattr(self.llm_with_tools, 'kwargs', {})}")
    
    def _get_tools(self) -> List[BaseTool]:
        """Get tools specific to conversation agent."""
        api_key = self.model_loader.get_tool_config('web_search').get('api_key')
        
        if api_key is None or not isinstance(api_key, str) or api_key == "":
            return [add, subtract, multiply, divide]
        else:
            return [add, subtract, multiply, divide, BigModelSearchTool(api_key=api_key)]
        
    def _build_graph(self):
        """Build a conversation graph that handles tool calling and summarization."""
        from langgraph.graph import MessageGraph
        
        def should_continue(messages):
            """Determine if we should continue to tool calling or end."""
            last_message = messages[-1]
            
            # 检查是否有工具调用
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                logger.info(f"Tool calls detected: {[tc.get('name', '') for tc in last_message.tool_calls]}")
                return "tools"
            
            # 检查是否是工具结果，如果是，回到agent进行总结
            if isinstance(last_message, ToolMessage):
                logger.info("Tool result detected, returning to agent for summarization")
                return "agent"
                
            return END
        
        def call_model(messages):
            """Call the LLM with messages."""
            logger.info(f"Calling model with {len(messages)} messages")
            
            # 检查最后的消息类型，如果有工具结果，添加指引让AI总结
            if messages and isinstance(messages[-1], ToolMessage):
                # 在工具结果后添加指引消息，让AI知道需要总结
                summary_instruction = AIMessage(content="请基于上述搜索结果，为用户提供一个清晰、有用的回答。")
                messages = messages + [summary_instruction]
            
            response = self.llm_with_tools.invoke(messages)
            logger.info(f"Model response type: {type(response)}, has tool_calls: {hasattr(response, 'tool_calls') and bool(response.tool_calls)}")
            return response
        
        def call_tools(messages):
            """Execute tool calls using ToolNode."""
            logger.info(f"Executing tools with {len(messages)} messages")
            try:
                result = self.tool_node.invoke({"messages": messages})
                logger.info(f"Tool execution completed, result type: {type(result)}")
                
                # 确保返回正确格式的消息
                if isinstance(result, dict) and 'messages' in result:
                    return result['messages']
                elif isinstance(result, list):
                    return result
                else:
                    return result
                    
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                # 返回一个错误消息
                from langchain_core.messages import AIMessage
                return [AIMessage(content=f"工具执行失败: {str(e)}")]
        
        # Create the graph
        workflow = MessageGraph()
        
        # Add nodes
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", call_tools)
        
        # Add edges
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")  # 工具执行后回到agent进行总结
        
        logger.info("Conversation graph built successfully")
        return workflow.compile()

