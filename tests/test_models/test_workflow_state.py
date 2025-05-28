"""Tests for workflow_state models."""

from datetime import datetime
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.dev_workflow_mcp.models.workflow_state import (
    WorkflowItem,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)


class TestWorkflowPhase:
    """Test WorkflowPhase enum."""

    def test_enum_values(self):
        """Test that all expected enum values exist."""
        assert WorkflowPhase.INIT == "INIT"
        assert WorkflowPhase.ANALYZE == "ANALYZE"
        assert WorkflowPhase.BLUEPRINT == "BLUEPRINT"
        assert WorkflowPhase.CONSTRUCT == "CONSTRUCT"
        assert WorkflowPhase.VALIDATE == "VALIDATE"

    def test_string_conversion(self):
        """Test that enum values convert to strings correctly."""
        assert str(WorkflowPhase.INIT) == "WorkflowPhase.INIT"
        assert str(WorkflowPhase.ANALYZE) == "WorkflowPhase.ANALYZE"
        # Test the actual value access
        assert WorkflowPhase.INIT.value == "INIT"
        assert WorkflowPhase.ANALYZE.value == "ANALYZE"


class TestWorkflowStatus:
    """Test WorkflowStatus enum."""

    def test_enum_values(self):
        """Test that all expected enum values exist."""
        assert WorkflowStatus.READY == "READY"
        assert WorkflowStatus.RUNNING == "RUNNING"
        assert WorkflowStatus.NEEDS_PLAN_APPROVAL == "NEEDS_PLAN_APPROVAL"
        assert WorkflowStatus.COMPLETED == "COMPLETED"
        assert WorkflowStatus.ERROR == "ERROR"

    def test_string_conversion(self):
        """Test that enum values convert to strings correctly."""
        assert str(WorkflowStatus.READY) == "WorkflowStatus.READY"
        assert str(WorkflowStatus.ERROR) == "WorkflowStatus.ERROR"
        # Test the actual value access
        assert WorkflowStatus.READY.value == "READY"
        assert WorkflowStatus.ERROR.value == "ERROR"


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
        state = WorkflowState(phase=WorkflowPhase.INIT, status=WorkflowStatus.READY)
        assert state.phase == WorkflowPhase.INIT
        assert state.status == WorkflowStatus.READY
        assert state.current_item is None
        assert state.plan == ""
        assert state.items == []
        assert state.log == ""
        assert state.archive_log == ""
        assert isinstance(state.last_updated, datetime)

    def test_creation_with_all_fields(self):
        """Test creating WorkflowState with all fields."""
        items = [WorkflowItem(id=1, description="Task 1")]
        state = WorkflowState(
            phase=WorkflowPhase.BLUEPRINT,
            status=WorkflowStatus.RUNNING,
            current_item="Current task",
            plan="Test plan",
            items=items,
            log="Test log",
            archive_log="Archive log",
        )
        assert state.phase == WorkflowPhase.BLUEPRINT
        assert state.status == WorkflowStatus.RUNNING
        assert state.current_item == "Current task"
        assert state.plan == "Test plan"
        assert len(state.items) == 1
        assert state.log == "Test log"
        assert state.archive_log == "Archive log"

    @patch("src.dev_workflow_mcp.models.workflow_state.datetime")
    def test_add_log_entry(self, mock_datetime):
        """Test adding log entry with timestamp."""
        # Mock datetime.now() to return a fixed time
        mock_datetime.now.return_value.strftime.return_value = "12:34:56"

        state = WorkflowState(phase=WorkflowPhase.INIT, status=WorkflowStatus.READY)

        state.add_log_entry("Test entry")

        assert state.log == "\n[12:34:56] Test entry"
        mock_datetime.now.assert_called_once()

    @patch("src.dev_workflow_mcp.models.workflow_state.datetime")
    def test_add_multiple_log_entries(self, mock_datetime):
        """Test adding multiple log entries."""
        mock_datetime.now.return_value.strftime.side_effect = ["12:34:56", "12:35:00"]

        state = WorkflowState(phase=WorkflowPhase.INIT, status=WorkflowStatus.READY)

        state.add_log_entry("First entry")
        state.add_log_entry("Second entry")

        expected_log = "\n[12:34:56] First entry\n[12:35:00] Second entry"
        assert state.log == expected_log

    def test_rotate_log_when_over_5000_chars(self):
        """Test that log rotates when it exceeds 5000 characters."""
        state = WorkflowState(phase=WorkflowPhase.INIT, status=WorkflowStatus.READY)

        # Create a log entry that's over 5000 characters
        long_entry = "x" * 5001
        state.log = long_entry

        state.rotate_log()

        assert state.archive_log == long_entry
        assert state.log == ""

    def test_rotate_log_with_existing_archive(self):
        """Test log rotation when archive already has content."""
        state = WorkflowState(phase=WorkflowPhase.INIT, status=WorkflowStatus.READY)

        state.archive_log = "Existing archive"
        state.log = "Current log"

        state.rotate_log()

        expected_archive = "Existing archive\n\n--- LOG ROTATION ---\n\nCurrent log"
        assert state.archive_log == expected_archive
        assert state.log == ""

    @patch("src.dev_workflow_mcp.models.workflow_state.datetime")
    def test_add_log_entry_triggers_rotation(self, mock_datetime):
        """Test that adding log entry triggers rotation when over 5000 chars."""
        mock_datetime.now.return_value.strftime.return_value = "12:34:56"

        state = WorkflowState(phase=WorkflowPhase.INIT, status=WorkflowStatus.READY)

        # Set log to be just under 5000 chars
        state.log = "x" * 4990

        # Add entry that pushes it over 5000
        state.add_log_entry("This will trigger rotation")

        # Log should be rotated (moved to archive) and log should be cleared
        assert "x" * 4990 in state.archive_log
        assert "\n[12:34:56] This will trigger rotation" in state.archive_log
        assert state.log == ""

    def test_get_next_pending_item_with_pending_items(self):
        """Test getting next pending item when pending items exist."""
        items = [
            WorkflowItem(id=1, description="Task 1", status="completed"),
            WorkflowItem(id=2, description="Task 2", status="pending"),
            WorkflowItem(id=3, description="Task 3", status="pending"),
        ]
        state = WorkflowState(
            phase=WorkflowPhase.INIT, status=WorkflowStatus.READY, items=items
        )

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
        state = WorkflowState(
            phase=WorkflowPhase.INIT, status=WorkflowStatus.READY, items=items
        )

        next_item = state.get_next_pending_item()

        assert next_item is None

    def test_get_next_pending_item_empty_items(self):
        """Test getting next pending item when items list is empty."""
        state = WorkflowState(
            phase=WorkflowPhase.INIT, status=WorkflowStatus.READY, items=[]
        )

        next_item = state.get_next_pending_item()

        assert next_item is None

    def test_mark_item_completed_success(self):
        """Test marking an existing item as completed."""
        items = [
            WorkflowItem(id=1, description="Task 1", status="pending"),
            WorkflowItem(id=2, description="Task 2", status="pending"),
        ]
        state = WorkflowState(
            phase=WorkflowPhase.INIT, status=WorkflowStatus.READY, items=items
        )

        result = state.mark_item_completed(1)

        assert result is True
        assert state.items[0].status == "completed"
        assert state.items[1].status == "pending"  # Unchanged

    def test_mark_item_completed_item_not_found(self):
        """Test marking a non-existent item as completed."""
        items = [
            WorkflowItem(id=1, description="Task 1", status="pending"),
        ]
        state = WorkflowState(
            phase=WorkflowPhase.INIT, status=WorkflowStatus.READY, items=items
        )

        result = state.mark_item_completed(999)

        assert result is False
        assert state.items[0].status == "pending"  # Unchanged

    def test_mark_item_completed_empty_items(self):
        """Test marking item as completed when items list is empty."""
        state = WorkflowState(
            phase=WorkflowPhase.INIT, status=WorkflowStatus.READY, items=[]
        )

        result = state.mark_item_completed(1)

        assert result is False

    def test_validation_error_missing_phase(self):
        """Test that missing phase raises validation error."""
        with pytest.raises(ValidationError):
            WorkflowState(status=WorkflowStatus.READY)

    def test_validation_error_missing_status(self):
        """Test that missing status raises validation error."""
        with pytest.raises(ValidationError):
            WorkflowState(phase=WorkflowPhase.INIT)

    def test_serialization(self):
        """Test that WorkflowState can be serialized."""
        items = [WorkflowItem(id=1, description="Task 1")]
        state = WorkflowState(
            phase=WorkflowPhase.BLUEPRINT,
            status=WorkflowStatus.RUNNING,
            current_item="Current task",
            plan="Test plan",
            items=items,
            log="Test log",
            archive_log="Archive log",
        )

        data = state.model_dump()

        assert data["phase"] == "BLUEPRINT"
        assert data["status"] == "RUNNING"
        assert data["current_item"] == "Current task"
        assert data["plan"] == "Test plan"
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == 1
        assert data["log"] == "Test log"
        assert data["archive_log"] == "Archive log"
        assert "last_updated" in data
