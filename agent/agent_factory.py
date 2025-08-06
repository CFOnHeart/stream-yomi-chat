"""
Agent factory for creating different types of agents.
Provides a centralized way to create and manage agent instances.
"""
from typing import Dict, Type
from agent.base_agent import BaseAgent
from agent.conversation_agent import ConversationAgent
from agent.code_agent import CodeAgent
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentFactory:
    """Factory class for creating different types of agents."""
    
    # Registry of available agent types
    _agent_types: Dict[str, Type[BaseAgent]] = {
        'conversation': ConversationAgent,
        'code': CodeAgent
        # Add more agent types here as they are created
    }
    
    @classmethod
    def create_agent(cls, agent_type: str, config_path: str, **kwargs) -> BaseAgent:
        """
        Create an agent of the specified type.
        
        Args:
            agent_type: Type of agent to create ('conversation', etc.)
            config_path: Path to configuration file
            **kwargs: Additional parameters for agent initialization
            
        Returns:
            An instance of the specified agent type
            
        Raises:
            ValueError: If agent_type is not supported
        """
        if agent_type not in cls._agent_types:
            available_types = list(cls._agent_types.keys())
            raise ValueError(f"Unsupported agent type: {agent_type}. Available types: {available_types}")
        
        agent_class = cls._agent_types[agent_type]
        logger.info(f"Creating {agent_type} agent with config: {config_path}")
        
        try:
            # Create the agent instance
            agent = agent_class(config_path, **kwargs)
            logger.info(f"Successfully created {agent_type} agent")
            return agent
        except Exception as e:
            logger.error(f"Failed to create {agent_type} agent: {e}")
            raise
    
    @classmethod
    def get_available_agent_types(cls) -> list:
        """Get list of available agent types."""
        return list(cls._agent_types.keys())
    
    @classmethod
    def get_agent_info(cls, agent_type: str) -> Dict[str, str]:
        """
        Get information about a specific agent type.
        
        Args:
            agent_type: Type of agent to get info for
            
        Returns:
            Dictionary with agent information
        """
        if agent_type not in cls._agent_types:
            return {}
        
        agent_class = cls._agent_types[agent_type]
        return {
            'name': agent_type,
            'class_name': agent_class.__name__,
            'module': agent_class.__module__,
            'description': agent_class.__doc__ or 'No description available'
        }


# Convenience function for backward compatibility
def create_conversation_agent(config_path: str) -> ConversationAgent:
    """
    Create a conversation agent (backward compatibility function).
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        ConversationAgent instance
    """
    return AgentFactory.create_agent('conversation', config_path)
