"""Agent logic for the Bedrock-compatible AI runtime.

This module implements the behavior of the AI agent that:
- discovers available tools from the MCP gateway
- builds prompts for the model
- invokes Bedrock for reasoning
- parses tool call instructions
- executes tools against the legacy system
- maintains conversational history
"""

import json
import os
from typing import Any, Dict, List, Optional

import boto3
import requests
from pydantic import BaseModel


class Tool:
    """Represents a tool available to the agent.

    A tool is an action the agent can perform through the MCP gateway.
    """

    def __init__(self, name: str, description: str, inputs: Dict[str, str]):
        self.name = name
        self.description = description
        self.inputs = inputs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
        }


class Agent:
    """Main agent class that orchestrates reasoning and tool execution.

    The agent uses a model backend to decide whether to call tools and
    then executes those tools through the MCP Gateway. Conversation history
    is passed to the model so the agent can perform multi-turn reasoning.
    """

    def __init__(self, bedrock_client=None, mcp_gateway_url: str = None):
        self.bedrock_client = bedrock_client or boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
        self.mcp_gateway_url = mcp_gateway_url or os.getenv("MCP_GATEWAY_URL", "http://mcp-gateway:8002")
        self.jwt_token = os.getenv("JWT_SECRET", "test-token-12345")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        self.max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))
        self.temperature = float(os.getenv("AGENT_TEMPERATURE", "0.7"))

    def get_available_tools(self) -> List[Tool]:
        """Fetch available tools from MCP Gateway."""
        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        response = requests.get(f"{self.mcp_gateway_url}/tools", headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return [Tool(name=tool["name"], description=tool["description"], inputs=tool["inputs"]) for tool in data["tools"]]

    def invoke_tool(self, tool_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool via MCP Gateway."""
        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        payload = {"tool_name": tool_name, "inputs": inputs}
        response = requests.post(f"{self.mcp_gateway_url}/invoke-tool", json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()["outputs"]

    def _build_system_prompt(self, tools: List[Tool]) -> str:
        """Build the system prompt with tool descriptions."""
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}\n  Inputs: {', '.join(tool.inputs.keys()) if tool.inputs else 'None'}"
            for tool in tools
        ])

        return f"""You are an intelligent e-commerce assistant that helps users with online shopping.

You have access to the following tools:
{tool_descriptions}

When a user asks something, think step-by-step:
1. Understand the user's intent
2. Determine if you need to use any tools
3. If tools are needed, call them with appropriate parameters
4. Format your final response clearly

Always respond in a helpful, conversational way. If you use tools, explain what you're doing."""

    def _call_bedrock(self, messages: List[Dict[str, str]], tools: List[Tool]) -> str:
        """Call Bedrock with the current conversation."""
        system_prompt = self._build_system_prompt(tools)

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": messages,
        }

        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]

    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract tool calls from the LLM response."""
        # Simple parsing - in production, use structured output
        tool_calls = []
        if "TOOL_CALL:" in response:
            # Parse tool calls from response
            lines = response.split("\n")
            for line in lines:
                if line.startswith("TOOL_CALL:"):
                    try:
                        tool_data = json.loads(line.replace("TOOL_CALL:", "").strip())
                        tool_calls.append(tool_data)
                    except json.JSONDecodeError:
                        continue
        return tool_calls

    def process_message(self, user_message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Process a user message and return the agent response."""
        if conversation_history is None:
            conversation_history = []

        # Add user message to history
        conversation_history.append({"role": "user", "content": user_message})

        tools = self.get_available_tools()

        for iteration in range(self.max_iterations):
            # Get LLM response
            llm_response = self._call_bedrock(conversation_history, tools)

            # Check for tool calls
            tool_calls = self._extract_tool_calls(llm_response)

            if not tool_calls:
                # No tools needed, return final response
                conversation_history.append({"role": "assistant", "content": llm_response})
                return {
                    "response": llm_response,
                    "conversation_history": conversation_history,
                    "tools_used": [],
                }

            # Execute tools
            tools_used = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool_name")
                inputs = tool_call.get("inputs", {})

                try:
                    result = self.invoke_tool(tool_name, inputs)
                    tools_used.append({
                        "tool_name": tool_name,
                        "inputs": inputs,
                        "outputs": result,
                    })

                    # Add tool result to conversation
                    tool_message = f"Tool result for {tool_name}: {json.dumps(result)}"
                    conversation_history.append({"role": "system", "content": tool_message})

                except Exception as e:
                    error_message = f"Tool execution failed for {tool_name}: {str(e)}"
                    conversation_history.append({"role": "system", "content": error_message})
                    tools_used.append({
                        "tool_name": tool_name,
                        "inputs": inputs,
                        "error": str(e),
                    })

        # Max iterations reached
        final_response = "I've reached the maximum number of thinking steps. Here's what I found:"
        conversation_history.append({"role": "assistant", "content": final_response})

        return {
            "response": final_response,
            "conversation_history": conversation_history,
            "tools_used": tools_used,
        }