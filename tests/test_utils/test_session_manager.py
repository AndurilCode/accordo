"""Tests for session manager utilities."""

import json

from src.dev_workflow_mcp.models.workflow_state import (
    WorkflowItem,
    WorkflowPhase,
    WorkflowStatus,
)
from src.dev_workflow_mcp.utils import session_manager


class TestSessionManager:
    """Test session manager basic functionality."""

    def setup_method(self):
        """Clear sessions before each test."""
        session_manager.client_sessions.clear()

    def test_create_session(self):
        """Test creating a new session."""
        session = session_manager.create_session("test-client", "Test task")
        assert session is not None
        assert session.client_id == "test-client"
        assert session.current_item == "Test task"
        assert session.phase == WorkflowPhase.INIT
        assert session.status == WorkflowStatus.READY

    def test_get_session_exists(self):
        """Test getting an existing session."""
        original = session_manager.create_session("test-client", "Test task")
        retrieved = session_manager.get_session("test-client")
        assert retrieved is not None
        assert retrieved.client_id == original.client_id
        assert retrieved.current_item == original.current_item

    def test_get_session_not_exists(self):
        """Test getting a non-existent session."""
        session = session_manager.get_session("non-existent")
        assert session is None

    def test_update_session(self):
        """Test updating session state."""
        session_manager.create_session("test-client", "Test task")
        result = session_manager.update_session(
            "test-client",
            phase=WorkflowPhase.ANALYZE,
            status=WorkflowStatus.RUNNING,
            current_item="Analysis task",
        )
        assert result is True

        session = session_manager.get_session("test-client")
        assert session.phase == WorkflowPhase.ANALYZE
        assert session.status == WorkflowStatus.RUNNING
        assert session.current_item == "Analysis task"

    def test_update_session_not_exists(self):
        """Test updating a non-existent session."""
        result = session_manager.update_session(
            "non-existent", phase=WorkflowPhase.ANALYZE
        )
        assert result is False

    def test_export_session_to_markdown(self):
        """Test exporting session to markdown."""
        session_manager.create_session("test-client", "Test task")
        markdown = session_manager.export_session_to_markdown("test-client")

        assert markdown is not None
        assert "# Workflow State" in markdown
        assert "Test task" in markdown  # Check for the current item instead
        assert "INIT" in markdown
        assert "READY" in markdown

    def test_export_session_to_markdown_not_exists(self):
        """Test exporting non-existent session to markdown."""
        markdown = session_manager.export_session_to_markdown("non-existent")
        assert markdown is None


class TestSessionExportFunctions:
    """Test session export functions (JSON and format dispatch)."""

    def setup_method(self):
        """Clear sessions before each test."""
        session_manager.client_sessions.clear()

    def test_export_session_to_json_basic(self):
        """Test basic JSON export functionality."""
        session_manager.create_session("test-client", "Test task")
        json_str = session_manager.export_session_to_json("test-client")

        assert json_str is not None
        # Should be valid JSON
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_export_session_to_json_structure(self):
        """Test JSON export returns expected structure."""
        session_manager.create_session("test-client", "Test task")
        session_manager.update_session(
            "test-client",
            phase=WorkflowPhase.ANALYZE,
            status=WorkflowStatus.RUNNING,
            current_item="Analysis task",
            plan="Test plan",
            log=["Test log"],
        )

        json_str = session_manager.export_session_to_json("test-client")
        data = json.loads(json_str)

        # Check top-level structure
        assert "metadata" in data
        assert "state" in data
        assert "plan" in data
        assert "items" in data
        assert "log" in data
        assert "archive_log" in data

    def test_export_session_to_json_metadata_fields(self):
        """Test JSON export metadata section."""
        session_manager.create_session("test-client", "Test task")
        json_str = session_manager.export_session_to_json("test-client")
        data = json.loads(json_str)

        metadata = data["metadata"]
        assert "last_updated" in metadata
        assert "client_id" in metadata
        assert "created_at" in metadata
        assert metadata["client_id"] == "test-client"

    def test_export_session_to_json_state_fields(self):
        """Test JSON export state section."""
        session_manager.create_session("test-client", "Test task")
        session_manager.update_session(
            "test-client",
            phase=WorkflowPhase.BLUEPRINT,
            status=WorkflowStatus.NEEDS_PLAN_APPROVAL,
            current_item="Current task",
        )

        json_str = session_manager.export_session_to_json("test-client")
        data = json.loads(json_str)

        state_data = data["state"]
        assert state_data["phase"] == "BLUEPRINT"
        assert state_data["status"] == "NEEDS_PLAN_APPROVAL"
        assert state_data["current_item"] == "Current task"

    def test_export_session_to_json_with_items(self):
        """Test JSON export includes items array."""
        session_manager.create_session("test-client", "Test task")
        session = session_manager.get_session("test-client")
        session.items = [
            WorkflowItem(id=1, description="Task 1", status="pending"),
            WorkflowItem(id=2, description="Task 2", status="completed"),
        ]

        json_str = session_manager.export_session_to_json("test-client")
        data = json.loads(json_str)

        items_data = data["items"]
        assert isinstance(items_data, list)
        assert len(items_data) == 2
        assert items_data[0]["description"] == "Task 1"
        assert items_data[1]["status"] == "completed"

    def test_export_session_to_json_not_exists(self):
        """Test JSON export for non-existent session."""
        json_str = session_manager.export_session_to_json("non-existent")
        assert json_str is None

    def test_export_session_format_dispatch_md(self):
        """Test export_session function dispatches to markdown for MD format."""
        session_manager.create_session("test-client", "Test task")

        result = session_manager.export_session("test-client", "MD")

        assert result is not None
        assert "# Workflow State" in result  # Markdown format
        assert not result.startswith("{")  # Not JSON

    def test_export_session_format_dispatch_json(self):
        """Test export_session function dispatches to JSON for JSON format."""
        session_manager.create_session("test-client", "Test task")

        result = session_manager.export_session("test-client", "JSON")

        assert result is not None
        assert result.startswith("{")  # JSON format
        # Should be valid JSON
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_export_session_format_dispatch_case_insensitive(self):
        """Test export_session format parameter is case-insensitive."""
        session_manager.create_session("test-client", "Test task")

        # Test lowercase
        md_result = session_manager.export_session("test-client", "md")
        json_result = session_manager.export_session("test-client", "json")

        assert md_result is not None
        assert "# Workflow State" in md_result

        assert json_result is not None
        assert json_result.startswith("{")

    def test_export_session_format_dispatch_invalid_format(self):
        """Test export_session with invalid format defaults to markdown."""
        session_manager.create_session("test-client", "Test task")

        result = session_manager.export_session("test-client", "INVALID")

        assert result is not None
        assert "# Workflow State" in result  # Should default to markdown

    def test_export_session_format_dispatch_not_exists(self):
        """Test export_session for non-existent session."""
        md_result = session_manager.export_session("non-existent", "MD")
        json_result = session_manager.export_session("non-existent", "JSON")

        assert md_result is None
        assert json_result is None

    def test_export_session_json_complete_data_integrity(self):
        """Test JSON export maintains complete data integrity."""
        session_manager.create_session("complex-client", "Complex task")
        session = session_manager.get_session("complex-client")

        # Set up complex state
        session.phase = WorkflowPhase.VALIDATE
        session.status = WorkflowStatus.COMPLETED
        session.current_item = "Final validation"
        session.plan = "Complex plan with multiple steps"
        session.items = [
            WorkflowItem(id=1, description="Complex task 1", status="pending"),
            WorkflowItem(id=2, description="Complex task 2", status="completed"),
        ]
        session.add_log_entry("Complex log entry 1")
        session.add_log_entry("Complex log entry 2")
        session.archive_log = ["Historical data"]

        json_str = session_manager.export_session_to_json("complex-client")
        data = json.loads(json_str)

        # Verify all data is present
        assert data["metadata"]["client_id"] == "complex-client"
        assert data["state"]["phase"] == "VALIDATE"
        assert data["state"]["status"] == "COMPLETED"
        assert data["state"]["current_item"] == "Final validation"
        assert data["plan"] == "Complex plan with multiple steps"
        assert len(data["items"]) == 2
        assert data["items"][0]["description"] == "Complex task 1"
        assert any("Complex log entry 1" in entry for entry in data["log"])
        assert any("Complex log entry 2" in entry for entry in data["log"])
        assert data["archive_log"] == ["Historical data"]

    def test_export_session_format_consistency(self):
        """Test that both export formats contain equivalent information."""
        session_manager.create_session("test-client", "Test task")
        session = session_manager.get_session("test-client")

        # Set up some state
        session.phase = WorkflowPhase.CONSTRUCT
        session.status = WorkflowStatus.RUNNING
        session.plan = "Test implementation plan"
        session.items = [WorkflowItem(id=1, description="Test task", status="pending")]
        session.add_log_entry("Test log entry")

        # Export in both formats
        md_result = session_manager.export_session("test-client", "MD")
        json_result = session_manager.export_session("test-client", "JSON")

        # Both should be non-empty
        assert md_result is not None and len(md_result) > 0
        assert json_result is not None and len(json_result) > 0

        # Parse JSON and check key information is present in both
        json_data = json.loads(json_result)

        # Check phase/status info
        assert "CONSTRUCT" in md_result
        assert json_data["state"]["phase"] == "CONSTRUCT"

        assert "RUNNING" in md_result
        assert json_data["state"]["status"] == "RUNNING"

        # Check plan info
        assert "Test implementation plan" in md_result
        assert json_data["plan"] == "Test implementation plan"

        # Check items info
        assert "Test task" in md_result
        assert json_data["items"][0]["description"] == "Test task"
