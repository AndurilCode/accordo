"""Tests for the main server module."""

from unittest.mock import patch

import pytest

from src.dev_workflow_mcp.server import main, mcp


class TestServerInitialization:
    """Test server initialization and setup."""

    def test_mcp_server_creation(self):
        """Test that MCP server is created with correct name."""
        assert mcp.name == "Development Workflow"

    @pytest.mark.asyncio
    async def test_guidance_tools_registered(self):
        """Test that guidance tools are registered."""
        tools = await mcp.get_tools()
        tool_names = list(tools.keys())

        # Check that key consolidated guidance tools are registered
        expected_tools = [
            "workflow_guidance",
            "workflow_state",
            "update_workflow_state_guidance",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, (
                f"Tool {tool_name} not found in registered tools"
            )

    @pytest.mark.asyncio
    async def test_tool_count(self):
        """Test that expected number of tools are registered."""
        tools = await mcp.get_tools()
        # Should have 2 consolidated phase tools + management tools
        # Based on the guidance files, we expect around 8 tools total
        assert len(tools) >= 8


class TestMainFunction:
    """Test main function."""

    @patch("src.dev_workflow_mcp.server.mcp.run")
    def test_main_calls_mcp_run(self, mock_run):
        """Test that main function calls mcp.run with correct parameters."""
        main()

        mock_run.assert_called_once_with(transport="stdio")


class TestToolExecution:
    """Test tool registration and structure."""

    @pytest.mark.asyncio
    async def test_workflow_guidance_tool_structure(self):
        """Test workflow_guidance tool is properly registered with correct structure."""
        # Get the tool
        tools = await mcp.get_tools()
        assert "workflow_guidance" in tools
        workflow_tool = tools["workflow_guidance"]

        # Verify tool structure
        assert workflow_tool.name == "workflow_guidance"
        assert "Consolidated smart workflow guidance" in workflow_tool.description
        assert workflow_tool.parameters["type"] == "object"
        assert "action" in workflow_tool.parameters["properties"]
        assert "task_description" in workflow_tool.parameters["properties"]
        assert "action" in workflow_tool.parameters["required"]
        assert "task_description" in workflow_tool.parameters["required"]

        # Test that the function exists and is callable
        assert callable(workflow_tool.fn)

    @pytest.mark.asyncio
    async def test_workflow_state_tool_structure(self):
        """Test workflow_state tool is properly registered with correct structure."""
        # Get the tool
        tools = await mcp.get_tools()
        assert "workflow_state" in tools
        state_tool = tools["workflow_state"]

        # Verify tool structure
        assert state_tool.name == "workflow_state"
        assert "Smart workflow state management" in state_tool.description
        assert state_tool.parameters["type"] == "object"
        assert "operation" in state_tool.parameters["properties"]
        assert "updates" in state_tool.parameters["properties"]
        assert "operation" in state_tool.parameters["required"]

        # Test that the function exists and is callable
        assert callable(state_tool.fn)

    @pytest.mark.asyncio
    async def test_update_workflow_state_guidance_tool_structure(self):
        """Test update_workflow_state_guidance tool is properly registered with correct structure."""
        # Get the tool
        tools = await mcp.get_tools()
        assert "update_workflow_state_guidance" in tools
        update_tool = tools["update_workflow_state_guidance"]

        # Verify tool structure
        assert update_tool.name == "update_workflow_state_guidance"
        assert "update the workflow state" in update_tool.description
        assert update_tool.parameters["type"] == "object"

        properties = update_tool.parameters["properties"]
        required = update_tool.parameters["required"]

        # Check required parameters
        assert "phase" in properties
        assert "status" in properties
        assert "phase" in required
        assert "status" in required

        # Check optional parameters
        assert "current_item" in properties
        assert "log_entry" in properties

        # Test that the function exists and is callable
        assert callable(update_tool.fn)


class TestToolParameters:
    """Test tool parameter validation."""

    @pytest.mark.asyncio
    async def test_workflow_guidance_requires_action_and_task(self):
        """Test that workflow_guidance requires action and task_description parameters."""
        tools = await mcp.get_tools()
        assert "workflow_guidance" in tools
        workflow_tool = tools["workflow_guidance"]

        # Check that required parameters are present
        assert "action" in workflow_tool.parameters["properties"]
        assert "task_description" in workflow_tool.parameters["properties"]
        assert "action" in workflow_tool.parameters["required"]
        assert "task_description" in workflow_tool.parameters["required"]

    @pytest.mark.asyncio
    async def test_workflow_state_requires_operation(self):
        """Test that workflow_state requires operation parameter."""
        tools = await mcp.get_tools()
        assert "workflow_state" in tools
        state_tool = tools["workflow_state"]

        # Check that operation is a required parameter
        assert "operation" in state_tool.parameters["properties"]
        assert "operation" in state_tool.parameters["required"]

    @pytest.mark.asyncio
    async def test_update_workflow_state_guidance_parameters(self):
        """Test update_workflow_state_guidance parameter schema."""
        tools = await mcp.get_tools()
        assert "update_workflow_state_guidance" in tools
        update_tool = tools["update_workflow_state_guidance"]

        properties = update_tool.parameters["properties"]
        required = update_tool.parameters["required"]

        # Check required parameters
        assert "phase" in properties
        assert "status" in properties
        assert "phase" in required
        assert "status" in required

        # Check optional parameters
        assert "current_item" in properties
        assert "log_entry" in properties
        assert "current_item" not in required
        assert "log_entry" not in required
