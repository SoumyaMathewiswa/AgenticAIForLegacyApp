"""Bedrock AgentCore runtime service.

This module exposes the runtime API for the agent, including invocation,
session management, and health status. It connects the agent logic to
Redis-based session storage and the MCP gateway.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import redis
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from agent.agent import Agent

app = FastAPI(title="Bedrock AgentCore Runtime", version="0.1")

JWT_SECRET = os.getenv("JWT_SECRET", "test-token-12345")
MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL", "http://mcp-gateway:8002")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SESSION_EXPIRY = int(os.getenv("SESSION_EXPIRY", "3600"))

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

security = HTTPBearer(auto_error=False)


class InvocationRequest(BaseModel):
    """Schema for agent invocation requests."""

    session_id: str
    message: str


class InvocationResponse(BaseModel):
    """Schema for agent invocation responses."""

    session_id: str
    response: str
    timestamp: str
    tools_used: List[Dict] = []


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or credentials.scheme.lower() != "bearer" or credentials.credentials != JWT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")
    return credentials.credentials


def get_session(session_id: str) -> list:
    """Retrieve conversation history from Redis."""
    key = f"session:{session_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return []


def save_session(session_id: str, history: list):
    """Save conversation history to Redis."""
    key = f"session:{session_id}"
    redis_client.setex(key, SESSION_EXPIRY, json.dumps(history))


@app.on_event("startup")
def startup_event():
    print("Starting Bedrock AgentCore Runtime")
    print(f"MCP Gateway: {MCP_GATEWAY_URL}")
    print(f"Redis: {'Connected' if redis_client else 'Disabled'}")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mcp_gateway": MCP_GATEWAY_URL,
        "redis": "connected" if redis_client else "disabled",
    }


@app.post("/invocations", response_model=InvocationResponse)
def invoke_agent(payload: InvocationRequest, token: str = Depends(validate_token)):
    """Invoke the agent with a user message and return the response."""
    try:
        # Get existing conversation history
        conversation_history = get_session(payload.session_id)

        # Create agent instance
        agent = Agent(mcp_gateway_url=MCP_GATEWAY_URL)

        # Process the message
        result = agent.process_message(payload.message, conversation_history)

        # Save updated conversation history
        save_session(payload.session_id, result["conversation_history"])

        return InvocationResponse(
            session_id=payload.session_id,
            response=result["response"],
            timestamp=datetime.utcnow().isoformat(),
            tools_used=result.get("tools_used", []),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")


@app.get("/sessions/{session_id}")
def get_session_info(session_id: str, token: str = Depends(validate_token)):
    history = get_session(session_id)
    return {
        "session_id": session_id,
        "message_count": len([msg for msg in history if msg["role"] == "user"]),
        "last_activity": history[-1] if history else None,
    }


@app.delete("/sessions/{session_id}")
def clear_session(session_id: str, token: str = Depends(validate_token)):
    key = f"session:{session_id}"
    redis_client.delete(key)
    return {"status": "cleared", "session_id": session_id}