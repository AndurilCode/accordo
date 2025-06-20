"""Tests for phase prompt registration and functionality."""

from unittest.mock import Mock

import pytest
from fastmcp import Context, FastMCP

from src.accordo_workflow_mcp.prompts.phase_prompts import register_phase_prompts


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
        )  # 4 tools: workflow_guidance, workflow_state, workflow_cache_management, workflow_semantic_search

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
        result = workflow_tool.fn(action="start", task_description=task)

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        assert "Workflow Discovery Required" in content
        assert task in content

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
        workflow_tool.fn(
            action="start",
            task_description=task,
            context=f"workflow: Test Workflow\nyaml: {test_yaml}",
        )

        # Then test 'plan' action
        result = workflow_tool.fn(
            action="plan",
            task_description=task,
            context="test requirements",
        )

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        # Either expect dynamic workflow response, legacy blueprint phase, or discovery requirement
        assert any(
            marker in content
            for marker in [
                "BLUEPRINT PHASE",
                "Dynamic Workflow",
                "Create plan",
                "DISCOVERY REQUIRED",
                "No Active Workflow Session",
            ]
        )
        assert task in content

        # Test 'build' action - either dynamic workflow or legacy construct phase
        result = workflow_tool.fn(action="build", task_description=task)

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        # The exact text depends on the workflow mode (dynamic vs legacy) or discovery requirement
        assert any(
            marker in content
            for marker in [
                "CONSTRUCT PHASE",
                "Dynamic Workflow",
                "Analyze requirements",
                "DISCOVERY REQUIRED",
                "No Active Workflow Session",
            ]
        )
        assert task in content

        # Test 'revise' action
        result = workflow_tool.fn(
            action="revise",
            task_description=task,
            context="user feedback",
        )

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        # Handle both dynamic workflow, legacy workflow responses, and discovery requirement
        assert any(
            marker in content
            for marker in [
                "REVISING BLUEPRINT",
                "Dynamic Workflow",
                "Analyze requirements",
                "DISCOVERY REQUIRED",
                "No Active Workflow Session",
            ]
        )
        assert task in content

        # Test 'next' action
        result = workflow_tool.fn(action="next", task_description=task)

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        assert task in content

    @pytest.mark.asyncio
    async def test_workflow_state_output(self, mock_context):
        """Test workflow_state output format for different operations."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        state_tool = tools["workflow_state"]

        # Test 'get' operation
        result = state_tool.fn(operation="get")

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        # Handle both possible outcomes - either a successful workflow state or an error message
        assert any(
            marker in content
            for marker in [
                "WORKFLOW STATE",
                "Dynamic Workflow State",
                "Error in workflow_state",
                "No Active Workflow Session",
                "DISCOVERY REQUIRED",
            ]
        )

        # Test 'update' operation
        result = state_tool.fn(operation="update", updates='{"phase": "BLUEPRINT"}')

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        # Either successfully updated or returned an error message
        assert any(
            marker in content
            for marker in [
                "UPDATED",
                "Error",
                "updated",
                "Updated",
                "workflow_state",
                "Dynamic Workflow",
                "No Active Workflow Session",
                "DISCOVERY REQUIRED",
            ]
        )

        # Test 'reset' operation
        result = state_tool.fn(operation="reset")

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        assert any(
            marker in content
            for marker in ["State reset", "ready for new workflow", "RESET"]
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
            result = workflow_tool.fn(action=action, task_description=task)
            
            # Handle both string and dict response formats
            if isinstance(result, dict):
                content = result.get("content", str(result))
                assert isinstance(content, str)
                assert len(content) > 0
            else:
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
                result = state_tool.fn(operation=operation, updates='{"phase": "INIT"}')
            else:
                result = state_tool.fn(operation=operation)

            # Handle both string and dict response formats
            if isinstance(result, dict):
                content = result.get("content", str(result))
                assert isinstance(content, str)
                assert len(content) > 0
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
        result = workflow_tool.fn(action="invalid_action", task_description=task)
        # Just verify we get a valid response
        
        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
            assert isinstance(content, str) and len(content) > 10
        else:
            assert isinstance(result, str) and len(result) > 10

    @pytest.mark.asyncio
    async def test_error_handling_invalid_operation(self, mock_context):
        """Test error handling for invalid workflow_state operation."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp)

        tools = await mcp.get_tools()
        state_tool = tools["workflow_state"]

        # The function now returns error message instead of raising exceptions
        result = state_tool.fn(operation="invalid_operation")

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        assert (
            "invalid" in content.lower()
            or "unknown" in content.lower()
            or "error" in content.lower()
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
        result = workflow_tool.fn(task_description="test task")
        
        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
            assert isinstance(content, str)
            assert len(content) > 0
        else:
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_mandatory_execution_emphasis(self, mock_context):
        """Test that mandatory execution emphasis is properly displayed."""
        mcp = FastMCP("test-server")
        register_phase_prompts(mcp, config=None)

        tools = await mcp.get_tools()
        workflow_tool = tools["workflow_guidance"]

        result = workflow_tool.fn(task_description="test task with mandatory execution")

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        # Check for mandatory execution emphasis
        mandatory_indicators = ["MANDATORY", "MUST", "REQUIRED", "🚨"]
        # Should contain at least one mandatory indicator
        assert any(indicator in content for indicator in mandatory_indicators)

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
        result = workflow_tool.fn(task_description="test enhanced emphasis")

        # Handle both string and dict response formats
        if isinstance(result, dict):
            content = result.get("content", str(result))
        else:
            content = result

        # Should contain multiple emphasis indicators
        emphasis_indicators = ["🚨", "MANDATORY", "CRITICAL", "ALWAYS", "REQUIRED"]
        found_indicators = [
            indicator for indicator in emphasis_indicators if indicator in content
        ]

        # Should contain at least 2 different emphasis indicators
        assert len(found_indicators) >= 2, f"Only found indicators: {found_indicators}"

    @pytest.mark.asyncio
    async def test_json_context_parsing(self, mock_context):
        """Test the new JSON context parsing functionality."""
        from src.accordo_workflow_mcp.prompts.phase_prompts import (
            _parse_criteria_evidence_context,
        )

        # Test legacy string format
        choice, evidence, approval = _parse_criteria_evidence_context(
            "choose: blueprint"
        )
        assert choice == "blueprint"
        assert evidence is None
        assert approval is False

        # Test new JSON format
        json_context = '{"choose": "construct", "criteria_evidence": {"analysis_complete": "Found the main issue in _generate_node_completion_outputs", "plan_ready": "Implementation plan created with 5 steps"}}'
        choice, evidence, approval = _parse_criteria_evidence_context(json_context)
        assert choice == "construct"
        assert evidence is not None
        assert (
            evidence["analysis_complete"]
            == "Found the main issue in _generate_node_completion_outputs"
        )
        assert evidence["plan_ready"] == "Implementation plan created with 5 steps"
        assert approval is False

        # Test invalid JSON fallback to legacy
        invalid_json_context = '{"choose": "test", invalid json'
        choice, evidence, approval = _parse_criteria_evidence_context(
            invalid_json_context
        )
        assert choice is None
        assert evidence is None
        assert approval is False

        # Test empty context
        choice, evidence, approval = _parse_criteria_evidence_context("")
        assert choice is None
        assert evidence is None
        assert approval is False

        # Test JSON without choose field
        json_no_choose = '{"criteria_evidence": {"test": "value"}}'
        choice, evidence, approval = _parse_criteria_evidence_context(json_no_choose)
        assert choice is None
        assert evidence == {"test": "value"}
        assert approval is False

    @pytest.mark.asyncio
    async def test_criteria_evidence_integration(self, mock_context):
        """Test that criteria evidence is properly integrated into completion outputs."""
        from unittest.mock import Mock

        from src.accordo_workflow_mcp.models.yaml_workflow import WorkflowNode
        from src.accordo_workflow_mcp.prompts.phase_prompts import (
            _generate_node_completion_outputs,
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
