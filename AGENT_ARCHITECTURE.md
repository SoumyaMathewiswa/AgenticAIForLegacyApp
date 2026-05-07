# Agentic Legacy Modernization Architecture

This document describes the architecture, design, and implementation of the `AgenticAIForLegacyApp` repository.
It includes component diagrams, service flow, class and function explanations, deployment guidance, and AWS-free demo details.

---

## Overview

This repo demonstrates a modern approach to upgrading legacy systems by layering an AI agent on top of existing APIs rather than rewriting the legacy application.

The architecture is built around:

- **Legacy System**: Existing e-commerce REST API built with FastAPI and PostgreSQL.
- **MCP Gateway**: A bridge that converts legacy REST endpoints into agent-invokable tools.
- **Agent Runtime**: A Bedrock-compatible runtime that performs reasoning, tool selection, and session management.
- **Redis Session Store**: Holds conversation context and state across invocations.
- **Demo Mode**: A local mock agent flow to validate the architecture without AWS credentials.

---

## Architecture Diagram

```mermaid
flowchart TD
    User[End User / Client]
    AgentRuntime[Agent Runtime\n(FastAPI Bedrock Runtime)]
    MCPGateway[MCP Gateway\n(FastAPI Tool Bridge)]
    Legacy[Legacy System\n(FastAPI E-commerce API)]
    Redis[Redis Session Store]
    Postgres[PostgreSQL Database]

    User -->|1. Send user query| AgentRuntime
    AgentRuntime -->|2. Load session data| Redis
    AgentRuntime -->|3. Discover tools| MCPGateway
    AgentRuntime -->|4. Reason & choose tool| Bedrock[Bedrock / LLM logic]
    AgentRuntime -->|5. Invoke tool| MCPGateway
    MCPGateway -->|6. Translate and call API| Legacy
    Legacy -->|7. Data / business logic| Postgres
    Legacy -->|8. Tool output| MCPGateway
    MCPGateway -->|9. Return tool result| AgentRuntime
    AgentRuntime -->|10. Persist session| Redis
    AgentRuntime -->|11. Respond to user| User

    classDef storage fill:#f9f,stroke:#333,stroke-width:1px
    class Redis,Postgres storage
``` 

---

## Component Design

### 1. Legacy System (`legacy_system/app.py`)

This component simulates a legacy e-commerce backend and exposes standard REST endpoints. It is intentionally simple and stable, representing a system that should remain unchanged.

Key endpoints:

- `GET /health`
- `GET /api/products`
- `POST /api/products`
- `GET /api/users`
- `POST /api/users`
- `POST /api/cart/add`
- `GET /api/cart/{user_id}`

Responsibilities:
- Manage products, users, shopping carts
- Perform validation and persistence
- Expose API operations that the agent can call via the MCP Gateway

### 2. MCP Gateway (`gateway/app.py`)

The MCP Gateway converts legacy API operations into a toolset that the AI agent can use.

Responsibilities:
- Provide a tool registry
- Authenticate requests with JWT
- Convert tool invocation into legacy API calls
- Return structured results to the agent

Main endpoints:

- `GET /health`
- `GET /tools`
- `POST /invoke-tool`

The gateway maintains a `TOOL_REGISTRY` with tool definitions and maps them to legacy API routes.

### 3. Agent Runtime (`bedrock_runtime/app.py`)

The runtime executes the agent interaction loop and stores session state.

Responsibilities:
- Validate JWT bearer tokens
- Load and persist session history in Redis
- Instantiate the agent and process messages
- Expose runtime endpoints for health, invocation, and session management

Main endpoints:

- `GET /health`
- `POST /invocations`
- `GET /sessions/{session_id}`
- `DELETE /sessions/{session_id}`

### 4. Agent Logic (`agent/agent.py`)

This module contains the main agent behavior and tool orchestration logic.

Responsibilities:
- Discover available tools
- Build a prompt for the model
- Call Bedrock (or a mock fallback)
- Parse tool calls from model output
- Execute tools through the MCP Gateway
- Loop until no tool calls remain or maximum iterations are reached

### 5. Demo Mode (`demo_agent.py`)

A local demonstration script that simulates agent reasoning without requiring AWS credentials.

Responsibilities:
- Show agent reasoning and tool selection
- Simulate responses for common shopping queries
- Validate architecture without a real LLM backend

---

## Runtime Flow

1. User sends a message to `POST /invocations`
2. Runtime validates JWT and loads session history from Redis
3. Runtime creates `Agent` and calls `process_message()`
4. Agent discovers tools via `GET /tools`
5. Agent builds a prompt and calls LLM via `_call_bedrock()`
6. LLM responds with either plain text or structured `TOOL_CALL`
7. Agent parses tool calls and executes them through MCP Gateway
8. Gateway translates tool calls into legacy API requests
9. Legacy system returns results from PostgreSQL
10. Agent appends results to conversation history and repeats if needed
11. Runtime saves the updated session to Redis
12. Runtime returns final user-facing response

---

## File and Class Documentation

### `agent/agent.py`

#### `class Tool`

A simple neutral model that describes agent tools.

- `name: str` — The tool identifier used by the agent
- `description: str` — A human-readable description of what the tool does
- `inputs: Dict[str, str]` — A map of expected input parameter names and types

Methods:

- `to_dict()` — Returns the tool definition as a dictionary. Useful for logging, prompt rendering, or debugging.

#### `class Agent`

The core agent logic. It orchestrates reasoning, tool discovery, tool execution, and conversation history tracking.

Constructor arguments:

- `bedrock_client` — Optional injected Bedrock runtime client
- `mcp_gateway_url` — URL for the MCP Gateway

Key fields:

- `self.bedrock_client` — AWS Bedrock runtime client, created by `boto3` if not provided
- `self.mcp_gateway_url` — URL for tool discovery and invocation
- `self.jwt_token` — JWT token used for gateway authentication
- `self.model_id` — Bedrock model ID for inference
- `self.max_iterations` — Maximum reasoning loop iterations
- `self.temperature` — LLM temperature parameter

Methods:

- `get_available_tools()`
  - Fetches the tool registry from the MCP Gateway
  - Returns a list of `Tool` objects

- `invoke_tool(tool_name, inputs)`
  - Sends a tool invocation request to `POST /invoke-tool`
  - Returns the tool response payload

- `_build_system_prompt(tools)`
  - Builds the prompt text returned to the model
  - Includes tool descriptions and reasoning instructions

- `_call_bedrock(messages, tools)`
  - Makes the actual Bedrock request
  - Formats the request body with system prompt and conversation history
  - Parses the model response and returns raw text

- `_extract_tool_calls(response)`
  - Parses model output looking for `TOOL_CALL:` markers
  - Produces a list of tool call dictionaries for execution

- `process_message(user_message, conversation_history)`
  - Main entry point for the agent
  - Adds user input to history
  - Discovers tools and loops through reasoning steps
  - Executes tools, appends results, and finalizes the response

### `bedrock_runtime/app.py`

This file is the runtime service that exposes the production API.

Important functions and classes:

- `InvocationRequest` — request model for `/invocations`
- `InvocationResponse` — response model with session, response text, timestamp, and tools used

- `validate_token(credentials)`
  - Ensures incoming requests have valid bearer token authentication

- `get_session(session_id)`
  - Retrieves session history from Redis

- `save_session(session_id, history)`
  - Persists conversation history into Redis with TTL

- `startup_event()`
  - Logs runtime startup information and configured endpoints

- `/health`
  - Returns runtime health plus configured MCP Gateway and Redis status

- `/invocations`
  - Accepts user messages, processes them through the agent, and persists session state

- `/sessions/{session_id}`
  - Returns session metadata and last activity

- `/sessions/{session_id}` DELETE
  - Clears session state from Redis

### `gateway/app.py`

This file is the MCP Gateway, which turns legacy endpoints into agent tools.

Key functions and data:

- `TOOL_REGISTRY`
  - Static tool definitions for the agent
  - Contains tool name, description, method, path, and input schema

- `validate_token(credentials)`
  - Authenticates inbound requests using JWT bearer token

- `/tools`
  - Returns the `TOOL_REGISTRY`

- `/invoke-tool`
  - Converts a tool invocation into a REST call to the legacy system
  - Supports path templating for user-specific endpoints
  - Returns tool outputs after calling the legacy API

### `legacy_system/app.py`

This file provides the legacy backend functionality.

Key models:

- `Product`
- `User`
- `ShoppingCart`

Endpoints:

- `list_products()`
  - Filters by category, max price, and free-text query

- `create_product()`
  - Creates product records

- `list_users()`
  - Returns all users

- `create_user()`
  - Creates a new user, with basic duplicate validation

- `add_to_cart()`
  - Adds or updates a cart item for a user

- `get_cart()`
  - Returns cart contents for a specific user

---

## Deployment and Testing

### Required services

The repository includes a `docker-compose.yml` with:

- `postgres` for data persistence
- `redis` for session storage
- `legacy-system` for the legacy API
- `mcp-gateway` for the tool adapter
- `agent-runtime` for the AI runtime

### Running the full stack

```bash
cp .env.example .env
# fill AWS credentials only if you want Bedrock
docker compose up -d --build
```

### Testing without AWS

The architecture supports validation without AWS credentials by using `demo_agent.py`.

```bash
python demo_agent.py
```

This file demonstrates core agent behavior and tool usage without requiring a real model.

### Real runtime test

If AWS credentials are available, the runtime can be tested with:

```bash
curl -X POST http://localhost:8001/invocations \
  -H "Authorization: Bearer test-token-12345" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-session","message":"Show me laptops under $2000"}'
```

---

## Design Patterns Used

- **Adapter Pattern**: MCP Gateway adapts legacy REST APIs into tool calls
- **Agentic Loop**: The agent reasons, acts, observes results, and plans next steps
- **Session Persistence**: Redis stores conversation history for stateful interactions
- **Configuration-driven architecture**: environment variables drive runtime selection
- **Mock / fallback mode**: `demo_agent.py` proves the same architecture without LLM access

---

## Notes and Next Steps

### Real AI integration
- Add actual AWS credentials and ensure `BEDROCK_MODEL_ID` is valid
- Optionally add a local model fallback to `agent/agent.py`

### Improvements
- Use structured tool outputs rather than text parsing
- Add OpenAPI generation for the tool registry
- Add telemetry / tracing for each tool invocation
- Expand tool registry with more legacy capabilities
- Add a frontend UI or chat client on top of `/invocations`

---

## Summary

This repository demonstrates a practical, low-risk modernization strategy:

- Keep the legacy system unchanged
- Build a bridge layer with MCP Gateway
- Wrap an AI decision engine around the legacy APIs
- Use session storage for stateful user conversations
- Provide AWS-free demo mode for architecture validation

The result is a modular platform that can scale from testing to real production AI-powered legacy augmentation.
