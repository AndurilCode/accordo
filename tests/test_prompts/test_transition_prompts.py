"""Tests for transition prompt registration and functionality."""

from unittest.mock import Mock

import pytest
from fastmcp import FastMCP

from src.dev_workflow_mcp.prompts.transition_prompts import register_transition_prompts


class TestTransitionPrompts:
    """Test transition prompt registration and functionality."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance for testing."""
        mcp = Mock(spec=FastMCP)
        mcp.tool = Mock()
        return mcp

    def test_register_transition_prompts(self, mock_mcp):
        """Test that register_transition_prompts registers all expected tools."""
        # Call the registration function
        register_transition_prompts(mock_mcp)

        # Verify that mcp.tool() was called for each prompt function
        assert mock_mcp.tool.call_count == 6  # 6 prompt functions

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
            "create_workflow_state_file_guidance",
            "check_project_config_guidance",
            "create_project_config_guidance",
            "validate_workflow_files_guidance",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not registered"

    @pytest.mark.asyncio
    async def test_update_workflow_state_guidance_output(self):
        """Test update_workflow_state_guidance output format."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)

        tools = await mcp.get_tools()
        update_tool = tools["update_workflow_state_guidance"]

        result = update_tool.fn(
            phase="CONSTRUCT",
            status="RUNNING",
            current_item="Test task",
            log_entry="Test log entry",
        )

        assert "UPDATING WORKFLOW STATE" in result
        assert "Phase: CONSTRUCT" in result
        assert "Status: RUNNING" in result
        assert "CurrentItem: Test task" in result
        assert "Test log entry" in result

    @pytest.mark.asyncio
    async def test_update_workflow_state_guidance_minimal(self):
        """Test update_workflow_state_guidance with minimal parameters."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)

        tools = await mcp.get_tools()
        update_tool = tools["update_workflow_state_guidance"]

        result = update_tool.fn(phase="INIT", status="READY")

        assert "UPDATING WORKFLOW STATE" in result
        assert "Phase: INIT" in result
        assert "Status: READY" in result
        assert "CurrentItem: null" in result

    @pytest.mark.asyncio
    async def test_create_workflow_state_file_guidance_output(self):
        """Test create_workflow_state_file_guidance output format."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)

        tools = await mcp.get_tools()
        create_tool = tools["create_workflow_state_file_guidance"]

        task = "Test task description"
        result = create_tool.fn(task_description=task)

        assert "CREATING WORKFLOW STATE FILE" in result
        assert task in result
        assert "workflow_state.md" in result
        assert "analyze_phase_guidance" in result
        assert "## State" in result
        assert "## Plan" in result
        assert "## Items" in result

    @pytest.mark.asyncio
    async def test_check_project_config_guidance_output(self):
        """Test check_project_config_guidance output format."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)

        tools = await mcp.get_tools()
        check_tool = tools["check_project_config_guidance"]

        result = check_tool.fn()

        assert "CHECKING PROJECT CONFIGURATION" in result
        assert "project_config.md" in result
        assert "create_project_config_guidance" in result
        assert "## Project Info" in result
        assert "## Dependencies" in result

    @pytest.mark.asyncio
    async def test_create_project_config_guidance_output(self):
        """Test create_project_config_guidance output format."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)

        tools = await mcp.get_tools()
        create_config_tool = tools["create_project_config_guidance"]

        result = create_config_tool.fn()

        assert "CREATING PROJECT CONFIG FILE" in result
        assert "project_config.md" in result
        assert "## Project Info" in result
        assert "## Dependencies" in result
        assert "## Test Commands" in result
        assert "## Changelog" in result

    @pytest.mark.asyncio
    async def test_validate_workflow_files_guidance_output(self):
        """Test validate_workflow_files_guidance output format."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)

        tools = await mcp.get_tools()
        validate_tool = tools["validate_workflow_files_guidance"]

        result = validate_tool.fn()

        assert "VALIDATING WORKFLOW FILES" in result
        assert "workflow_state.md" in result
        assert "project_config.md" in result
        assert "## State" in result
        assert "## Plan" in result

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

        # Test create_workflow_state_file_guidance parameters
        create_tool = tools["create_workflow_state_file_guidance"]
        assert "task_description" in create_tool.parameters["properties"]
        assert "task_description" in create_tool.parameters["required"]

    @pytest.mark.asyncio
    async def test_workflow_file_creation_chain(self):
        """Test the workflow file creation chain."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        # Test create workflow state -> analyze chain
        create_result = tools["create_workflow_state_file_guidance"].fn(
            task_description="test"
        )
        assert "analyze_phase_guidance" in create_result

        # Test check config -> create config chain
        check_result = tools["check_project_config_guidance"].fn()
        assert "create_project_config_guidance" in check_result

    @pytest.mark.asyncio
    async def test_all_prompts_contain_required_elements(self):
        """Test that all prompts contain required workflow elements."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        for tool_name, tool in tools.items():
            if tool_name == "update_workflow_state_guidance":
                result = tool.fn(phase="TEST", status="RUNNING")
            elif tool_name == "create_workflow_state_file_guidance":
                result = tool.fn(task_description="test task")
            elif (
                tool_name == "check_project_config_guidance"
                or tool_name == "create_project_config_guidance"
                or tool_name == "validate_workflow_files_guidance"
            ):
                result = tool.fn()
            else:
                continue

            # All prompts should have clear action items
            assert "ACTIONS" in result or "ACTION" in result
            # All prompts should have next step guidance
            assert (
                "WHEN" in result
                or "IF" in result
                or "AFTER" in result
                or "Return" in result
            )

    @pytest.mark.asyncio
    async def test_state_update_with_all_parameters(self):
        """Test state update with all possible parameters."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        update_tool = tools["update_workflow_state_guidance"]

        result = update_tool.fn(
            phase="VALIDATE",
            status="COMPLETED",
            current_item="Complex task with special chars: <>[]",
            log_entry="Multi-line log entry\nwith newlines\nand details",
        )

        assert "Phase: VALIDATE" in result
        assert "Status: COMPLETED" in result
        assert "Complex task with special chars: <>[]" in result
        assert "Multi-line log entry" in result

    @pytest.mark.asyncio
    async def test_workflow_state_template_structure(self):
        """Test that workflow state template has correct structure."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        create_tool = tools["create_workflow_state_file_guidance"]
        result = create_tool.fn(task_description="test")

        # Check for all required sections
        required_sections = [
            "## State",
            "## Plan",
            "## Rules",
            "## Items",
            "## Log",
            "## ArchiveLog",
        ]

        for section in required_sections:
            assert section in result, f"Missing section: {section}"

        # Check for workflow rules
        assert "PHASE: ANALYZE" in result
        assert "PHASE: BLUEPRINT" in result
        assert "PHASE: CONSTRUCT" in result
        assert "PHASE: VALIDATE" in result

    @pytest.mark.asyncio
    async def test_mandatory_execution_emphasis(self):
        """Test that all guidance tools emphasize mandatory execution."""
        mcp = FastMCP("test-server")
        register_transition_prompts(mcp)
        tools = await mcp.get_tools()

        # Check that tool descriptions emphasize mandatory execution
        for _tool_name, tool in tools.items():
            assert (
                "mandatory" in tool.description.lower()
                or "guide" in tool.description.lower()
            )

        # Check that tool responses contain required actions
        for tool_name, tool in tools.items():
            if tool_name == "update_workflow_state_guidance":
                result = tool.fn(phase="TEST", status="RUNNING")
            elif tool_name == "create_workflow_state_file_guidance":
                result = tool.fn(task_description="test task")
            elif (
                tool_name == "check_project_config_guidance"
                or tool_name == "create_project_config_guidance"
                or tool_name == "validate_workflow_files_guidance"
            ):
                result = tool.fn()
            else:
                continue

            assert "REQUIRED ACTIONS" in result or "ACTIONS TO TAKE" in result
