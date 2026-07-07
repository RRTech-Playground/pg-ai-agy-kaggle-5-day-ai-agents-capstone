import pytest
import os
from unittest.mock import MagicMock
from app.policy_server import PolicyServerPlugin
from google.adk.tools import BaseTool, ToolContext

@pytest.mark.asyncio
async def test_localhost_blocked_tools():
    """Verify that send_email and mutate_state are blocked on localhost."""
    plugin = PolicyServerPlugin()
    
    # Mock send_email tool
    tool_send_email = MagicMock(spec=BaseTool)
    tool_send_email.name = "send_email"
    
    tool_context = MagicMock(spec=ToolContext)
    
    result = await plugin.before_tool_callback(
        tool=tool_send_email,
        tool_args={},
        tool_context=tool_context
    )
    
    assert result is not None
    assert "blocked" in result["error"]
    assert result["status"] == "blocked"
    assert result["code"] == "POLICY_VIOLATION_STRUCTURAL"


@pytest.mark.asyncio
async def test_readonly_blocked_tools():
    """Verify that write/mutation tools are blocked for read-only agents."""
    plugin = PolicyServerPlugin()
    
    # Mock a tool matching a write pattern
    tool_mutate = MagicMock(spec=BaseTool)
    tool_mutate.name = "mutate_database"
    
    tool_context = MagicMock(spec=ToolContext)
    
    result = await plugin.before_tool_callback(
        tool=tool_mutate,
        tool_args={},
        tool_context=tool_context
    )
    
    assert result is not None
    assert "read-only" in result["error"]
    assert result["status"] == "blocked"
    assert result["code"] == "POLICY_VIOLATION_READ_ONLY"


@pytest.mark.asyncio
async def test_semantic_credentials_check():
    """Verify that unmasked secrets/credentials in arguments are blocked."""
    plugin = PolicyServerPlugin()
    
    tool = MagicMock(spec=BaseTool)
    tool.name = "get_weather"
    
    tool_context = MagicMock(spec=ToolContext)
    
    # Pass a sensitive credential/API key in the arguments
    result = await plugin.before_tool_callback(
        tool=tool,
        tool_args={"query": "San Francisco", "api_key": "AIzaSyD-fakekey12345SECRET"},
        tool_context=tool_context
    )
    
    assert result is not None
    assert "Security Violation" in result["error"]
    assert result["status"] == "blocked"


@pytest.mark.asyncio
async def test_passed_checks():
    """Verify that a safe tool call passes all security checks."""
    plugin = PolicyServerPlugin()
    
    tool = MagicMock(spec=BaseTool)
    tool.name = "get_weather"
    
    tool_context = MagicMock(spec=ToolContext)
    
    result = await plugin.before_tool_callback(
        tool=tool,
        tool_args={"query": "San Francisco"},
        tool_context=tool_context
    )
    
    # If it passes, it should return None to proceed normally
    assert result is None
