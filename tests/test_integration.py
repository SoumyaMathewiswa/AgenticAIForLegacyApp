"""Integration tests for the Bedrock legacy integration system."""

import os

import pytest
import requests


@pytest.fixture
def headers():
    """JWT auth headers for API calls."""
    return {"Authorization": f"Bearer test-token-12345"}


@pytest.fixture
def legacy_url():
    return os.getenv("LEGACY_SYSTEM_URL", "http://localhost:8000")


@pytest.fixture
def gateway_url():
    return os.getenv("MCP_GATEWAY_URL", "http://localhost:8002")


@pytest.fixture
def runtime_url():
    return os.getenv("AGENT_RUNTIME_URL", "http://localhost:8001")


class TestLegacySystem:
    """Test the legacy e-commerce system endpoints."""

    def test_legacy_health(self, legacy_url):
        response = requests.get(f"{legacy_url}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_list_products(self, legacy_url):
        response = requests.get(f"{legacy_url}/api/products")
        assert response.status_code == 200
        products = response.json()
        assert len(products) > 0
        assert "name" in products[0]
        assert "price" in products[0]

    def test_filter_products_by_category(self, legacy_url):
        response = requests.get(f"{legacy_url}/api/products?category=laptops")
        assert response.status_code == 200
        products = response.json()
        assert all(p["category"].lower() == "laptops" for p in products)

    def test_create_product(self, legacy_url):
        payload = {
            "name": "Test Laptop",
            "category": "laptops",
            "price": 1500.00,
            "stock": 5,
        }
        response = requests.post(f"{legacy_url}/api/products", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Laptop"
        assert data["price"] == 1500.00

    def test_list_users(self, legacy_url):
        response = requests.get(f"{legacy_url}/api/users")
        assert response.status_code == 200
        users = response.json()
        assert len(users) > 0

    def test_create_user(self, legacy_url):
        payload = {
            "username": "testuser",
            "email": "testuser@example.com",
            "full_name": "Test User",
        }
        response = requests.post(f"{legacy_url}/api/users", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"

    def test_add_to_cart(self, legacy_url):
        payload = {"user_id": 1, "product_id": 1, "quantity": 2}
        response = requests.post(f"{legacy_url}/api/cart/add", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_get_cart(self, legacy_url):
        response = requests.get(f"{legacy_url}/api/cart/1")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 1
        assert "items" in data


class TestMCPGateway:
    """Test the MCP Gateway endpoints."""

    def test_gateway_health(self, gateway_url, headers):
        response = requests.get(f"{gateway_url}/health", headers=headers)
        assert response.status_code == 200

    def test_list_tools(self, gateway_url, headers):
        response = requests.get(f"{gateway_url}/tools", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        tools = data["tools"]
        assert len(tools) > 0
        assert any(t["name"] == "list_products" for t in tools)
        assert any(t["name"] == "add_to_cart" for t in tools)

    def test_invoke_list_products_tool(self, gateway_url, headers):
        payload = {"tool_name": "list_products", "inputs": {"category": "laptops"}}
        response = requests.post(f"{gateway_url}/invoke-tool", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "outputs" in data

    def test_unauthorized_access(self, gateway_url):
        response = requests.get(f"{gateway_url}/tools")
        assert response.status_code == 401

    def test_invalid_tool(self, gateway_url, headers):
        payload = {"tool_name": "nonexistent_tool", "inputs": {}}
        response = requests.post(f"{gateway_url}/invoke-tool", json=payload, headers=headers)
        assert response.status_code == 404


class TestAgentRuntime:
    """Test the Bedrock Agent Runtime endpoints."""

    def test_runtime_health(self, runtime_url, headers):
        response = requests.get(f"{runtime_url}/health", headers=headers)
        assert response.status_code == 200

    def test_health_without_auth(self, runtime_url):
        response = requests.get(f"{runtime_url}/health")
        assert response.status_code == 200

    def test_invoke_agent(self, runtime_url, headers):
        payload = {"session_id": "test-session", "message": "List products"}
        response = requests.post(f"{runtime_url}/invocations", json=payload, headers=headers, timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["session_id"] == "test-session"

    def test_session_persistence(self, runtime_url, headers):
        session_id = "persistence-test"
        payload1 = {"session_id": session_id, "message": "First message"}
        response1 = requests.post(f"{runtime_url}/invocations", json=payload1, headers=headers, timeout=30)
        assert response1.status_code == 200

        # Retrieve session
        response2 = requests.get(f"{runtime_url}/sessions/{session_id}", headers=headers)
        assert response2.status_code == 200

    def test_unauthorized_invocation(self, runtime_url):
        payload = {"session_id": "test", "message": "test"}
        response = requests.post(f"{runtime_url}/invocations", json=payload)
        assert response.status_code == 401

    def test_clear_session(self, runtime_url, headers):
        session_id = "clear-test"
        payload = {"session_id": session_id, "message": "test"}
        requests.post(f"{runtime_url}/invocations", json=payload, headers=headers, timeout=30)

        response = requests.delete(f"{runtime_url}/sessions/{session_id}", headers=headers)
        assert response.status_code == 200


def test_mcp_gateway_invoke_tool():
    """Test invoking a tool through MCP gateway."""
    headers = {"Authorization": "Bearer test-token-12345"}
    payload = {
        "tool_name": "list_products",
        "inputs": {}
    }
    response = requests.post("http://localhost:8002/invoke-tool", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "tool_name" in data
    assert "outputs" in data


def test_agent_runtime_health():
    """Test agent runtime health endpoint."""
    response = requests.get("http://localhost:8001/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_agent_runtime_invocation():
    """Test invoking the agent through runtime."""
    headers = {"Authorization": "Bearer test-token-12345"}
    payload = {
        "session_id": "test-session-123",
        "message": "Show me all laptops"
    }
    response = requests.post("http://localhost:8001/invocations", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "response" in data
    assert "tools_used" in data


def test_end_to_end_workflow():
    """Test complete end-to-end workflow."""
    headers = {"Authorization": "Bearer test-token-12345"}

    # Step 1: Create a user
    user_data = {
        "username": "alice_test",
        "email": "alice_test@example.com",
        "full_name": "Alice Test"
    }
    response = requests.post("http://localhost:8000/api/users", json=user_data)
    assert response.status_code == 201
    user = response.json()
    user_id = user["id"]

    # Step 2: Get a product
    response = requests.get("http://localhost:8000/api/products?category=laptops")
    assert response.status_code == 200
    products = response.json()
    assert len(products) > 0
    product_id = products[0]["id"]

    # Step 3: Use agent to add to cart
    payload = {
        "session_id": "e2e-test-session",
        "message": f"Add product {product_id} to cart for user {user_id}"
    }
    response = requests.post("http://localhost:8001/invocations", json=payload, headers=headers)
    assert response.status_code == 200

    # Step 4: Verify cart was updated
    response = requests.get(f"http://localhost:8000/api/cart/{user_id}")
    assert response.status_code == 200
    cart = response.json()
    assert cart["user_id"] == user_id
    assert len(cart["items"]) > 0