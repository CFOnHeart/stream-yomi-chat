"""
FastAPI routes for the Conversation Agent backend.
Provides endpoints for chat streaming and session management.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import asyncio
from pathlib import Path

from agent.builder import ConversationAgent
from utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Conversation Agent API",
    description="A conversation agent backend with streaming support, tool calling, and memory management",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the conversation agent
config_path = Path("agent/config/llm_config.yaml")
agent = ConversationAgent(str(config_path))


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    session_id: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    """Response model for non-streaming chat."""
    response: str
    session_id: str
    tool_calls: list = []


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Conversation Agent API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat_stream": "/chat/stream",
            "chat": "/chat",
            "session_info": "/session/{session_id}",
            "clear_session": "/session/{session_id}/clear"
        }
    }


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat response with tool calling support.
    
    This is the main endpoint for conversational interaction.
    Supports Server-Sent Events (SSE) streaming.
    """
    logger.info(f"Received streaming chat request: {request.message[:100]}...")
    
    async def generate_stream():
        """Generate SSE stream."""
        try:
            async for chunk in agent.chat_stream(
                message=request.message,
                session_id=request.session_id
            ):
                # Format as SSE
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"
                
                # 强制刷新缓冲区，确保数据立即发送
                await asyncio.sleep(0)  # 让出控制权，确保数据发送
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_data = json.dumps({
                "type": "error",
                "content": f"Streaming error: {str(e)}"
            })
            yield f"data: {error_data}\n\n"
        
        finally:
            # Send completion signal
            yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            "Transfer-Encoding": "chunked",  # 确保分块传输
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_complete(request: ChatRequest):
    """
    Complete chat response (non-streaming).
    
    Returns the full response at once instead of streaming.
    """
    logger.info(f"Received complete chat request: {request.message[:100]}...")
    
    try:
        response_content = ""
        tool_calls = []
        session_id = request.session_id
        
        async for chunk in agent.chat_stream(
            message=request.message,
            session_id=request.session_id
        ):
            if chunk["type"] == "message":
                response_content += chunk["content"]
            elif chunk["type"] == "tool_call":
                tool_calls.append(chunk)
            elif chunk["type"] == "session_info":
                session_id = chunk["session_id"]
        
        return ChatResponse(
            response=response_content,
            session_id=session_id,
            tool_calls=tool_calls
        )
    
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Get information about a specific session.
    
    Returns statistics and metadata about the session.
    """
    try:
        info = agent.get_session_info(session_id)
        return {
            "session_id": session_id,
            **info
        }
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}/clear")
async def clear_session(session_id: str):
    """
    Clear all messages for a specific session.
    
    This removes all chat history for the session.
    """
    try:
        agent.clear_session(session_id)
        logger.info(f"Cleared session: {session_id}")
        return {
            "message": f"Session {session_id} cleared successfully",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Conversation Agent API"
    }


@app.get("/tools")
async def list_tools():
    """List available tools."""
    tools_info = []
    for tool in agent.tools:
        tools_info.append({
            "name": tool.name,
            "description": tool.description,
            "args_schema": tool.args if hasattr(tool, 'args') else None
        })
    
    return {
        "tools": tools_info,
        "count": len(tools_info)
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return HTTPException(
        status_code=500,
        detail="Internal server error"
    )
