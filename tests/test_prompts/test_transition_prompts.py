"""Tests for transition prompt registration and functionality."""

from unittest.mock import Mock

import pytest
from fastmcp import Context, FastMCP

from src.dev_workflow_mcp.prompts.transition_prompts import register_transition_prompts
from src.dev_workflow_mcp.utils import session_manager


class TestTransitionPrompts:
    """Test transition prompt registration and functionality."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance for testing."""
        mcp = Mock(spec=FastMCP)
        mcp.tool = Mock()
        return mcp

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context for testing."""
        ctx = Mock(spec=Context)
        ctx.client_id = "test-client"
        return ctx

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_register_transition_prompts(self, mock_mcp):
        """Test that register_transition_prompts registers all expected tools."""
        # Call the registration function
        register_transition_prompts(mock_mcp)

        # Verify that mcp.tool() was called for each prompt function
        assert mock_mcp.tool.call_count == 2  # 2 prompt functions

        # Verify the decorator was called (tool registration)
        mock_mcp.tool.assert_called()

    @pytest.mark.asyncio
    async def test_transition_prompts_registration_with_real_mcp(self):
        """Test registration with a real FastMCP instance."""
        mcp = FastMCP("test-server")

        # Register the prompts
        register_transition_prompts(mcp)

        # Get the registered tools
        tools = await mcp.get_tools()

        # Verify all expected prompt tools are registered
        expected_tools = [
            "update_workflow_state_guidance",
            "get_workflow_state_markdown",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_update_workflow_state_guidance_output(self, mock_context):
        """Test update_workflow_state_guidance output format."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)

        tools = await mcp.get_tools()
        update_tool = tools["update_workflow_state_guidance"]

        result = update_tool.fn(
            phase="CONSTRUCT",
            status="RUNNING",
            ctx=mock_context,
            current_item="Test task",
            log_entry="Test log entry",
        )

        assert "WORKFLOW STATE UPDATED" in result
        assert "Phase → CONSTRUCT" in result
        assert "Status → RUNNING" in result
        assert "CurrentItem → Test task" in result
        assert "Test log entry" in result

    @pytest.mark.asyncio
    async def test_update_workflow_state_guidance_minimal(self, mock_context):
        """Test update_workflow_state_guidance with minimal parameters."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)

        tools = await mcp.get_tools()
        update_tool = tools["update_workflow_state_guidance"]

        result = update_tool.fn(phase="INIT", status="READY", ctx=mock_context)

        assert "WORKFLOW STATE UPDATED" in result
        assert "Phase → INIT" in result
        assert "Status → READY" in result
        assert "CurrentItem → null" in result

    @pytest.mark.asyncio
    async def test_get_workflow_state_markdown_output(self, mock_context):
        """Test get_workflow_state_markdown output format."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)

        tools = await mcp.get_tools()
        get_state_tool = tools["get_workflow_state_markdown"]

        # First create a session by updating state
        update_tool = tools["update_workflow_state_guidance"]
        update_tool.fn(phase="INIT", status="READY", ctx=mock_context)

        # Now get the state
        result = get_state_tool.fn(ctx=mock_context)

        assert "CURRENT WORKFLOW STATE" in result
        assert "Client:" in result
        assert "# Workflow State" in result

    @pytest.mark.asyncio
    async def test_tool_parameters(self):
        """Test that tools have correct parameter definitions."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)

        tools = await mcp.get_tools()

        # Test update_workflow_state_guidance parameters
        update_tool = tools["update_workflow_state_guidance"]
        assert "phase" in update_tool.parameters["properties"]
        assert "status" in update_tool.parameters["properties"]
        assert "current_item" in update_tool.parameters["properties"]
        assert "log_entry" in update_tool.parameters["properties"]
        assert "phase" in update_tool.parameters["required"]
        assert "status" in update_tool.parameters["required"]

        # Test get_workflow_state_markdown parameters
        get_state_tool = tools["get_workflow_state_markdown"]
        # This tool has no required parameters (only context)
        assert get_state_tool.parameters["properties"] == {}

    @pytest.mark.asyncio
    async def test_session_based_state_management(self, mock_context):
        """Test that the tools work with session-based state management."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        # Test state update
        update_result = tools["update_workflow_state_guidance"].fn(
            phase="ANALYZE",
            status="RUNNING",
            ctx=mock_context,
            current_item="Test analysis task",
            log_entry="Starting analysis phase",
        )

        assert "Phase → ANALYZE" in update_result
        assert "Status → RUNNING" in update_result
        assert "Test analysis task" in update_result
        assert "Starting analysis phase" in update_result

        # Test state retrieval
        get_result = tools["get_workflow_state_markdown"].fn(ctx=mock_context)
        assert "CURRENT WORKFLOW STATE" in get_result
        assert "# Workflow State" in get_result

    @pytest.mark.asyncio
    async def test_all_prompts_contain_required_elements(self, mock_context):
        """Test that all prompts contain required guidance elements."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        # Test update guidance contains state information
        update_result = tools["update_workflow_state_guidance"].fn(
            phase="CONSTRUCT", status="RUNNING", ctx=mock_context
        )
        assert "STATE UPDATED AUTOMATICALLY" in update_result
        assert "CURRENT WORKFLOW STATE" in update_result
        assert "NEXT STEP" in update_result

        # Test get state contains markdown (after creating session)
        get_result = tools["get_workflow_state_markdown"].fn(ctx=mock_context)
        assert "CURRENT WORKFLOW STATE" in get_result
        assert "markdown" in get_result.lower()

    @pytest.mark.asyncio
    async def test_state_update_with_all_parameters(self, mock_context):
        """Test state update with all possible parameters."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        result = tools["update_workflow_state_guidance"].fn(
            phase="VALIDATE",
            status="COMPLETED",
            ctx=mock_context,
            current_item="Final validation task",
            log_entry="All tests passed successfully",
        )

        assert "Phase → VALIDATE" in result
        assert "Status → COMPLETED" in result
        assert "CurrentItem → Final validation task" in result
        assert "All tests passed successfully" in result
        assert "STATE UPDATED AUTOMATICALLY" in result

    @pytest.mark.asyncio
    async def test_session_based_workflow_state_structure(self, mock_context):
        """Test that session-based workflow state has proper structure."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        # Update state first
        tools["update_workflow_state_guidance"].fn(
            phase="BLUEPRINT",
            status="NEEDS_PLAN_APPROVAL",
            ctx=mock_context,
            current_item="Create implementation plan",
        )

        # Get the state
        result = tools["get_workflow_state_markdown"].fn(ctx=mock_context)

        # Verify session-based structure
        assert "# Workflow State" in result
        assert "## State" in result
        assert "## Plan" in result
        assert "## Items" in result
        assert "## Log" in result
        assert "Phase: BLUEPRINT" in result
        assert "Status: NEEDS_PLAN_APPROVAL" in result

    @pytest.mark.asyncio
    async def test_mandatory_execution_emphasis(self, mock_context):
        """Test that prompts emphasize mandatory execution."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        result = tools["update_workflow_state_guidance"].fn(
            phase="CONSTRUCT", status="RUNNING", ctx=mock_context
        )

        # Check for mandatory execution language
        assert "STATE UPDATED AUTOMATICALLY" in result
        assert "continue with your workflow" in result.lower()
        assert "🎯" in result  # Target emoji for emphasis

    @pytest.mark.asyncio
    async def test_get_workflow_state_no_session(self, mock_context):
        """Test get_workflow_state_markdown when no session exists."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        # Test without creating a session first
        result = tools["get_workflow_state_markdown"].fn(ctx=mock_context)
        assert "No workflow session found" in result
        assert "test-client" in result
