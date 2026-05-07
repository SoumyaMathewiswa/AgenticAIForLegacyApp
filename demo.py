#!/usr/bin/env python3
"""
Interactive demo script for the AI Agent integration with legacy systems.
Demonstrates the agentic loop: Think → Act → Observe → Plan
"""

import json
import os
import sys

import requests

# Configuration
AGENT_RUNTIME_URL = os.getenv("AGENT_RUNTIME_URL", "http://localhost:8001")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "test-token-12345")
SESSION_ID = "demo-session"

headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}


def invoke_agent(message: str) -> str:
    """Send a message to the agent and get a response."""
    payload = {
        "session_id": SESSION_ID,
        "message": message,
    }

    response = requests.post(
        f"{AGENT_RUNTIME_URL}/invocations",
        json=payload,
        headers=headers,
        timeout=30,
    )

    if response.status_code == 200:
        data = response.json()
        return data["response"]
    else:
        return f"Error: {response.status_code} - {response.text}"


def main():
    print("=" * 80)
    print("AI Agent Integration with Legacy E-commerce System")
    print("=" * 80)
    print("\nDemonstrating the agentic loop:")
    print("  Think → Agent interprets intent")
    print("  Act → Agent calls MCP tools")
    print("  Observe → Agent receives tool results")
    print("  Plan → Agent formulates response\n")

    # Example interactions demonstrating different workflows
    examples = [
        {
            "title": "Workflow 1: Product Browsing",
            "message": "Show me laptops under $2000",
        },
        {
            "title": "Workflow 2: Creating a User",
            "message": "Create an account for a new user named David Lee with email david@example.com",
        },
        {
            "title": "Workflow 3: Multi-step Shopping",
            "message": "Can you help me find wireless headphones and add them to my cart? I'm user 1.",
        },
        {
            "title": "Workflow 4: Natural Language Query",
            "message": "What are the best audio products available?",
        },
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n{'-' * 80}")
        print(f"{example['title']}")
        print(f"{'-' * 80}")
        print(f"\nUser: {example['message']}")
        print("\nAgent processing...\n")

        response = invoke_agent(example["message"])
        print(f"Agent: {response}")

        # Retrieve and show session state
        session_response = requests.get(
            f"{AGENT_RUNTIME_URL}/sessions/{SESSION_ID}",
            headers=headers,
        )
        if session_response.status_code == 200:
            session_data = session_response.json()
            if session_data.get("tools_used"):
                print("\n[Tools Used]")
                for tool in session_data["tools_used"]:
                    print(f"  - {tool['tool_name']}")

        # Small delay between requests
        input("\nPress Enter to continue to next example...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

            start_time = time.time()
            response = requests.post(f"{base_url}/invocations", json=payload, headers=headers, timeout=30)
            end_time = time.time()

            if response.status_code == 200:
                data = response.json()
                print(f"Agent: {data['response']}")
                print(f"⏱️  Response time: {end_time - start_time:.2f}s")
                if data.get('tools_used'):
                    print(f"🔧 Tools used: {len(data['tools_used'])}")
                    for tool in data['tools_used']:
                        print(f"   - {tool['tool_name']}: {tool.get('inputs', {})}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")

        time.sleep(1)  # Brief pause between requests

    print("\n" + "=" * 50)
    print("✅ Demo completed!")


def check_services_health():
    """Check if all services are running."""
    services = [
        ("Legacy System", "http://localhost:8000/health"),
        ("MCP Gateway", "http://localhost:8002/health"),
        ("Agent Runtime", "http://localhost:8001/health")
    ]

    print("\n🔍 Checking service health...")
    all_healthy = True

    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: OK")
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                all_healthy = False
        except requests.exceptions.RequestException:
            print(f"❌ {name}: Connection failed")
            all_healthy = False

    return all_healthy


if __name__ == "__main__":
    if check_services_health():
        demo_agent_workflow()
    else:
        print("\n❌ Some services are not running. Please start them with:")
        print("   docker-compose up -d")
        print("   Then run: python demo.py")