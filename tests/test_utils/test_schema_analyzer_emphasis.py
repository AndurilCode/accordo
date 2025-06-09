"""Tests for schema analyzer emphasis enhancements."""

from unittest.mock import Mock

import pytest

from src.accordo_mcp.models.yaml_workflow import WorkflowDefinition, WorkflowNode
from src.accordo_mcp.utils.schema_analyzer import format_node_status


class TestSchemaAnalyzerEmphasis:
    """Test enhanced emphasis in schema analyzer functions."""

    @pytest.fixture
    def mock_workflow_def(self):
        """Create a mock WorkflowDefinition for testing."""
        workflow_def = Mock(spec=WorkflowDefinition)
        workflow_def.name = "Test Workflow"
        workflow_def.description = "Test workflow description"
        return workflow_def

    @pytest.fixture
    def single_transition_node(self):
        """Create a mock node with single transition option."""
        node = Mock(spec=WorkflowNode)
        node.goal = "Test single transition goal"
        node.acceptance_criteria = {
            "criterion1": "First acceptance criterion",
            "criterion2": "Second acceptance criterion",
        }
        node.next_allowed_nodes = ["next_node"]
        node.next_allowed_workflows = []
        return node

    @pytest.fixture
    def multiple_transition_node(self):
        """Create a mock node with multiple transition options."""
        node = Mock(spec=WorkflowNode)
        node.goal = "Test multiple transition goal"
        node.acceptance_criteria = {
            "analysis_complete": "Complete analysis requirement",
            "plan_ready": "Implementation plan requirement",
        }
        node.next_allowed_nodes = ["blueprint", "construct", "validate"]
        node.next_allowed_workflows = []
        return node

    @pytest.fixture
    def terminal_node(self):
        """Create a mock terminal node with no transitions."""
        node = Mock(spec=WorkflowNode)
        node.goal = "Terminal node goal"
        node.acceptance_criteria = {"final_check": "Final validation"}
        node.next_allowed_nodes = []
        node.next_allowed_workflows = []
        return node

    def test_format_node_status_contains_critical_emphasis(
        self, single_transition_node, mock_workflow_def
    ):
        """Test that format_node_status contains critical emphasis indicators."""
        result = format_node_status(single_transition_node, mock_workflow_def)

        # Check for critical emphasis indicators
        assert "🚨" in result
        assert "CRITICAL" in result
        assert "ALWAYS provide criteria evidence" in result

    def test_format_node_status_single_transition_example(
        self, single_transition_node, mock_workflow_def
    ):
        """Test that single transition shows specific node example."""
        result = format_node_status(single_transition_node, mock_workflow_def)

        # Should contain specific example with the actual next node name
        assert '"choose": "next_node"' in result
        assert '"criteria_evidence":' in result
        assert '"criterion1": "detailed evidence"' in result

    def test_format_node_status_multiple_transition_example(
        self, multiple_transition_node, mock_workflow_def
    ):
        """Test that multiple transitions show generic example."""
        result = format_node_status(multiple_transition_node, mock_workflow_def)

        # Should contain generic example for multiple options
        assert '"choose": "node_name"' in result
        assert '"criteria_evidence":' in result
        assert '"criterion1": "detailed evidence"' in result

    def test_format_node_status_terminal_node_no_transition_guidance(
        self, terminal_node, mock_workflow_def
    ):
        """Test that terminal nodes don't show transition guidance."""
        result = format_node_status(terminal_node, mock_workflow_def)

        # Terminal nodes should not contain transition guidance
        assert "🚨 CRITICAL:" not in result
        assert "ALWAYS provide criteria evidence" not in result
        assert "choose:" not in result
        assert "This is a terminal node" in result

    def test_format_node_status_json_format_preference(
        self, single_transition_node, mock_workflow_def
    ):
        """Test that JSON format is strongly emphasized over string format."""
        result = format_node_status(single_transition_node, mock_workflow_def)

        # Should emphasize JSON format
        assert 'action="next"' in result
        assert "context=" in result
        assert "{" in result and "}" in result  # JSON structure

        # Should not show the legacy string format as primary example
        assert 'context="choose: next_node"' not in result or result.count("{") > 0

    def test_format_node_status_maintains_goal_and_criteria(
        self, single_transition_node, mock_workflow_def
    ):
        """Test that original functionality (goal and criteria) is maintained."""
        result = format_node_status(single_transition_node, mock_workflow_def)

        # Original functionality should remain
        assert "Test single transition goal" in result
        assert "criterion1" in result
        assert "First acceptance criterion" in result
        assert "criterion2" in result
        assert "Second acceptance criterion" in result

    def test_format_node_status_structure_consistency(
        self, multiple_transition_node, mock_workflow_def
    ):
        """Test that the overall structure remains consistent."""
        result = format_node_status(multiple_transition_node, mock_workflow_def)

        # Should maintain expected structure sections
        assert "Current Goal:" in result
        assert "Acceptance Criteria:" in result
        assert "Available Next Steps:" in result
        assert "To Proceed:" in result

        # Lines should be properly formatted
        lines = result.split("\n")
        assert len(lines) > 5  # Should have multiple lines

        # Should have proper markdown formatting
        assert any("**" in line for line in lines)
