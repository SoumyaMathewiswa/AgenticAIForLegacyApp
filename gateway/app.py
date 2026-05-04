import os
from typing import Any, Dict, List

import requests
from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

app = FastAPI(title="MCP Gateway", version="0.1")

JWT_SECRET = os.getenv("JWT_SECRET", "test-token-12345")
LEGACY_SYSTEM_URL = os.getenv("LEGACY_SYSTEM_URL", "http://legacy-system:8000")
security = HTTPBearer(auto_error=False)

TOOL_REGISTRY: List[Dict[str, Any]] = [
    {
        "name": "list_products",
        "description": "List products from the legacy catalog using filters.",
        "inputs": {"category": "string", "max_price": "number", "query": "string"},
        "method": "GET",
        "path": "/api/products",
    },
    {
        "name": "create_user",
        "description": "Create a new user account in the legacy system.",
        "inputs": {"username": "string", "email": "string", "full_name": "string"},
        "method": "POST",
        "path": "/api/users",
    },
    {
        "name": "list_users",
        "description": "List known users in the legacy system.",
        "inputs": {},
        "method": "GET",
        "path": "/api/users",
    },
    {
        "name": "add_to_cart",
        "description": "Add a product to a user's shopping cart.",
        "inputs": {"user_id": "integer", "product_id": "integer", "quantity": "integer"},
        "method": "POST",
        "path": "/api/cart/add",
    },
    {
        "name": "get_cart",
        "description": "Fetch the shopping cart contents for a user.",
        "inputs": {"user_id": "integer"},
        "method": "GET",
        "path": "/api/cart/{user_id}",
    },
]


class ToolRequest(BaseModel):
    tool_name: str
    inputs: Dict[str, Any] = {}


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or credentials.scheme.lower() != "bearer" or credentials.credentials != JWT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")
    return credentials.credentials


@app.get("/health")
def health():
    return {"status": "ok", "legacy_system": LEGACY_SYSTEM_URL}


@app.get("/tools")
def list_tools(token: str = Depends(validate_token)):
    return {"tools": TOOL_REGISTRY}


@app.post("/invoke-tool")
def invoke_tool(payload: ToolRequest, token: str = Depends(validate_token)):
    tool = next((item for item in TOOL_REGISTRY if item["name"] == payload.tool_name), None)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {payload.tool_name}")

    url = f"{LEGACY_SYSTEM_URL}{tool['path']}"
    method = tool["method"].upper()
    params = payload.inputs if method == "GET" else None
    json_body = payload.inputs if method == "POST" else None

    if "{user_id}" in tool["path"]:
        if "user_id" not in payload.inputs:
            raise HTTPException(status_code=400, detail="user_id is required for get_cart")
        url = url.format(user_id=payload.inputs["user_id"])

    response = requests.request(method, url, params=params, json=json_body, timeout=10)
    try:
        data = response.json()
    except ValueError:
        data = response.text
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=data)
    return {"tool_name": payload.tool_name, "outputs": data}
