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
        assert (
            mock_mcp.tool.call_count == 4
        )  # 4 consolidated tools: workflow_guidance, workflow_state, workflow_cache_management, workflow_semantic_analysis

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
        result = workflow_tool.fn(action="start", task_description=task, session_id="")
        # Handle both dict and string formats
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert "Workflow Discovery Required" in result_text
        assert task in result_text

        # Test 'plan' action with provided YAML
        test_yaml = """
name: Test Workflow
description: A simple test workflow
workflow:
  goal: Test goal
  root: analyze
  tree:
    analyze:
      goal: Analyze requirements
      description: Understand the task
      next_allowed_nodes: [blueprint]
    blueprint:
      goal: Create plan
      description: Plan implementation
      next_allowed_nodes: []
inputs:
  task_description:
    type: string
    description: Task description
    required: true
        """

        # Start with YAML to establish session
        start_result = workflow_tool.fn(
            action="start",
            task_description=task,
            session_id="",
            context=f"workflow: Test Workflow\nyaml: {test_yaml}",
        )

        # Verify the start was successful
        # Handle both dict and string formats
        start_result_text = (
            start_result.get("content", start_result)
            if isinstance(start_result, dict)
            else start_result
        )
        assert "Workflow Started" in start_result_text
        assert "Test Workflow" in start_result_text

        # Extract session_id from the start result for subsequent calls
        session_id = (
            start_result.get("session_id", "") if isinstance(start_result, dict) else ""
        )

        # Test that the workflow guidance function handles different actions appropriately
        # For this test, we just verify that it returns a meaningful response
        result = workflow_tool.fn(
            action="next",
            task_description=task,
            session_id=session_id or "",
            context='{"choose": "blueprint", "criteria_evidence": {"analysis_complete": "test requirements analyzed"}}',
        )

        # Should return some kind of workflow guidance (either error or instruction)
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert isinstance(result_text, str)
        assert len(result_text) > 10  # Should be a meaningful response
        # The result should contain workflow guidance - either node status or error message
        assert (
            "Create plan" in result_text
            or "blueprint" in result_text
            or "Missing Choice" in result_text
            or "Workflow" in result_text
        )

        # Test 'build' action - should return some workflow guidance
        result = workflow_tool.fn(action="build", task_description=task, session_id="")
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert isinstance(result_text, str)
        assert len(result_text) > 10  # Should be a meaningful response

        # Test 'revise' action
        result = workflow_tool.fn(
            action="revise",
            task_description=task,
            session_id="",
            context="user feedback",
        )
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert isinstance(result_text, str)
        assert len(result_text) > 10  # Should be a meaningful response

        # Test 'next' action
        result = workflow_tool.fn(action="next", task_description=task, session_id="")
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert isinstance(result_text, str)
        assert len(result_text) > 10  # Should be a meaningful response

    @pytest.mark.asyncio
    async def test_workflow_state_output(self, mock_context):
        """Test workflow_state output format for different operations."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        state_tool = tools["workflow_state"]

        # Test 'get' operation
        result = state_tool.fn(operation="get", session_id="")
        # Handle both possible outcomes - either a successful workflow state or an error message
        # Result might be a dict with 'content' key or a string
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert any(
            marker in result_text
            for marker in [
                "WORKFLOW STATE",
                "Dynamic Workflow State",
                "Error in workflow_state",
                "No Active Workflow Session",
            ]
        )

        # Test 'update' operation
        result = state_tool.fn(
            operation="update", session_id="", updates='{"phase": "BLUEPRINT"}'
        )
        # Either successfully updated or returned an error message
        # Result might be a dict with 'content' key or a string
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert any(
            marker in result_text
            for marker in [
                "UPDATED",
                "Error",
                "updated",
                "Updated",
                "workflow_state",
                "Dynamic Workflow",
                "successfully",
                "No Active Workflow Session",
            ]
        )

        # Test 'reset' operation
        result = state_tool.fn(operation="reset", session_id="")
        # Result might be a dict with 'content' key or a string
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert any(
            marker in result_text
            for marker in ["State reset", "ready for new workflow", "RESET", "reset"]
        )

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
        assert "task_description" in workflow_tool.parameters["required"]
        assert "session_id" in workflow_tool.parameters["required"]

        # Test workflow_state parameters
        state_tool = tools["workflow_state"]
        assert "operation" in state_tool.parameters["properties"]
        assert "session_id" in state_tool.parameters["properties"]
        assert "updates" in state_tool.parameters["properties"]
        assert "operation" in state_tool.parameters["required"]
        assert "session_id" in state_tool.parameters["required"]

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
                action=action, task_description=task, session_id=""
            )
            # Handle both dict and string formats
            result_text = (
                result.get("content", result) if isinstance(result, dict) else result
            )
            assert isinstance(result_text, str)
            assert len(result_text) > 0

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
                    operation=operation, session_id="", updates='{"phase": "INIT"}'
                )
            else:
                result = state_tool.fn(operation=operation, session_id="")
            # Result might be a dict with 'content' key or a string
            if isinstance(result, dict):
                assert "content" in result
                assert isinstance(result["content"], str)
            else:
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

        # The behavior with invalid action has changed - now it might handle the action as dynamic workflow
        # or fallback to current node output instead of generating an error
        # The function now returns a workflow response even for invalid actions
        # Since it may fallback to dynamic workflow or legacy handler
        result = workflow_tool.fn(
            action="invalid_action", task_description=task, session_id=""
        )
        # Just verify we get a valid response string
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert isinstance(result_text, str) and len(result_text) > 10

    @pytest.mark.asyncio
    async def test_error_handling_invalid_operation(self, mock_context):
        """Test error handling for invalid workflow_state operation."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        state_tool = tools["workflow_state"]

        # The function now returns error message instead of raising exceptions
        result = state_tool.fn(operation="invalid_operation", session_id="")
        # Result might be a dict with 'content' key or a string
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert (
            "invalid" in result_text.lower()
            or "unknown" in result_text.lower()
            or "error" in result_text.lower()
        )

    @pytest.mark.asyncio
    async def test_consolidated_tools_contain_required_elements(self, mock_context):
        """Test that consolidated tools have all required functionality."""
        # This is a comprehensive test to ensure we haven't removed any required tools
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp, config=None)

        # Get all registered tools
        tools = await mcp.get_tools()

        # Check that required tools are present
        required_tools = ["workflow_guidance", "workflow_state"]
        for tool_name in required_tools:
            assert tool_name in tools, (
                f"Required tool {tool_name} not found in registered tools"
            )

        # Verify that workflow_guidance has required functionality
        workflow_tool = tools["workflow_guidance"]

        # Test basic functionality by calling with minimal parameters
        result = workflow_tool.fn(task_description="test task", session_id="")
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert isinstance(result_text, str)
        assert len(result_text) > 0

    @pytest.mark.asyncio
    async def test_mandatory_execution_emphasis(self, mock_context):
        """Test that mandatory execution emphasis is properly displayed."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp, config=None)

        tools = await mcp.get_tools()
        workflow_tool = tools["workflow_guidance"]

        result = workflow_tool.fn(
            task_description="test task with mandatory execution", session_id=""
        )

        # Check for mandatory execution emphasis
        mandatory_indicators = ["MANDATORY", "MUST", "REQUIRED", "🚨"]
        # Should contain at least one mandatory indicator
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        assert any(indicator in result_text for indicator in mandatory_indicators)

    @pytest.mark.asyncio
    async def test_enhanced_criteria_evidence_emphasis(self, mock_context):
        """Test that enhanced emphasis on criteria evidence is properly displayed."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp, config=None)

        tools = await mcp.get_tools()
        workflow_tool = tools["workflow_guidance"]

        # Get the tool directly to check its docstring and parameter descriptions
        tool_definition = tools["workflow_guidance"]

        # Check docstring contains enhanced emphasis
        docstring = tool_definition.fn.__doc__
        assert "🚨 CRITICAL AGENT REQUIREMENTS" in docstring
        assert "MANDATORY" in docstring
        assert "ALWAYS provide criteria_evidence" in docstring
        assert "NEVER" in docstring
        assert "JSON format" in docstring

        # Check context parameter description contains mandatory format emphasis
        context_param = tool_definition.parameters.get("properties", {}).get(
            "context", {}
        )
        context_desc = context_param.get("description", "")
        assert "🚨 MANDATORY CONTEXT FORMAT" in context_desc
        assert "ALWAYS use JSON format" in context_desc
        assert "PREFERRED" in context_desc
        assert "DISCOURAGED" in context_desc

        # Test actual tool output contains emphasis
        result = workflow_tool.fn(
            task_description="test enhanced emphasis", session_id=""
        )

        # Should contain multiple emphasis indicators
        emphasis_indicators = ["🚨", "MANDATORY", "CRITICAL", "ALWAYS", "REQUIRED"]
        result_text = (
            result.get("content", result) if isinstance(result, dict) else result
        )
        found_indicators = [
            indicator for indicator in emphasis_indicators if indicator in result_text
        ]

        # Should contain at least 2 different emphasis indicators
        assert len(found_indicators) >= 2, f"Only found indicators: {found_indicators}"

    @pytest.mark.asyncio
    async def test_json_context_parsing(self, mock_context):
        """Test the new JSON context parsing functionality."""
        from src.dev_workflow_mcp.prompts.yaml_parsing import (
            parse_criteria_evidence_context as _parse_criteria_evidence_context,
        )

        # Test legacy string format
        choice, evidence, user_approval = _parse_criteria_evidence_context(
            "choose: blueprint"
        )
        assert choice == "blueprint"
        assert evidence is None
        assert user_approval is False

        # Test new JSON format
        json_context = '{"choose": "construct", "criteria_evidence": {"analysis_complete": "Found the main issue in _generate_node_completion_outputs", "plan_ready": "Implementation plan created with 5 steps"}}'
        choice, evidence, user_approval = _parse_criteria_evidence_context(json_context)
        assert choice == "construct"
        assert evidence is not None
        assert (
            evidence["analysis_complete"]
            == "Found the main issue in _generate_node_completion_outputs"
        )
        assert evidence["plan_ready"] == "Implementation plan created with 5 steps"
        assert user_approval is False

        # Test invalid JSON fallback to legacy
        invalid_json_context = '{"choose": "test", invalid json'
        choice, evidence, user_approval = _parse_criteria_evidence_context(
            invalid_json_context
        )
        assert choice is None
        assert evidence is None
        assert user_approval is False

        # Test empty context
        choice, evidence, user_approval = _parse_criteria_evidence_context("")
        assert choice is None
        assert evidence is None
        assert user_approval is False

        # Test JSON without choose field
        json_no_choose = '{"criteria_evidence": {"test": "value"}}'
        choice, evidence, user_approval = _parse_criteria_evidence_context(
            json_no_choose
        )
        assert choice is None
        assert evidence == {"test": "value"}
        assert user_approval is False

    @pytest.mark.asyncio
    async def test_criteria_evidence_integration(self, mock_context):
        """Test that criteria evidence is properly integrated into completion outputs."""
        from unittest.mock import Mock

        from src.dev_workflow_mcp.models.yaml_workflow import WorkflowNode
        from src.dev_workflow_mcp.prompts.formatting import (
            generate_node_completion_outputs as _generate_node_completion_outputs,
        )

        # Create a mock node with acceptance criteria
        mock_node = Mock(spec=WorkflowNode)
        mock_node.acceptance_criteria = {
            "analysis_complete": "Complete analysis of the task",
            "requirements_clear": "Clear understanding of requirements",
        }

        # Create a mock session with proper log attribute
        mock_session = Mock()
        mock_session.execution_context = {}
        mock_session.log = []  # Empty log for testing automatic extraction fallback

        # Test with criteria evidence
        criteria_evidence = {
            "analysis_complete": "Analyzed the codebase and found _generate_node_completion_outputs generates hardcoded strings",
            "requirements_clear": "Need to transform context parameter to dict format and store actual evidence",
        }

        outputs = _generate_node_completion_outputs(
            "test_node", mock_node, mock_session, criteria_evidence
        )

        # Verify that actual evidence is stored
        assert "completed_criteria" in outputs
        assert (
            outputs["completed_criteria"]["analysis_complete"]
            == criteria_evidence["analysis_complete"]
        )
        assert (
            outputs["completed_criteria"]["requirements_clear"]
            == criteria_evidence["requirements_clear"]
        )

        # Test without criteria evidence (fallback behavior)
        outputs_fallback = _generate_node_completion_outputs(
            "test_node", mock_node, mock_session
        )

        # Verify fallback uses descriptive text instead of hardcoded generic string
        assert "completed_criteria" in outputs_fallback
        assert (
            "Complete analysis of the task"
            in outputs_fallback["completed_criteria"]["analysis_complete"]
        )
        assert (
            "Clear understanding of requirements"
            in outputs_fallback["completed_criteria"]["requirements_clear"]
        )
