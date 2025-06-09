"""Tests for node executor functionality."""

from unittest.mock import Mock

import pytest

from src.accordo_workflow_mcp.models.workflow_state import DynamicWorkflowState
from src.accordo_workflow_mcp.models.yaml_workflow import (
    WorkflowDefinition,
    WorkflowNode,
)
from src.accordo_workflow_mcp.utils.node_executor import (
    NodeExecutionResult,
    NodeExecutor,
)


class TestNodeExecutionResult:
    """Test NodeExecutionResult class."""

    def test_init_with_defaults(self):
        """Test NodeExecutionResult initialization with default values."""
        result = NodeExecutionResult(success=True)

        assert result.success is True
        assert result.outputs == {}
        assert result.message == ""
        assert result.next_node_suggestion is None

    def test_init_with_all_parameters(self):
        """Test NodeExecutionResult initialization with all parameters."""
        outputs = {"key": "value"}
        result = NodeExecutionResult(
            success=False,
            outputs=outputs,
            message="Test message",
            next_node_suggestion="next_node",
        )

        assert result.success is False
        assert result.outputs == outputs
        assert result.message == "Test message"
        assert result.next_node_suggestion == "next_node"

    def test_init_with_none_outputs(self):
        """Test NodeExecutionResult initialization with None outputs."""
        result = NodeExecutionResult(success=True, outputs=None)

        assert result.outputs == {}


class TestNodeExecutor:
    """Test NodeExecutor class."""

    @pytest.fixture
    def executor(self):
        """Create a NodeExecutor instance for testing."""
        return NodeExecutor()

    @pytest.fixture
    def mock_state(self):
        """Create a mock DynamicWorkflowState for testing."""
        state = Mock(spec=DynamicWorkflowState)
        state.current_node = "test_node"
        state.current_item = "Test task"
        state.inputs = {"task_description": "Test task"}
        state.execution_context = {}
        state.add_log_entry = Mock()
        return state

    @pytest.fixture
    def mock_workflow_def(self):
        """Create a mock WorkflowDefinition for testing."""
        workflow_def = Mock(spec=WorkflowDefinition)
        workflow_def.name = "Test Workflow"

        # Mock the workflow attribute
        workflow_def.workflow = Mock()
        workflow_def.workflow.get_node = Mock(return_value=None)

        return workflow_def

    @pytest.fixture
    def action_node(self):
        """Create a mock action node (no children)."""
        node = Mock(spec=WorkflowNode)
        node.goal = "Test action goal"
        node.children = None
        node.acceptance_criteria = {
            "criterion1": "First criterion",
            "criterion2": "Second criterion",
        }
        node.next_allowed_nodes = ["next_node"]
        return node

    @pytest.fixture
    def decision_node(self):
        """Create a mock decision node (with children)."""
        child1 = Mock(spec=WorkflowNode)
        child1.goal = "Child 1 goal"
        child1.acceptance_criteria = {"child1_criterion": "Child 1 criterion"}

        child2 = Mock(spec=WorkflowNode)
        child2.goal = "Child 2 goal"
        child2.acceptance_criteria = {"child2_criterion": "Child 2 criterion"}

        node = Mock(spec=WorkflowNode)
        node.goal = "Test decision goal"
        node.children = {"child1": child1, "child2": child2}
        node.acceptance_criteria = {}
        return node

    def test_execute_node_action_node(
        self, executor, action_node, mock_state, mock_workflow_def
    ):
        """Test executing an action node."""
        result = executor.execute_node(action_node, mock_state, mock_workflow_def)

        # Verify logging calls
        mock_state.add_log_entry.assert_any_call("🎯 EXECUTING NODE: test_node")
        mock_state.add_log_entry.assert_any_call("📋 GOAL: Test action goal")
        mock_state.add_log_entry.assert_any_call("⚡ ACTION NODE: Executing goal")

        # Verify result
        assert isinstance(result, NodeExecutionResult)
        assert result.success is True
        assert "execution_guidance" in result.outputs

    def test_execute_node_decision_node(
        self, executor, decision_node, mock_state, mock_workflow_def
    ):
        """Test executing a decision node."""
        result = executor.execute_node(decision_node, mock_state, mock_workflow_def)

        # Verify logging calls
        mock_state.add_log_entry.assert_any_call("🎯 EXECUTING NODE: test_node")
        mock_state.add_log_entry.assert_any_call("📋 GOAL: Test decision goal")
        mock_state.add_log_entry.assert_any_call(
            "🔀 DECISION NODE: 2 options available"
        )

        # Verify result
        assert isinstance(result, NodeExecutionResult)

    def test_execute_decision_node_with_user_choice(
        self, executor, decision_node, mock_state, mock_workflow_def
    ):
        """Test executing a decision node with user choice."""
        user_input = {"decision": "child1"}

        result = executor._execute_decision_node(
            decision_node, mock_state, mock_workflow_def, user_input
        )

        assert result.success is True
        assert result.outputs["decision"] == "child1"
        assert result.outputs["decision_type"] == "user_choice"
        assert result.next_node_suggestion == "child1"
        mock_state.add_log_entry.assert_any_call("👤 USER DECISION: child1")

    def test_execute_decision_node_with_invalid_user_choice(
        self, executor, decision_node, mock_state, mock_workflow_def
    ):
        """Test executing a decision node with invalid user choice."""
        user_input = {"decision": "invalid_child"}

        result = executor._execute_decision_node(
            decision_node, mock_state, mock_workflow_def, user_input
        )

        assert result.success is False
        assert "Invalid decision 'invalid_child'" in result.message
        assert "child1, child2" in result.message

    def test_execute_decision_node_auto_decision(
        self, executor, decision_node, mock_state, mock_workflow_def
    ):
        """Test executing a decision node with auto decision."""
        # Mock the auto_decide_child method to return a choice
        executor._auto_decide_child = Mock(return_value="child2")

        result = executor._execute_decision_node(
            decision_node, mock_state, mock_workflow_def
        )

        assert result.success is True
        assert result.outputs["decision"] == "child2"
        assert result.outputs["decision_type"] == "auto_choice"
        assert result.next_node_suggestion == "child2"
        mock_state.add_log_entry.assert_any_call("🤖 AUTO DECISION: child2")

    def test_execute_decision_node_no_auto_decision(
        self, executor, decision_node, mock_state, mock_workflow_def
    ):
        """Test executing a decision node when no auto decision can be made."""
        # Mock the auto_decide_child method to return None
        executor._auto_decide_child = Mock(return_value=None)

        result = executor._execute_decision_node(
            decision_node, mock_state, mock_workflow_def
        )

        assert result.success is False
        assert "Decision required" in result.message
        assert "available_choices" in result.outputs
        assert "child1" in result.outputs["available_choices"]
        assert "child2" in result.outputs["available_choices"]

    def test_execute_action_node_basic(
        self, executor, action_node, mock_state, mock_workflow_def
    ):
        """Test executing a basic action node."""
        result = executor._execute_action_node(
            action_node, mock_state, mock_workflow_def
        )

        # Verify state updates
        assert mock_state.execution_context["current_goal"] == "Test action goal"
        assert mock_state.execution_context["node_name"] == "test_node"

        # Verify logging of acceptance criteria
        mock_state.add_log_entry.assert_any_call("📋 ACCEPTANCE CRITERIA:")
        mock_state.add_log_entry.assert_any_call("  • criterion1: First criterion")
        mock_state.add_log_entry.assert_any_call("  • criterion2: Second criterion")

        assert result.success is True
        assert "execution_guidance" in result.outputs

    def test_execute_action_node_with_criteria_evidence(
        self, executor, action_node, mock_state, mock_workflow_def
    ):
        """Test executing an action node with criteria evidence provided."""
        user_input = {
            "criteria_evidence": {
                "criterion1": "Evidence for criterion 1",
                "criterion2": "Evidence for criterion 2",
            }
        }

        result = executor._execute_action_node(
            action_node, mock_state, mock_workflow_def, user_input
        )

        assert result.success is True
        assert result.outputs["goal_achieved"] is True
        assert (
            result.outputs["completed_criteria"]["criterion1"]
            == "Evidence for criterion 1"
        )
        assert (
            result.outputs["completed_criteria"]["criterion2"]
            == "Evidence for criterion 2"
        )
        assert result.next_node_suggestion == "next_node"

        # Verify logging of completed criteria
        mock_state.add_log_entry.assert_any_call(
            "✅ criterion1: Evidence for criterion 1"
        )
        mock_state.add_log_entry.assert_any_call(
            "✅ criterion2: Evidence for criterion 2"
        )

    def test_execute_action_node_with_partial_criteria_evidence(
        self, executor, action_node, mock_state, mock_workflow_def
    ):
        """Test executing an action node with partial criteria evidence."""
        user_input = {
            "criteria_evidence": {
                "criterion1": "Evidence for criterion 1"
                # Missing criterion2
            }
        }

        result = executor._execute_action_node(
            action_node, mock_state, mock_workflow_def, user_input
        )

        # Should not be marked as complete since not all criteria are met
        assert result.success is True
        assert "goal_achieved" not in result.outputs or not result.outputs.get(
            "goal_achieved"
        )

    def test_auto_decide_child_no_children(
        self, executor, mock_state, mock_workflow_def
    ):
        """Test auto_decide_child with a node that has no children."""
        # Create a node with no children (None)
        node = Mock(spec=WorkflowNode)
        node.children = None

        result = executor._auto_decide_child(node, mock_state, mock_workflow_def)

        assert result is None

    def test_auto_decide_child_with_children(
        self, executor, decision_node, mock_state, mock_workflow_def
    ):
        """Test auto_decide_child with a decision node."""
        # This method contains heuristic logic that might return None or a child name
        result = executor._auto_decide_child(
            decision_node, mock_state, mock_workflow_def
        )

        # The result should be either None or one of the child names
        assert result is None or result in decision_node.children

    def test_generate_execution_guidance(
        self, executor, action_node, mock_state, mock_workflow_def
    ):
        """Test generation of execution guidance."""
        guidance = executor._generate_execution_guidance(
            action_node, mock_state, mock_workflow_def
        )

        assert isinstance(guidance, str)
        assert len(guidance) > 0
        assert "Test action goal" in guidance

    def test_check_node_completion_no_evidence(self, executor, action_node, mock_state):
        """Test checking node completion without evidence."""
        is_complete, missing, completed = executor.check_node_completion(
            action_node, mock_state
        )

        assert is_complete is False
        assert "criterion1: First criterion" in missing
        assert "criterion2: Second criterion" in missing
        assert len(completed) == 0

    def test_check_node_completion_with_evidence(
        self, executor, action_node, mock_state
    ):
        """Test checking node completion with evidence."""
        evidence = {"criterion1": "Evidence 1", "criterion2": "Evidence 2"}

        is_complete, missing, completed = executor.check_node_completion(
            action_node, mock_state, evidence
        )

        assert is_complete is True
        assert len(missing) == 0
        assert completed["criterion1"] == "Evidence 1"
        assert completed["criterion2"] == "Evidence 2"

    def test_check_node_completion_partial_evidence(
        self, executor, action_node, mock_state
    ):
        """Test checking node completion with partial evidence."""
        evidence = {
            "criterion1": "Evidence 1"
            # Missing criterion2
        }

        is_complete, missing, completed = executor.check_node_completion(
            action_node, mock_state, evidence
        )

        assert is_complete is False
        assert "criterion2: Second criterion" in missing
        assert completed["criterion1"] == "Evidence 1"
        assert "criterion2" not in completed

    def test_check_node_completion_no_criteria(self, executor, mock_state):
        """Test checking node completion for a node with no acceptance criteria."""
        node = Mock(spec=WorkflowNode)
        node.acceptance_criteria = {}

        is_complete, missing, completed = executor.check_node_completion(
            node, mock_state
        )

        assert is_complete is True
        assert len(missing) == 0
        assert len(completed) == 0

    def test_execute_node_with_user_input(
        self, executor, action_node, mock_state, mock_workflow_def
    ):
        """Test executing a node with user input."""
        user_input = {"custom_param": "custom_value"}

        result = executor.execute_node(
            action_node, mock_state, mock_workflow_def, user_input
        )

        assert result.success is True
        assert mock_state.execution_context["user_input"] == user_input

    def test_execute_action_node_no_acceptance_criteria(
        self, executor, mock_state, mock_workflow_def
    ):
        """Test executing an action node with no acceptance criteria."""
        node = Mock(spec=WorkflowNode)
        node.goal = "Simple goal"
        node.children = None
        node.acceptance_criteria = {}
        node.next_allowed_nodes = []

        result = executor._execute_action_node(node, mock_state, mock_workflow_def)

        assert result.success is True
        # Should not log acceptance criteria section
        mock_state.add_log_entry.assert_any_call("⚡ ACTION NODE: Executing goal")

    def test_execute_action_node_no_next_nodes(
        self, executor, mock_state, mock_workflow_def
    ):
        """Test executing an action node with no next allowed nodes."""
        node = Mock(spec=WorkflowNode)
        node.goal = "Terminal goal"
        node.children = None
        node.acceptance_criteria = {"criterion": "test"}
        node.next_allowed_nodes = []

        user_input = {"criteria_evidence": {"criterion": "Evidence"}}

        result = executor._execute_action_node(
            node, mock_state, mock_workflow_def, user_input
        )

        assert result.success is True
        assert result.next_node_suggestion is None
