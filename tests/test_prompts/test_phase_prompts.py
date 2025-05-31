"""Tests for phase prompt registration and functionality."""

from unittest.mock import Mock

import pytest
from fastmcp import Context, FastMCP

from src.dev_workflow_mcp.prompts.phase_prompts import register_phase_prompts


class TestPhasePrompts:
    """Test phase prompt registration and functionality."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance for testing."""
        mcp = Mock(spec=FastMCP)
        mcp.tool = Mock()
        return mcp

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context instance for testing."""
        context = Mock(spec=Context)
        context.client_id = "test-client-123"
        return context

    def test_register_phase_prompts(self, mock_mcp):
        """Test that register_phase_prompts registers all expected tools."""
        # Call the registration function
        register_phase_prompts(mock_mcp)

        # Verify that mcp.tool() was called for each prompt function
        assert mock_mcp.tool.call_count == 2  # 2 consolidated tools

        # Verify the decorator was called (tool registration)
        mock_mcp.tool.assert_called()

    @pytest.mark.asyncio
    async def test_phase_prompts_registration(self):
        """Test that all phase prompts are registered correctly."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()

        expected_tools = [
            "workflow_guidance",
            "workflow_state",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_workflow_guidance_output(self, mock_context):
        """Test workflow_guidance output format for different actions."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        workflow_tool = tools["workflow_guidance"]

        task = "Test: task description"

        # Test 'start' action
        result = workflow_tool.fn(
            action="start", task_description=task, ctx=mock_context
        )
        assert "WORKFLOW STARTED" in result
        assert task in result
        assert "ANALYZE PHASE" in result

        # Test 'plan' action
        result = workflow_tool.fn(
            action="plan",
            task_description=task,
            context="test requirements",
            ctx=mock_context,
        )
        assert "BLUEPRINT PHASE" in result
        assert task in result

        # Test 'build' action
        result = workflow_tool.fn(
            action="build", task_description=task, ctx=mock_context
        )
        assert "CONSTRUCT PHASE" in result
        assert task in result

        # Test 'revise' action
        result = workflow_tool.fn(
            action="revise",
            task_description=task,
            context="test feedback",
            ctx=mock_context,
        )
        assert "REVISING BLUEPRINT" in result
        assert task in result

        # Test 'next' action
        result = workflow_tool.fn(
            action="next", task_description=task, ctx=mock_context
        )
        assert task in result

    @pytest.mark.asyncio
    async def test_workflow_state_output(self, mock_context):
        """Test workflow_state output format for different operations."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        state_tool = tools["workflow_state"]

        # Test 'get' operation
        result = state_tool.fn(operation="get", ctx=mock_context)
        assert "WORKFLOW STATE" in result

        # Test 'update' operation
        result = state_tool.fn(
            operation="update",
            updates='{"phase": "CONSTRUCT", "status": "RUNNING"}',
            ctx=mock_context,
        )
        assert "STATE UPDATED" in result

        # Test 'reset' operation
        result = state_tool.fn(operation="reset", ctx=mock_context)
        assert "WORKFLOW RESET" in result

    @pytest.mark.asyncio
    async def test_tool_parameters(self):
        """Test that tools have correct parameter definitions."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()

        # Test workflow_guidance parameters
        workflow_tool = tools["workflow_guidance"]
        assert "action" in workflow_tool.parameters["properties"]
        assert "task_description" in workflow_tool.parameters["properties"]
        assert "context" in workflow_tool.parameters["properties"]
        assert "options" in workflow_tool.parameters["properties"]
        assert "action" in workflow_tool.parameters["required"]
        assert "task_description" in workflow_tool.parameters["required"]

        # Test workflow_state parameters
        state_tool = tools["workflow_state"]
        assert "operation" in state_tool.parameters["properties"]
        assert "updates" in state_tool.parameters["properties"]
        assert "operation" in state_tool.parameters["required"]

    @pytest.mark.asyncio
    async def test_workflow_guidance_actions(self, mock_context):
        """Test that workflow_guidance supports all expected actions."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        workflow_tool = tools["workflow_guidance"]

        task = "Test: task description"

        # Test all valid actions
        valid_actions = ["start", "plan", "build", "revise", "next"]

        for action in valid_actions:
            result = workflow_tool.fn(
                action=action, task_description=task, ctx=mock_context
            )
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_workflow_state_operations(self, mock_context):
        """Test that workflow_state supports all expected operations."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        state_tool = tools["workflow_state"]

        # Test all valid operations
        valid_operations = ["get", "update", "reset"]

        for operation in valid_operations:
            if operation == "update":
                result = state_tool.fn(
                    operation=operation, updates='{"phase": "INIT"}', ctx=mock_context
                )
            else:
                result = state_tool.fn(operation=operation, ctx=mock_context)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_error_handling_invalid_action(self, mock_context):
        """Test error handling for invalid workflow_guidance action."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        workflow_tool = tools["workflow_guidance"]

        task = "Test: task description"

        with pytest.raises(ValueError, match="Unknown action"):
            workflow_tool.fn(
                action="invalid_action", task_description=task, ctx=mock_context
            )

    @pytest.mark.asyncio
    async def test_error_handling_invalid_operation(self, mock_context):
        """Test error handling for invalid workflow_state operation."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        state_tool = tools["workflow_state"]

        with pytest.raises(ValueError, match="Unknown operation"):
            state_tool.fn(operation="invalid_operation", ctx=mock_context)

    @pytest.mark.asyncio
    async def test_consolidated_tools_contain_required_elements(self, mock_context):
        """Test that consolidated tools contain required workflow elements."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        workflow_tool = tools["workflow_guidance"]

        task = "Test: task description"

        # Test that start action contains required elements
        result = workflow_tool.fn(
            action="start", task_description=task, ctx=mock_context
        )
        assert "MANDATORY" in result
        assert "REQUIRED" in result
        assert "CHECKLIST" in result

        # Test that plan action contains required elements
        result = workflow_tool.fn(
            action="plan",
            task_description=task,
            context="test requirements",
            ctx=mock_context,
        )
        assert "MANDATORY" in result
        assert "REQUIRED" in result

    @pytest.mark.asyncio
    async def test_mandatory_execution_emphasis(self, mock_context):
        """Test that consolidated tools emphasize mandatory execution."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        workflow_tool = tools["workflow_guidance"]

        task = "Test: task description"

        # Test different actions for mandatory execution emphasis
        actions_to_test = ["start", "plan", "build"]

        for action in actions_to_test:
            result = workflow_tool.fn(
                action=action, task_description=task, ctx=mock_context
            )

            # Check for mandatory execution indicators
            mandatory_indicators = ["MANDATORY", "REQUIRED", "MUST", "⚠️"]
            assert any(indicator in result for indicator in mandatory_indicators), (
                f"Action '{action}' result should contain mandatory execution emphasis"
            )
