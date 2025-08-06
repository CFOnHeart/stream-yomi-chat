"""
Example of how to create a new agent type using the extensible architecture.
This demonstrates creating a CodeAgent that specializes in code-related tasks.
"""
from typing import List
from langchain.tools import BaseTool
from langgraph.prebuilt import ToolNode, create_react_agent

from agent.base_agent import BaseAgent
from utils.logger import get_logger

logger = get_logger(__name__)


class CodeAgent(BaseAgent):
    """
    Example agent specialized for code-related tasks.
    Demonstrates how to extend the base agent architecture.
    """
    
    def _initialize_agent(self):
        """Initialize code-specific components."""
        # Get tools specific to code agent
        self.tools = self._get_tools()
        self.tool_node = ToolNode(self.tools) if self.tools else None
        
        # Bind tools to LLM
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm
        
        # Build the graph
        self.graph = self._build_graph()
        
        logger.info(f"CodeAgent initialized with {len(self.tools)} tools")
    
    def _get_tools(self) -> List[BaseTool]:
        """Get tools specific to code agent."""
        # For this example, we'll use the same math tools
        # In a real implementation, you would add code-specific tools here
        from agent.tools.math_tools import get_math_tools
        
        # You could add code-specific tools like:
        # - code_formatter_tool
        # - syntax_checker_tool
        # - code_analyzer_tool
        # - documentation_generator_tool
        
        return get_math_tools()  # Placeholder - replace with actual code tools
    
    def _build_graph(self):
        """Build the LangGraph for code agent."""
        try:
            if self.tools:
                # Use create_react_agent if we have tools
                graph = create_react_agent(self.llm, self.tools)
            else:
                # Simple chat agent without tools
                from langgraph.graph.message import MessageGraph
                
                def call_model(messages):
                    return self.llm_with_tools.invoke(messages)
                
                workflow = MessageGraph()
                workflow.add_node("agent", call_model)
                workflow.set_entry_point("agent")
                graph = workflow.compile()
            
            return graph
        except Exception as e:
            logger.error(f"Failed to create code agent graph: {e}")
            raise