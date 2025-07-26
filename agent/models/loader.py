"""
Model configuration and loading utilities.
Provides unified interface for different LLM and embedding providers.
"""
import yaml
from typing import Dict, Any, Union
from pathlib import Path

from langchain_openai import ChatOpenAI, AzureChatOpenAI, OpenAIEmbeddings, AzureOpenAIEmbeddings
from langchain.schema.language_model import BaseLanguageModel
from langchain.embeddings.base import Embeddings

# Optional Google import
try:
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    ChatGoogleGenerativeAI = None
    GoogleGenerativeAIEmbeddings = None

from utils.logger import get_logger

logger = get_logger(__name__)


class ModelLoader:
    """Unified model loader for different providers."""
    
    def __init__(self, config_path: str):
        """
        Initialize model loader with config file.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                logger.info(f"Loaded configuration from {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            raise
    
    def load_llm(self) -> BaseLanguageModel:
        """Load LLM model based on configuration."""
        llm_config = self.config.get('llm', {})
        provider = llm_config.get('provider', '').lower()
        
        if provider == 'azure':
            return self._load_azure_llm(llm_config)
        elif provider == 'openai':
            return self._load_openai_llm(llm_config)
        elif provider == 'google':
            if not GOOGLE_AVAILABLE:
                raise ValueError("Google Generative AI not available. Install langchain-google-genai package.")
            return self._load_google_llm(llm_config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def load_embedding(self) -> Embeddings:
        """Load embedding model based on configuration."""
        embedding_config = self.config.get('embedding', {})
        provider = embedding_config.get('provider', '').lower()
        
        if provider == 'azure':
            return self._load_azure_embedding(embedding_config)
        elif provider == 'openai':
            return self._load_openai_embedding(embedding_config)
        elif provider == 'google':
            if not GOOGLE_AVAILABLE:
                raise ValueError("Google Generative AI not available. Install langchain-google-genai package.")
            return self._load_google_embedding(embedding_config)
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    def _load_azure_llm(self, config: Dict[str, Any]) -> AzureChatOpenAI:
        """Load Azure OpenAI LLM."""
        return AzureChatOpenAI(
            azure_endpoint=config['endpoint'],
            api_key=config['api_key'],
            api_version=config.get('api_version', '2024-02-15-preview'),
            azure_deployment=config['model'],
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 2000),
            streaming=True
        )
    
    def _load_openai_llm(self, config: Dict[str, Any]) -> ChatOpenAI:
        """Load OpenAI LLM."""
        return ChatOpenAI(
            api_key=config['api_key'],
            model=config['model'],
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 2000),
            streaming=True
        )
    
    def _load_google_llm(self, config: Dict[str, Any]) -> BaseLanguageModel:
        """Load Google Generative AI LLM."""
        return ChatGoogleGenerativeAI(
            google_api_key=config['api_key'],
            model=config['model'],
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 2000)
        )
    
    def _load_azure_embedding(self, config: Dict[str, Any]) -> AzureOpenAIEmbeddings:
        """Load Azure OpenAI embedding."""
        return AzureOpenAIEmbeddings(
            azure_endpoint=config['endpoint'],
            api_key=config['api_key'],
            api_version=config.get('api_version', '2024-02-15-preview'),
            azure_deployment=config['model']
        )
    
    def _load_openai_embedding(self, config: Dict[str, Any]) -> OpenAIEmbeddings:
        """Load OpenAI embedding."""
        return OpenAIEmbeddings(
            api_key=config['api_key'],
            model=config['model']
        )
    
    def _load_google_embedding(self, config: Dict[str, Any]) -> Embeddings:
        """Load Google Generative AI embedding."""
        return GoogleGenerativeAIEmbeddings(
            google_api_key=config['api_key'],
            model=config['model']
        )
