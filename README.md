# Conversation Agent Backend Service

A FastAPI-based conversation agent backend service built with LangGraph + LangChain, featuring multi-model support, tool calling, streaming responses, and intelligent memory management.

## 🚀 Features

- **Multi-Model Support**: Azure OpenAI, OpenAI, and Google Generative AI
- **Tool Calling**: Built-in math tools with extensible architecture
- **Streaming Responses**: Real-time streaming via Server-Sent Events (SSE)
- **Intelligent Memory**: Automatic conversation compression when context exceeds limits
- **Session Management**: Persistent chat history with SQLite storage
- **Flexible Configuration**: YAML-based model and provider configuration
- **Comprehensive Logging**: Structured logging with configurable levels

## 🛠️ Technology Stack

- **Web Framework**: FastAPI
- **Agent Framework**: LangGraph + LangChain
- **Database**: SQLite
- **Environment Management**: Python virtual environment
- **Configuration**: YAML files

## 📁 Project Structure

```
stream-yomi-chatbot/
├── main.py                     # Application entry point
├── agent/
│   ├── builder.py             # Main agent implementation
│   ├── memory.py              # Memory management and compression
│   ├── tools/
│   │   └── math_tools.py      # Math tools (add, subtract, multiply, divide)
│   ├── models/
│   │   └── loader.py          # Model loading for different providers
│   └── config/
│       ├── llm_config.yaml    # LLM model configuration
│       └── embedding_config.yaml # Embedding model configuration
├── database/
│   ├── interface.py           # Database abstraction layer
│   └── chat_history.db        # SQLite database (created automatically)
├── api/
│   └── routes.py              # FastAPI routes and endpoints
├── utils/
│   └── logger.py              # Logging utilities
└── README.md                  # This file
```

## 🚀 Quick Start

### 1. Environment Setup

The project uses Python virtual environment. Ensure you have Python 3.13+ installed:

```bash
# The virtual environment should already be configured
# Dependencies are managed via pyproject.toml and installed
```

### 2. Configuration

Edit the configuration files in `agent/config/`:

**`agent/config/llm_config.yaml`**:
```yaml
llm:
  provider: azure  # azure, openai, google
  model: gpt-4.1
  api_key: YOUR_AZURE_OPENAI_KEY
  endpoint: https://your-endpoint.openai.azure.com/
  api_version: "2024-02-15-preview"
  temperature: 0.7
  max_tokens: 2000

embedding:
  provider: azure
  model: text-embedding-ada-002
  api_key: YOUR_AZURE_OPENAI_KEY
  endpoint: https://your-endpoint.openai.azure.com/
  api_version: "2024-02-15-preview"
```

### 3. Run the Service

```bash
# Run the FastAPI server
python main.py
```

The service will start on `http://localhost:8000`

### 4. API Documentation

Once running, visit:
- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## 📡 API Endpoints

### Main Chat Endpoint

**POST `/chat/stream`** - Streaming chat with tool calling
```json
{
  "message": "What is 15 multiplied by 8?",
  "session_id": "optional-session-id",
  "stream": true
}
```

**POST `/chat`** - Complete response (non-streaming)
```json
{
  "message": "Calculate 25 + 17",
  "session_id": "optional-session-id"
}
```

### Session Management

- **GET `/session/{session_id}`** - Get session information
- **DELETE `/session/{session_id}/clear`** - Clear session history

### Utility Endpoints

- **GET `/`** - Service information
- **GET `/health`** - Health check
- **GET `/tools`** - List available tools

## 🧮 Available Tools

The system includes 4 math tools for testing:

1. **add(a, b)** - Add two numbers
2. **subtract(a, b)** - Subtract two numbers
3. **multiply(a, b)** - Multiply two numbers
4. **divide(a, b)** - Divide two numbers (with zero-division protection)

## 💾 Memory Management

The system automatically manages conversation memory:

- **≤ 3200 characters**: Normal message storage
- **> 3200 characters**: Automatic compression using LLM summarization
- **Persistent Storage**: Original messages stored in SQLite
- **In-Memory Compression**: Summaries used only for context, not stored

## 🗄️ Database Design

SQLite database structure:

```sql
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    message_type TEXT NOT NULL,  -- 'human', 'ai', 'tool_call', 'system'
    content TEXT NOT NULL,
    metadata TEXT,               -- JSON metadata
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    character_count INTEGER
);
```

## 🔧 Configuration Examples

### Azure OpenAI Configuration
```yaml
llm:
  provider: azure
  model: gpt-4.1
  api_key: YOUR_AZURE_KEY
  endpoint: https://your-endpoint.openai.azure.com/
  api_version: "2024-02-15-preview"
```

### OpenAI Configuration
```yaml
llm:
  provider: openai
  model: gpt-4o
  api_key: YOUR_OPENAI_KEY
```

### Google AI Configuration
```yaml
llm:
  provider: google
  model: gemini-pro
  api_key: YOUR_GOOGLE_API_KEY
```

## 🧪 Testing the Service

### Using curl

**Stream chat:**
```bash
curl -X POST "http://localhost:8000/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 12 * 7?", "stream": true}'
```

**Complete chat:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 50 / 2"}'
```

### Example Responses

**Tool calling example:**
```
User: "What is 15 + 25?"
Response: Uses add tool → Returns: "15 + 25 = 40"
```

**Regular conversation:**
```
User: "Hello, how are you?"
Response: "Hello! I'm doing well, thank you for asking. How can I help you today?"
```

## 🔧 Development

### Adding New Tools

1. Create tool functions in `agent/tools/`
2. Use `@tool` decorator from LangChain
3. Add to `get_tools()` function
4. Update agent builder to include new tools

### Adding New Model Providers

1. Extend `ModelLoader` class in `agent/models/loader.py`
2. Add provider-specific loading methods
3. Update configuration schema

### Extending Database

1. Implement `DatabaseInterface` in `database/interface.py`
2. Add new database type to factory function
3. Update configuration as needed

## 📝 Logging

The system uses structured logging:

- **Console Output**: Formatted with timestamps
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Module-specific**: Each module has its own logger
- **No Print Statements**: All output through logging framework

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **API Key Issues**: Check configuration files for correct keys
3. **Database Errors**: Ensure write permissions for database directory
4. **Streaming Issues**: Check network connectivity and browser SSE support

### Debug Mode

Enable debug logging by modifying the logger setup:

```python
logger = setup_logger(__name__, level="DEBUG")
```

## 🚀 Production Deployment

For production deployment:

1. **Environment Variables**: Use environment variables for API keys
2. **Database**: Consider PostgreSQL for production scale
3. **CORS**: Configure appropriate CORS settings
4. **Load Balancing**: Use proper load balancer for scaling
5. **Monitoring**: Add health checks and monitoring
6. **Security**: Implement authentication and rate limiting

## 📄 License

This project is part of a personal development initiative. Please refer to your organization's guidelines for usage and distribution.

## 🤝 Contributing

1. Follow the existing code structure
2. Add comprehensive logging
3. Write tests for new features
4. Update documentation
5. Follow Python best practices

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error details
3. Ensure configuration is correct
4. Test with simple examples first
