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

        # Check that some key guidance tools are registered
        expected_tools = [
            "init_workflow_guidance",
            "analyze_phase_guidance",
            "blueprint_phase_guidance",
            "construct_phase_guidance",
            "validate_phase_guidance",
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
        # Should have guidance tools only
        # Based on the guidance files, we expect around 14 tools
        assert len(tools) >= 14


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
    async def test_init_workflow_guidance_tool_structure(self):
        """Test init_workflow_guidance tool is properly registered with correct structure."""
        # Get the tool
        tools = await mcp.get_tools()
        assert "init_workflow_guidance" in tools
        init_tool = tools["init_workflow_guidance"]

        # Verify tool structure
        assert init_tool.name == "init_workflow_guidance"
        assert "Initialize a new development workflow" in init_tool.description
        assert init_tool.parameters["type"] == "object"
        assert "task_description" in init_tool.parameters["properties"]
        assert "task_description" in init_tool.parameters["required"]

        # Test that the function exists and is callable
        assert callable(init_tool.fn)

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
    async def test_init_workflow_guidance_requires_task_description(self):
        """Test that init_workflow_guidance requires task_description parameter."""
        tools = await mcp.get_tools()
        assert "init_workflow_guidance" in tools
        init_tool = tools["init_workflow_guidance"]

        # Check that task_description is a required parameter
        assert "task_description" in init_tool.parameters["properties"]
        assert "task_description" in init_tool.parameters["required"]

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
