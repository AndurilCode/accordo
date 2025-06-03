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
        """Test that essential YAML workflow tools are registered."""
        tools = await mcp.get_tools()
        tool_names = list(tools.keys())

        # Check that essential workflow tools are registered (after legacy cleanup)
        expected_tools = [
            "workflow_guidance",
            "workflow_state", 
            "workflow_discovery",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, (
                f"Essential tool {tool_name} not found in registered tools"
            )

    @pytest.mark.asyncio
    async def test_tool_count(self):
        """Test that expected number of tools are registered."""
        tools = await mcp.get_tools()
        # After legacy cleanup: 2 phase tools + 4 discovery tools = 6 essential tools
        assert len(tools) == 6, f"Expected 6 tools, got {len(tools)}: {list(tools.keys())}"


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
        assert "Pure schema-driven workflow guidance" in workflow_tool.description
        assert workflow_tool.parameters["type"] == "object"
        assert "action" in workflow_tool.parameters["properties"]
        assert "task_description" in workflow_tool.parameters["properties"]
        # Only task_description is required, action has a default value
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
        assert "Get or update workflow state" in state_tool.description
        assert state_tool.parameters["type"] == "object"
        assert "operation" in state_tool.parameters["properties"]
        assert "updates" in state_tool.parameters["properties"]
        assert "operation" in state_tool.parameters["required"]

        # Test that the function exists and is callable
        assert callable(state_tool.fn)

    @pytest.mark.asyncio
    async def test_workflow_discovery_tool_structure(self):
        """Test workflow_discovery tool is properly registered with correct structure."""
        # Get the tool
        tools = await mcp.get_tools()
        assert "workflow_discovery" in tools
        discovery_tool = tools["workflow_discovery"]

        # Verify tool structure
        assert discovery_tool.name == "workflow_discovery"
        assert "Discover available workflows" in discovery_tool.description
        assert discovery_tool.parameters["type"] == "object"
        assert "task_description" in discovery_tool.parameters["properties"]
        assert "task_description" in discovery_tool.parameters["required"]

        # Test that the function exists and is callable
        assert callable(discovery_tool.fn)


class TestToolParameters:
    """Test tool parameter validation."""

    @pytest.mark.asyncio
    async def test_workflow_guidance_requires_task_description(self):
        """Test that workflow_guidance requires task_description parameter."""
        tools = await mcp.get_tools()
        assert "workflow_guidance" in tools
        workflow_tool = tools["workflow_guidance"]

        # Check that required parameters are present
        assert "action" in workflow_tool.parameters["properties"]
        assert "task_description" in workflow_tool.parameters["properties"]
        # Only task_description is required, action has a default value
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
    async def test_workflow_discovery_parameters(self):
        """Test workflow_discovery parameter schema."""
        tools = await mcp.get_tools()
        assert "workflow_discovery" in tools
        discovery_tool = tools["workflow_discovery"]

        properties = discovery_tool.parameters["properties"]
        required = discovery_tool.parameters["required"]

        # Check required parameters
        assert "task_description" in properties
        assert "task_description" in required

        # Check optional parameters
        assert "workflows_dir" in properties
        assert "client_id" in properties
        assert "workflows_dir" not in required
        assert "client_id" not in required
