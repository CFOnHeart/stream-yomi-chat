"""
Conversation agent implementation extending the base agent.
Provides conversation-focused functionality with tool calling support.
"""
from typing import List
from langchain.tools import BaseTool
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.graph.message import MessageGraph
from langgraph.graph import END

from agent.base_agent import BaseAgent
from agent.tools.math_tools import get_math_tools
from utils.logger import get_logger

logger = get_logger(__name__)


class ConversationAgent(BaseAgent):
    """Conversation agent with LangGraph integration and tool calling."""
    
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
        return get_math_tools()
    
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
