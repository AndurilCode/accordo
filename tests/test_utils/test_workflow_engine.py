"""Tests for workflow engine functionality."""

from unittest.mock import Mock, patch

import pytest

from src.accordo_mcp.models.workflow_state import DynamicWorkflowState
from src.accordo_mcp.models.yaml_workflow import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTree,
)
from src.accordo_mcp.utils.workflow_engine import (
    WorkflowEngine,
    WorkflowEngineError,
)


class TestWorkflowEngineError:
    """Test WorkflowEngineError exception."""

    def test_workflow_engine_error_creation(self):
        """Test creating WorkflowEngineError."""
        error = WorkflowEngineError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


class TestWorkflowEngine:
    """Test WorkflowEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a WorkflowEngine instance for testing."""
        with patch("src.accordo_mcp.utils.workflow_engine.WorkflowLoader"):
            engine = WorkflowEngine("test_workflows_dir")
            return engine

    @pytest.fixture
    def mock_workflow_def(self):
        """Create a mock WorkflowDefinition for testing."""
        workflow_def = Mock(spec=WorkflowDefinition)
        workflow_def.name = "Test Workflow"
        workflow_def.description = "Test workflow description"

        # Mock workflow tree
        workflow_tree = Mock(spec=WorkflowTree)
        workflow_tree.root = "start_node"
        workflow_tree.get_node = Mock()

        # Create mock nodes
        start_node = Mock(spec=WorkflowNode)
        start_node.goal = "Start goal"
        start_node.acceptance_criteria = {"criterion1": "description1"}
        start_node.next_allowed_nodes = ["middle_node"]
        start_node.next_allowed_workflows = []
        start_node.children = None

        middle_node = Mock(spec=WorkflowNode)
        middle_node.goal = "Middle goal"
        middle_node.acceptance_criteria = {"criterion2": "description2"}
        middle_node.next_allowed_nodes = ["end_node"]
        middle_node.next_allowed_workflows = []
        middle_node.children = None

        end_node = Mock(spec=WorkflowNode)
        end_node.goal = "End goal"
        end_node.acceptance_criteria = {"criterion3": "description3"}
        end_node.next_allowed_nodes = []
        end_node.next_allowed_workflows = []
        end_node.children = None

        # Configure get_node mock to return appropriate nodes
        def get_node_side_effect(node_name):
            node_map = {
                "start_node": start_node,
                "middle_node": middle_node,
                "end_node": end_node,
            }
            return node_map.get(node_name)

        workflow_tree.get_node.side_effect = get_node_side_effect
        workflow_tree.tree = {
            "start_node": start_node,
            "middle_node": middle_node,
            "end_node": end_node,
        }

        workflow_def.workflow = workflow_tree
        workflow_def.inputs = {"task_description": {"type": "string", "required": True}}

        return workflow_def

    @pytest.fixture
    def mock_state(self):
        """Create a mock DynamicWorkflowState for testing."""
        state = Mock(spec=DynamicWorkflowState)
        state.client_id = "test_client"
        state.workflow_name = "Test Workflow"
        state.current_node = "start_node"
        state.status = "READY"
        state.inputs = {"task_description": "Test task"}
        state.current_item = "Test task"
        state.node_history = [
            "analyze",
            "blueprint",
        ]  # Add node_history for progress tracking
        state.execution_context = {}  # Add execution_context
        state.add_log_entry = Mock()
        state.complete_current_node = Mock()
        state.transition_to_node = Mock(return_value=True)
        return state

    def test_init(self, engine):
        """Test WorkflowEngine initialization."""
        assert engine.workflows_dir == "test_workflows_dir"
        assert engine.loader is not None

    def test_initialize_workflow_with_workflow_name(self, engine, mock_workflow_def):
        """Test initializing workflow with specific workflow name."""
        # Mock loader.discover_workflows
        engine.loader.discover_workflows.return_value = {
            "Test Workflow": mock_workflow_def
        }

        with patch(
            "src.accordo_mcp.utils.workflow_engine.DynamicWorkflowState"
        ) as mock_state_class:
            mock_state_instance = Mock()
            mock_state_class.return_value = mock_state_instance

            state, workflow_def = engine.initialize_workflow(
                client_id="test_client",
                task_description="Test task",
                workflow_name="Test Workflow",
            )

            # Verify workflow discovery was called
            engine.loader.discover_workflows.assert_called_once()

            # Verify state creation
            mock_state_class.assert_called_once_with(
                client_id="test_client",
                workflow_name="Test Workflow",
                current_node="start_node",
                status="READY",
                inputs={"task_description": "Test task"},
                current_item="Test task",
            )

            # Verify log entries
            mock_state_instance.add_log_entry.assert_any_call(
                "🚀 WORKFLOW ENGINE INITIALIZED: Test Workflow"
            )
            mock_state_instance.add_log_entry.assert_any_call(
                "📍 Starting at root node: start_node"
            )
            mock_state_instance.add_log_entry.assert_any_call("🎯 Task: Test task")

            assert state == mock_state_instance
            assert workflow_def == mock_workflow_def

    def test_initialize_workflow_nonexistent_workflow(self, engine):
        """Test initializing workflow with nonexistent workflow name."""
        engine.loader.discover_workflows.return_value = {}

        with pytest.raises(
            WorkflowEngineError, match="Workflow 'NonExistent' not found"
        ):
            engine.initialize_workflow(
                client_id="test_client",
                task_description="Test task",
                workflow_name="NonExistent",
            )

    def test_initialize_workflow_no_workflow_name(self, engine):
        """Test initializing workflow without workflow name raises error."""
        with pytest.raises(WorkflowEngineError, match="Workflow name required"):
            engine.initialize_workflow(
                client_id="test_client",
                task_description="Test task",
                workflow_name=None,
            )

    def test_initialize_workflow_from_definition_success(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test initializing workflow from definition successfully."""
        result = engine.initialize_workflow_from_definition(
            mock_state, mock_workflow_def
        )

        assert result is True
        assert mock_state.workflow_name == "Test Workflow"
        assert mock_state.current_node == "start_node"
        assert mock_state.status == "READY"

        mock_state.add_log_entry.assert_any_call(
            "🚀 WORKFLOW INITIALIZED: Test Workflow"
        )
        mock_state.add_log_entry.assert_any_call("📍 Starting at root node: start_node")

    def test_initialize_workflow_from_definition_failure(
        self, engine, mock_workflow_def
    ):
        """Test initializing workflow from definition with exception."""
        # Create a mock state that raises an exception when add_log_entry is called
        mock_state = Mock()
        mock_state.add_log_entry = Mock(side_effect=Exception("Test error"))

        result = engine.initialize_workflow_from_definition(
            mock_state, mock_workflow_def
        )

        assert result is False

    def test_get_current_node_info_success(self, engine, mock_state, mock_workflow_def):
        """Test getting current node info successfully."""
        result = engine.get_current_node_info(mock_state, mock_workflow_def)

        expected = {
            "node_name": "start_node",
            "goal": "Start goal",
            "acceptance_criteria": {"criterion1": "description1"},
            "next_allowed_nodes": ["middle_node"],
            "next_allowed_workflows": [],
            "is_decision_node": False,
            "children": [],
            "workflow_info": {
                "name": "Test Workflow",
                "description": "Test workflow description",
                "total_nodes": 3,
            },
        }

        assert result == expected

    def test_get_current_node_info_node_not_found(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test getting current node info when node not found."""
        mock_state.current_node = "nonexistent_node"

        result = engine.get_current_node_info(mock_state, mock_workflow_def)

        assert "error" in result
        assert "nonexistent_node" in result["error"]

    def test_get_current_node_info_with_children(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test getting current node info for a decision node with children."""
        # Mock a node with children - need to ensure children is truthy for bool(children) check
        decision_node = Mock(spec=WorkflowNode)
        decision_node.goal = "Decision goal"
        decision_node.acceptance_criteria = {}
        decision_node.next_allowed_nodes = []
        decision_node.next_allowed_workflows = []
        # Create a dict that evaluates to True in boolean context
        children_dict = {"option1": Mock(), "option2": Mock()}
        decision_node.children = children_dict

        # Override the get_node method to return our decision node for the current node
        def get_node_side_effect(node_name):
            if node_name == mock_state.current_node:
                return decision_node
            return None

        mock_workflow_def.workflow.get_node.side_effect = get_node_side_effect

        result = engine.get_current_node_info(mock_state, mock_workflow_def)

        assert result["is_decision_node"] is True
        assert result["children"] == ["option1", "option2"]

    def test_validate_transition_success(self, engine, mock_state, mock_workflow_def):
        """Test validating transition successfully."""
        is_valid, reason = engine.validate_transition(
            mock_state, mock_workflow_def, "middle_node"
        )

        assert is_valid is True
        assert reason == "Transition is valid"

    def test_validate_transition_current_node_not_found(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test validating transition when current node not found."""
        mock_state.current_node = "nonexistent_node"

        is_valid, reason = engine.validate_transition(
            mock_state, mock_workflow_def, "middle_node"
        )

        assert is_valid is False
        assert "Current node 'nonexistent_node' not found" in reason

    def test_validate_transition_target_node_not_found(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test validating transition when target node not found."""
        is_valid, reason = engine.validate_transition(
            mock_state, mock_workflow_def, "nonexistent_target"
        )

        assert is_valid is False
        assert "Target node 'nonexistent_target' not found" in reason

    def test_validate_transition_not_allowed(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test validating transition when not allowed."""
        is_valid, reason = engine.validate_transition(
            mock_state, mock_workflow_def, "end_node"
        )

        assert is_valid is False
        assert "Transition to 'end_node' not allowed" in reason
        assert "Allowed: middle_node" in reason

    def test_execute_transition_success(self, engine, mock_state, mock_workflow_def):
        """Test executing transition successfully."""
        result = engine.execute_transition(mock_state, mock_workflow_def, "middle_node")

        assert result is True
        mock_state.transition_to_node.assert_called_once_with(
            "middle_node", mock_workflow_def
        )

    def test_execute_transition_success_with_outputs(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test executing transition successfully with outputs."""
        outputs = {"result": "success"}

        result = engine.execute_transition(
            mock_state, mock_workflow_def, "middle_node", outputs
        )

        assert result is True
        mock_state.complete_current_node.assert_called_once_with(outputs)
        mock_state.transition_to_node.assert_called_once_with(
            "middle_node", mock_workflow_def
        )

    def test_execute_transition_invalid(self, engine, mock_state, mock_workflow_def):
        """Test executing invalid transition."""
        result = engine.execute_transition(
            mock_state, mock_workflow_def, "invalid_node"
        )

        assert result is False
        mock_state.add_log_entry.assert_called()
        # Verify error log entry was called with failure message
        call_args = mock_state.add_log_entry.call_args[0][0]
        assert "❌ TRANSITION FAILED" in call_args

    def test_execute_transition_state_transition_fails(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test executing transition when state transition fails."""
        mock_state.transition_to_node.return_value = False

        result = engine.execute_transition(mock_state, mock_workflow_def, "middle_node")

        assert result is False

    def test_get_available_transitions(self, engine, mock_state, mock_workflow_def):
        """Test getting available transitions."""
        result = engine.get_available_transitions(mock_state, mock_workflow_def)

        assert len(result) == 1
        assert result[0]["node_name"] == "middle_node"
        assert result[0]["goal"] == "Middle goal"
        assert result[0]["acceptance_criteria"] == {"criterion2": "description2"}

    def test_get_available_transitions_current_node_not_found(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test getting available transitions when current node not found."""
        mock_state.current_node = "nonexistent_node"

        result = engine.get_available_transitions(mock_state, mock_workflow_def)

        assert result == []

    def test_get_available_transitions_target_node_not_found(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test getting available transitions when target node not found."""
        # Mock current node to have a nonexistent target
        start_node = mock_workflow_def.workflow.get_node("start_node")
        start_node.next_allowed_nodes = ["nonexistent_target"]

        result = engine.get_available_transitions(mock_state, mock_workflow_def)

        assert result == []

    def test_check_completion_criteria_no_criteria(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test checking completion criteria when node has no criteria."""
        # Mock node with no acceptance criteria
        node = mock_workflow_def.workflow.get_node("start_node")
        node.acceptance_criteria = {}

        is_complete, missing = engine.check_completion_criteria(
            mock_state, mock_workflow_def
        )

        assert is_complete is True
        assert missing == []

    def test_check_completion_criteria_no_evidence(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test checking completion criteria without evidence."""
        is_complete, missing = engine.check_completion_criteria(
            mock_state, mock_workflow_def
        )

        assert is_complete is False
        assert missing == ["criterion1: description1"]

    def test_check_completion_criteria_with_evidence(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test checking completion criteria with evidence."""
        evidence = {"criterion1": "Evidence provided"}

        is_complete, missing = engine.check_completion_criteria(
            mock_state, mock_workflow_def, evidence
        )

        assert is_complete is True
        assert missing == []

    def test_check_completion_criteria_partial_evidence(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test checking completion criteria with partial evidence."""
        # Add more criteria to the node
        node = mock_workflow_def.workflow.get_node("start_node")
        node.acceptance_criteria = {"criterion1": "desc1", "criterion2": "desc2"}

        evidence = {"criterion1": "Evidence provided"}

        is_complete, missing = engine.check_completion_criteria(
            mock_state, mock_workflow_def, evidence
        )

        assert is_complete is False
        assert missing == ["criterion2: desc2"]

    def test_check_completion_criteria_current_node_not_found(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test checking completion criteria when current node not found."""
        mock_state.current_node = "nonexistent_node"

        is_complete, missing = engine.check_completion_criteria(
            mock_state, mock_workflow_def
        )

        assert is_complete is False
        assert missing == ["Current node not found"]

    def test_get_workflow_progress(self, engine, mock_state, mock_workflow_def):
        """Test getting workflow progress."""
        result = engine.get_workflow_progress(mock_state, mock_workflow_def)

        expected_keys = [
            "current_node",
            "total_nodes",
            "visited_nodes",
            "progress_percentage",
            "node_history",
            "workflow_name",
            "workflow_description",
            "status",
            "execution_context",
        ]
        for key in expected_keys:
            assert key in result

        assert result["current_node"] == "start_node"
        assert result["total_nodes"] == 3
        assert result["visited_nodes"] == 3  # 2 from history + 1 current (unique)
        assert isinstance(result["progress_percentage"], int | float)

    def test_is_workflow_complete_true(self, engine, mock_state, mock_workflow_def):
        """Test checking if workflow is complete when it is."""
        # Mock end node with no next nodes
        mock_state.current_node = "end_node"

        result = engine.is_workflow_complete(mock_state, mock_workflow_def)

        assert result is True

    def test_is_workflow_complete_false(self, engine, mock_state, mock_workflow_def):
        """Test checking if workflow is complete when it's not."""
        result = engine.is_workflow_complete(mock_state, mock_workflow_def)

        assert result is False

    def test_is_workflow_complete_node_not_found(
        self, engine, mock_state, mock_workflow_def
    ):
        """Test checking if workflow is complete when current node not found."""
        mock_state.current_node = "nonexistent_node"

        result = engine.is_workflow_complete(mock_state, mock_workflow_def)

        assert result is False

    def test_prepare_inputs(self, engine, mock_workflow_def):
        """Test preparing inputs from task description."""
        result = engine._prepare_inputs("Test task description", mock_workflow_def)

        assert result == {"task_description": "Test task description"}

    def test_prepare_inputs_no_input_definition(self, engine, mock_workflow_def):
        """Test preparing inputs when workflow has no input definition."""
        mock_workflow_def.inputs = {}

        result = engine._prepare_inputs("Test task description", mock_workflow_def)

        assert result == {"main_task": "Test task description"}
