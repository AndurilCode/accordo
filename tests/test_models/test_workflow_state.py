"""Tests for workflow state models."""

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.accordo_workflow_mcp.models.workflow_state import (
    WorkflowItem,
    WorkflowState,
)


class TestWorkflowItem:
    """Test WorkflowItem model."""

    def test_valid_creation(self):
        """Test creating a valid WorkflowItem."""
        item = WorkflowItem(id=1, description="Test task")
        assert item.id == 1
        assert item.description == "Test task"
        assert item.status == "pending"  # Default value

    def test_custom_status(self):
        """Test creating WorkflowItem with custom status."""
        item = WorkflowItem(id=2, description="Done task", status="completed")
        assert item.id == 2
        assert item.description == "Done task"
        assert item.status == "completed"

    def test_validation_error_missing_id(self):
        """Test that missing id raises validation error."""
        with pytest.raises(ValidationError):
            WorkflowItem(description="Test task")

    def test_validation_error_missing_description(self):
        """Test that missing description raises validation error."""
        with pytest.raises(ValidationError):
            WorkflowItem(id=1)

    def test_serialization(self):
        """Test that WorkflowItem can be serialized."""
        item = WorkflowItem(id=1, description="Test task", status="completed")
        data = item.model_dump()
        assert data == {"id": 1, "description": "Test task", "status": "completed"}


class TestWorkflowState:
    """Test WorkflowState model."""

    def test_valid_creation(self):
        """Test creating a valid WorkflowState."""
        state = WorkflowState(phase="INIT", status="READY")
        assert state.phase == "INIT"
        assert state.status == "READY"
        assert state.current_item is None
        assert state.plan == ""
        assert state.items == []
        assert state.log == []
        assert state.archive_log == []
        assert isinstance(state.last_updated, datetime)

    def test_creation_with_all_fields(self):
        """Test creating WorkflowState with all fields."""
        items = [WorkflowItem(id=1, description="Task 1")]
        state = WorkflowState(
            phase="BLUEPRINT",
            status="RUNNING",
            current_item="Current task",
            plan="Test plan",
            items=items,
            log=["Test log"],
            archive_log=["Archive log"],
        )
        assert state.phase == "BLUEPRINT"
        assert state.status == "RUNNING"
        assert state.current_item == "Current task"
        assert state.plan == "Test plan"
        assert len(state.items) == 1
        assert state.log == ["Test log"]
        assert state.archive_log == ["Archive log"]

    @patch("src.accordo_workflow_mcp.models.workflow_state.datetime")
    def test_add_log_entry(self, mock_datetime):
        """Test adding log entry with timestamp."""
        # Mock datetime.now() to return a fixed time
        mock_datetime.now.return_value.strftime.return_value = "12:34:56"

        state = WorkflowState(phase="INIT", status="READY")

        state.add_log_entry("Test entry")

        assert state.log == ["[12:34:56] Test entry"]
        mock_datetime.now.assert_called_once()

    @patch("src.accordo_workflow_mcp.models.workflow_state.datetime")
    def test_add_multiple_log_entries(self, mock_datetime):
        """Test adding multiple log entries."""
        mock_datetime.now.return_value.strftime.side_effect = ["12:34:56", "12:35:00"]

        state = WorkflowState(phase="INIT", status="READY")

        state.add_log_entry("First entry")
        state.add_log_entry("Second entry")

        expected_log = ["[12:34:56] First entry", "[12:35:00] Second entry"]
        assert state.log == expected_log

    def test_rotate_log_when_over_5000_chars(self):
        """Test that log rotates when it exceeds 5000 characters."""
        state = WorkflowState(phase="INIT", status="READY")

        # Create a log entry that's over 5000 characters
        long_entry = "x" * 5001
        state.log = [long_entry]

        state.rotate_log()

        assert state.archive_log == [long_entry]
        assert state.log == []

    def test_rotate_log_with_existing_archive(self):
        """Test log rotation when archive already has content."""
        state = WorkflowState(phase="INIT", status="READY")

        state.archive_log = ["Existing archive"]
        state.log = ["Current log"]

        state.rotate_log()

        expected_archive = ["Existing archive", "--- LOG ROTATION ---", "Current log"]
        assert state.archive_log == expected_archive
        assert state.log == []

    @patch("src.accordo_workflow_mcp.models.workflow_state.datetime")
    def test_add_log_entry_triggers_rotation(self, mock_datetime):
        """Test that adding log entry triggers rotation when over 5000 chars."""
        mock_datetime.now.return_value.strftime.return_value = "12:34:56"

        state = WorkflowState(phase="INIT", status="READY")

        # Set log to be just under 5000 chars
        state.log = ["x" * 4990]

        # Add entry that pushes it over 5000
        state.add_log_entry("This will trigger rotation")

        # Log should be rotated (moved to archive) and log should be cleared
        assert "x" * 4990 in state.archive_log
        assert "[12:34:56] This will trigger rotation" in state.archive_log
        assert state.log == []

    def test_get_next_pending_item_with_pending_items(self):
        """Test getting next pending item when pending items exist."""
        items = [
            WorkflowItem(id=1, description="Task 1", status="completed"),
            WorkflowItem(id=2, description="Task 2", status="pending"),
            WorkflowItem(id=3, description="Task 3", status="pending"),
        ]
        state = WorkflowState(phase="INIT", status="READY", items=items)

        next_item = state.get_next_pending_item()

        assert next_item is not None
        assert next_item.id == 2
        assert next_item.description == "Task 2"
        assert next_item.status == "pending"

    def test_get_next_pending_item_no_pending_items(self):
        """Test getting next pending item when no pending items exist."""
        items = [
            WorkflowItem(id=1, description="Task 1", status="completed"),
            WorkflowItem(id=2, description="Task 2", status="completed"),
        ]
        state = WorkflowState(phase="INIT", status="READY", items=items)

        next_item = state.get_next_pending_item()

        assert next_item is None

    def test_get_next_pending_item_empty_items(self):
        """Test getting next pending item when items list is empty."""
        state = WorkflowState(phase="INIT", status="READY", items=[])

        next_item = state.get_next_pending_item()

        assert next_item is None

    def test_mark_item_completed_success(self):
        """Test marking an existing item as completed."""
        items = [
            WorkflowItem(id=1, description="Task 1", status="pending"),
            WorkflowItem(id=2, description="Task 2", status="pending"),
        ]
        state = WorkflowState(phase="INIT", status="READY", items=items)

        result = state.mark_item_completed(1)

        assert result is True
        assert state.items[0].status == "completed"
        assert state.items[1].status == "pending"  # Unchanged

    def test_mark_item_completed_item_not_found(self):
        """Test marking a non-existent item as completed."""
        items = [
            WorkflowItem(id=1, description="Task 1", status="pending"),
        ]
        state = WorkflowState(phase="INIT", status="READY", items=items)

        result = state.mark_item_completed(999)

        assert result is False
        assert state.items[0].status == "pending"  # Unchanged

    def test_mark_item_completed_empty_items(self):
        """Test marking item as completed when items list is empty."""
        state = WorkflowState(phase="INIT", status="READY", items=[])

        result = state.mark_item_completed(1)

        assert result is False

    def test_validation_error_missing_phase(self):
        """Test that missing phase raises validation error."""
        with pytest.raises(ValidationError):
            WorkflowState(status="READY")

    def test_validation_error_missing_status(self):
        """Test that missing status raises validation error."""
        with pytest.raises(ValidationError):
            WorkflowState(phase="INIT")

    def test_serialization(self):
        """Test that WorkflowState can be serialized."""
        items = [WorkflowItem(id=1, description="Task 1")]
        state = WorkflowState(
            phase="BLUEPRINT",
            status="RUNNING",
            current_item="Current task",
            plan="Test plan",
            items=items,
            log=["Test log"],
            archive_log=["Archive log"],
        )

        data = state.model_dump()

        assert data["phase"] == "BLUEPRINT"
        assert data["status"] == "RUNNING"
        assert data["current_item"] == "Current task"
        assert data["plan"] == "Test plan"
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == 1
        assert data["log"] == ["Test log"]
        assert data["archive_log"] == ["Archive log"]
        assert "last_updated" in data


class TestWorkflowStateJsonExport:
    """Test WorkflowState JSON export functionality."""

    def test_to_json_basic(self):
        """Test basic to_json functionality."""
        state = WorkflowState(
            phase="INIT",
            status="READY",
            client_id="test-client",
        )
        json_str = state.to_json()

        # Should be valid JSON
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_to_json_structure(self):
        """Test to_json returns expected structure."""
        state = WorkflowState(
            phase="ANALYZE",
            status="RUNNING",
            client_id="test-client",
            current_item="Test task",
            plan="Test plan",
            log=["Test log"],
            archive_log=["Test archive"],
        )
        json_str = state.to_json()
        data = json.loads(json_str)

        # Check top-level structure
        assert "metadata" in data
        assert "state" in data
        assert "plan" in data
        assert "items" in data
        assert "log" in data
        assert "archive_log" in data

    def test_to_json_metadata_fields(self):
        """Test to_json metadata section contains expected fields."""
        state = WorkflowState(
            phase="INIT",
            status="READY",
            client_id="test-client",
        )
        json_str = state.to_json()
        data = json.loads(json_str)

        metadata = data["metadata"]
        assert "last_updated" in metadata
        assert "client_id" in metadata
        assert "created_at" in metadata
        assert metadata["client_id"] == "test-client"

    def test_to_json_state_fields(self):
        """Test to_json state section contains expected fields."""
        state = WorkflowState(
            phase="BLUEPRINT",
            status="NEEDS_PLAN_APPROVAL",
            client_id="test-client",
            current_item="Current task",
        )
        json_str = state.to_json()
        data = json.loads(json_str)

        state_data = data["state"]
        assert "phase" in state_data
        assert "status" in state_data
        assert "current_item" in state_data
        assert state_data["phase"] == "BLUEPRINT"
        assert state_data["status"] == "NEEDS_PLAN_APPROVAL"
        assert state_data["current_item"] == "Current task"

    def test_to_json_with_items(self):
        """Test to_json includes items array with complete item data."""
        items = [
            WorkflowItem(id=1, description="Task 1", status="pending"),
            WorkflowItem(id=2, description="Task 2", status="completed"),
        ]
        state = WorkflowState(
            phase="INIT",
            status="READY",
            items=items,
        )
        json_str = state.to_json()
        data = json.loads(json_str)

        items_data = data["items"]
        assert isinstance(items_data, list)
        assert len(items_data) == 2

        # Check first item
        item1 = items_data[0]
        assert item1["id"] == 1
        assert item1["description"] == "Task 1"
        assert item1["status"] == "pending"

        # Check second item
        item2 = items_data[1]
        assert item2["id"] == 2
        assert item2["description"] == "Task 2"
        assert item2["status"] == "completed"

    def test_to_json_with_plan_and_logs(self):
        """Test to_json includes plan and log data."""
        state = WorkflowState(
            phase="CONSTRUCT",
            status="RUNNING",
            plan="Detailed implementation plan",
            log=["Implementation log entry"],
            archive_log=["Previous log entries"],
        )
        json_str = state.to_json()
        data = json.loads(json_str)

        assert data["plan"] == "Detailed implementation plan"
        assert data["log"] == ["Implementation log entry"]
        assert data["archive_log"] == ["Previous log entries"]

    def test_to_json_empty_values_as_null(self):
        """Test to_json represents empty strings as null."""
        state = WorkflowState(
            phase="INIT",
            status="READY",
            plan="",
            log=[],
            archive_log=[],
        )
        json_str = state.to_json()
        data = json.loads(json_str)

        assert data["plan"] is None
        assert data["log"] is None
        assert data["archive_log"] is None

    def test_to_json_current_item_null(self):
        """Test to_json handles None current_item correctly."""
        state = WorkflowState(
            phase="INIT",
            status="READY",
            current_item=None,
        )
        json_str = state.to_json()
        data = json.loads(json_str)

        assert data["state"]["current_item"] is None

    def test_to_json_empty_items_array(self):
        """Test to_json handles empty items array correctly."""
        state = WorkflowState(
            phase="INIT",
            status="READY",
        )
        json_str = state.to_json()
        data = json.loads(json_str)

        assert data["items"] == []

    def test_to_json_datetime_serialization(self):
        """Test to_json properly serializes datetime fields."""
        state = WorkflowState(
            phase="INIT",
            status="READY",
        )
        json_str = state.to_json()
        data = json.loads(json_str)

        # Should be ISO format strings
        last_updated = data["metadata"]["last_updated"]
        created_at = data["metadata"]["created_at"]

        # Should be parseable as ISO datetime
        from datetime import datetime

        datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))

    def test_to_json_consistent_output(self):
        """Test to_json produces consistent output for same state."""
        state = WorkflowState(
            phase="ANALYZE",
            status="RUNNING",
            client_id="consistent-test",
            plan="Same plan",
        )

        # Export twice
        json1 = state.to_json()
        json2 = state.to_json()

        # Parse both
        data1 = json.loads(json1)
        data2 = json.loads(json2)

        # Non-timestamp fields should be identical
        assert data1["state"] == data2["state"]
        assert data1["plan"] == data2["plan"]
        assert data1["items"] == data2["items"]
        assert data1["metadata"]["client_id"] == data2["metadata"]["client_id"]

    def test_to_json_formatting(self):
        """Test to_json produces properly formatted JSON."""
        state = WorkflowState(
            phase="INIT",
            status="READY",
        )
        json_str = state.to_json()

        # Should have indentation (formatted JSON)
        assert "  " in json_str or "\t" in json_str

        # Should have newlines
        assert "\n" in json_str

    def test_to_json_complete_data_integrity(self):
        """Test to_json maintains complete data integrity with complex state."""
        items = [
            WorkflowItem(id=1, description="Complex task 1", status="pending"),
            WorkflowItem(id=2, description="Complex task 2", status="completed"),
            WorkflowItem(id=3, description="Complex task 3", status="in-progress"),
        ]

        state = WorkflowState(
            phase="VALIDATE",
            status="COMPLETED",
            client_id="complex-test-client",
            current_item="Final validation task",
            plan="Complex multi-step plan with detailed instructions",
            items=items,
            log=["Detailed log with multiple entries and timestamps"],
            archive_log=["Historical log data from previous phases"],
        )

        json_str = state.to_json()
        data = json.loads(json_str)

        # Verify all data is present and correct
        assert data["metadata"]["client_id"] == "complex-test-client"
        assert data["state"]["phase"] == "VALIDATE"
        assert data["state"]["status"] == "COMPLETED"
        assert data["state"]["current_item"] == "Final validation task"
        assert data["plan"] == "Complex multi-step plan with detailed instructions"
        assert len(data["items"]) == 3
        assert data["items"][2]["description"] == "Complex task 3"
        assert data["items"][2]["status"] == "in-progress"
        assert data["log"] == ["Detailed log with multiple entries and timestamps"]
        assert data["archive_log"] == ["Historical log data from previous phases"]


class TestDynamicWorkflowStateProgress:
    """Test DynamicWorkflowState progress tracking functionality."""

    @pytest.fixture
    def mock_workflow_def(self):
        """Create a mock WorkflowDefinition for testing."""
        from unittest.mock import Mock

        from src.accordo_workflow_mcp.models.yaml_workflow import (
            WorkflowDefinition,
            WorkflowNode,
            WorkflowTree,
        )

        # Create mock nodes
        analyze_node = Mock(spec=WorkflowNode)
        analyze_node.goal = "Analyze the requirements and understand the codebase"
        analyze_node.acceptance_criteria = {
            "requirements_analysis": "Clear breakdown of task requirements",
            "codebase_exploration": "Understanding of current architecture",
        }
        analyze_node.next_allowed_nodes = ["blueprint"]

        blueprint_node = Mock(spec=WorkflowNode)
        blueprint_node.goal = "Create implementation plan and design"
        blueprint_node.acceptance_criteria = {
            "solution_architecture": "Complete technical approach documented",
            "implementation_plan": "Detailed step-by-step plan created",
        }
        blueprint_node.next_allowed_nodes = ["construct"]

        construct_node = Mock(spec=WorkflowNode)
        construct_node.goal = "Implement the planned solution"
        construct_node.acceptance_criteria = {
            "step_execution": "All planned steps executed",
            "quality_validation": "Code follows project standards",
        }
        construct_node.next_allowed_nodes = ["validate"]

        # Create mock workflow tree
        workflow_tree = Mock(spec=WorkflowTree)
        workflow_tree.get_node = Mock(
            side_effect=lambda name: {
                "analyze": analyze_node,
                "blueprint": blueprint_node,
                "construct": construct_node,
            }.get(name)
        )
        workflow_tree.tree = {
            "analyze": analyze_node,
            "blueprint": blueprint_node,
            "construct": construct_node,
        }

        # Create mock workflow definition
        workflow_def = Mock(spec=WorkflowDefinition)
        workflow_def.name = "Test Workflow"
        workflow_def.description = "Test workflow for progress tracking"
        workflow_def.workflow = workflow_tree

        return workflow_def

    @pytest.fixture
    def dynamic_state_with_progress(self, mock_workflow_def):
        """Create a DynamicWorkflowState with completed nodes and outputs."""
        from src.accordo_workflow_mcp.models.workflow_state import DynamicWorkflowState

        state = DynamicWorkflowState(
            workflow_name="Test Workflow",
            current_node="construct",
            status="RUNNING",
            node_history=["analyze", "blueprint"],
            node_outputs={
                "analyze": {
                    "completed_criteria": {
                        "requirements_analysis": "Successfully analyzed task requirements and identified scope",
                        "codebase_exploration": "Explored existing codebase and understood architecture patterns",
                    },
                    "goal_achieved": True,
                    "additional_info": "Found relevant patterns in existing code",
                },
                "blueprint": {
                    "completed_criteria": {
                        "solution_architecture": "Designed comprehensive solution with clear architecture",
                        "implementation_plan": "Created detailed 5-step implementation plan",
                    },
                    "goal_achieved": True,
                    "risk_assessment": "Low risk implementation with clear rollback plan",
                },
            },
        )
        return state

    def test_to_markdown_includes_completed_nodes_progress(
        self, dynamic_state_with_progress, mock_workflow_def
    ):
        """Test that to_markdown includes completed nodes progress section."""
        markdown = dynamic_state_with_progress.to_markdown(mock_workflow_def)

        # Check that completed nodes progress section exists
        assert "## Completed Nodes Progress" in markdown

        # Check that completed nodes are listed
        assert "### 🎯 analyze" in markdown
        assert "### 🎯 blueprint" in markdown

        # Check that goals are included
        assert "Analyze the requirements and understand the codebase" in markdown
        assert "Create implementation plan and design" in markdown

    def test_to_markdown_shows_acceptance_criteria_satisfaction(
        self, dynamic_state_with_progress, mock_workflow_def
    ):
        """Test that markdown shows which acceptance criteria were satisfied."""
        markdown = dynamic_state_with_progress.to_markdown(mock_workflow_def)

        # Check acceptance criteria satisfaction for analyze node
        assert (
            "✅ **requirements_analysis**: Successfully analyzed task requirements and identified scope"
            in markdown
        )
        assert (
            "✅ **codebase_exploration**: Explored existing codebase and understood architecture patterns"
            in markdown
        )

        # Check acceptance criteria satisfaction for blueprint node
        assert (
            "✅ **solution_architecture**: Designed comprehensive solution with clear architecture"
            in markdown
        )
        assert (
            "✅ **implementation_plan**: Created detailed 5-step implementation plan"
            in markdown
        )

    def test_to_markdown_shows_additional_outputs(
        self, dynamic_state_with_progress, mock_workflow_def
    ):
        """Test that markdown shows additional outputs from completed nodes."""
        markdown = dynamic_state_with_progress.to_markdown(mock_workflow_def)

        # Check additional outputs are shown
        assert "**Additional Outputs:**" in markdown
        assert (
            "**additional_info**: Found relevant patterns in existing code" in markdown
        )
        assert (
            "**risk_assessment**: Low risk implementation with clear rollback plan"
            in markdown
        )

    def test_to_markdown_handles_missing_evidence(self, mock_workflow_def):
        """Test that markdown handles cases where acceptance criteria evidence is missing."""
        from src.accordo_workflow_mcp.models.workflow_state import DynamicWorkflowState

        state = DynamicWorkflowState(
            workflow_name="Test Workflow",
            current_node="blueprint",
            status="RUNNING",
            node_history=["analyze"],
            node_outputs={
                "analyze": {
                    "completed_criteria": {
                        "requirements_analysis": "Analysis completed"
                        # Missing codebase_exploration evidence
                    },
                    "goal_achieved": True,
                }
            },
        )

        markdown = state.to_markdown(mock_workflow_def)

        # Check that missing evidence is indicated
        assert "✅ **requirements_analysis**: Analysis completed" in markdown
        assert (
            "❓ **codebase_exploration**: Understanding of current architecture (no evidence recorded)"
            in markdown
        )

    def test_to_markdown_handles_no_completed_nodes(self, mock_workflow_def):
        """Test that markdown handles cases with no completed nodes."""
        from src.accordo_workflow_mcp.models.workflow_state import DynamicWorkflowState

        state = DynamicWorkflowState(
            workflow_name="Test Workflow",
            current_node="analyze",
            status="RUNNING",
            node_history=[],
            node_outputs={},
        )

        markdown = state.to_markdown(mock_workflow_def)

        # Should not include completed nodes progress section when no nodes completed
        assert "## Completed Nodes Progress" not in markdown

    def test_to_markdown_handles_completed_nodes_without_outputs(
        self, mock_workflow_def
    ):
        """Test that markdown handles completed nodes that have no recorded outputs."""
        from src.accordo_workflow_mcp.models.workflow_state import DynamicWorkflowState

        state = DynamicWorkflowState(
            workflow_name="Test Workflow",
            current_node="blueprint",
            status="RUNNING",
            node_history=["analyze"],
            node_outputs={},  # No outputs recorded
        )

        markdown = state.to_markdown(mock_workflow_def)

        # Should show basic completion status
        assert "## Completed Nodes Progress" in markdown
        assert "✅ **analyze**: Completed (no detailed output recorded)" in markdown
