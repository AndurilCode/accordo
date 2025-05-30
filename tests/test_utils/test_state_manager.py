"""Tests for state manager utility functions."""

import os
from unittest.mock import patch

from src.dev_workflow_mcp.utils import session_manager
from src.dev_workflow_mcp.utils.state_manager import (
    StateManager,
    get_file_operation_instructions,
)


class TestStateManager:
    """Test StateManager class functionality."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_init_default(self):
        """Test StateManager initialization with default parameters."""
        manager = StateManager()
        assert manager.client_id == "default"

    def test_init_custom_client(self):
        """Test StateManager initialization with custom client."""
        manager = StateManager("ignored_file.md", "test-client")
        assert manager.client_id == "test-client"

    def test_create_initial_state_creates_session(self):
        """Test creating initial state creates session."""
        manager = StateManager(client_id="test-init-client")
        manager.create_initial_state("Test initialization task")

        # Should create session
        result = manager.read_state()
        assert result is not None
        assert "Test initialization task" in result

    def test_read_state_session_based(self):
        """Test reading state returns session markdown."""
        manager = StateManager(client_id="test-read-client")
        result = manager.read_state()

        # Should return markdown from session
        assert result is not None
        assert "# Workflow State" in result
        assert "## State" in result

    def test_read_state_creates_session(self):
        """Test reading state creates session if it doesn't exist."""
        manager = StateManager(client_id="test-create-client")
        result = manager.read_state()

        # Should create session and return markdown
        assert result is not None
        assert "Default task" in result

    def test_update_state_section_success(self):
        """Test successful state section update via session."""
        manager = StateManager(client_id="test-update-client")
        # First create a session
        manager.create_initial_state("Update test task")

        result = manager.update_state_section("ANALYZE", "RUNNING", "New task")
        assert result is True

        # Verify update in session
        updated_content = manager.read_state()
        assert "Phase: ANALYZE" in updated_content
        assert "Status: RUNNING" in updated_content
        assert "CurrentItem: New task" in updated_content

    def test_update_state_section_no_current_item(self):
        """Test state section update with None current_item."""
        manager = StateManager(client_id="test-null-client")
        manager.create_initial_state("Null test task")

        result = manager.update_state_section("ANALYZE", "RUNNING", None)
        assert result is True

        updated_content = manager.read_state()
        assert "CurrentItem: null" in updated_content

    def test_update_state_section_creates_session(self):
        """Test state section update creates session if needed."""
        manager = StateManager(client_id="test-auto-create-client")
        result = manager.update_state_section("ANALYZE", "RUNNING", "Task")

        # Should succeed and create session
        assert result is True

    def test_update_state_section_invalid_phase(self):
        """Test state section update with invalid phase."""
        manager = StateManager(client_id="test-invalid-client")
        result = manager.update_state_section("INVALID", "RUNNING", "Task")

        # Should fail with invalid phase
        assert result is False

    def test_update_state_section_invalid_status(self):
        """Test state section update with invalid status."""
        manager = StateManager(client_id="test-invalid-status-client")
        result = manager.update_state_section("ANALYZE", "INVALID", "Task")

        # Should fail with invalid status
        assert result is False

    def test_append_to_log_success(self):
        """Test successful log entry append via session."""
        manager = StateManager(client_id="test-log-client")
        manager.create_initial_state("Log test task")

        result = manager.append_to_log("New log entry")
        assert result is True

        updated_content = manager.read_state()
        assert "New log entry" in updated_content
        assert "[" in updated_content  # Should have timestamp

    def test_append_to_log_creates_session(self):
        """Test log append creates session if needed."""
        manager = StateManager(client_id="test-log-create-client")
        result = manager.append_to_log("New entry")

        # Should succeed and create session
        assert result is True

    def test_client_id_operations(self):
        """Test client ID getter and setter."""
        manager = StateManager(client_id="original-client")
        assert manager.get_client_id() == "original-client"

        manager.set_client_id("new-client")
        assert manager.get_client_id() == "new-client"

    def test_session_isolation(self):
        """Test that different clients have isolated sessions."""
        manager1 = StateManager(client_id="client-1")
        manager2 = StateManager(client_id="client-2")

        # Create different tasks
        manager1.create_initial_state("Task for client 1")
        manager2.create_initial_state("Task for client 2")

        # Verify isolation
        content1 = manager1.read_state()
        content2 = manager2.read_state()

        assert "Task for client 1" in content1
        assert "Task for client 1" not in content2
        assert "Task for client 2" in content2
        assert "Task for client 2" not in content1

    def test_multiple_log_entries(self):
        """Test multiple log entries are properly handled."""
        manager = StateManager(client_id="test-multi-log-client")
        manager.create_initial_state("Multi log test")

        # Add multiple log entries
        manager.append_to_log("First entry")
        manager.append_to_log("Second entry")
        manager.append_to_log("Third entry")

        content = manager.read_state()
        assert "First entry" in content
        assert "Second entry" in content
        assert "Third entry" in content


class TestStateManagerCompatibility:
    """Test StateManager backward compatibility features."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_legacy_create_state_manager(self):
        """Test legacy create_state_manager function."""
        from src.dev_workflow_mcp.utils.state_manager import create_state_manager

        manager = create_state_manager("ignored_file.md", "legacy-client")
        assert manager.client_id == "legacy-client"
        assert isinstance(manager, StateManager)

    def test_constructor_backward_compatibility(self):
        """Test that old constructor signature still works."""
        # Old way: StateManager(state_file, client_id)
        manager = StateManager("some_file.md", "compat-client")
        assert manager.client_id == "compat-client"

        # New way: StateManager(client_id=client_id)
        manager2 = StateManager(client_id="new-client")
        assert manager2.client_id == "new-client"


class TestGetFileOperationInstructions:
    """Test get_file_operation_instructions function with format support."""

    def setup_method(self):
        """Clear sessions before each test."""
        session_manager.client_sessions.clear()

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE": "false"})
    def test_get_file_operation_instructions_disabled(self):
        """Test get_file_operation_instructions when local state file is disabled."""
        result = get_file_operation_instructions()
        assert result == ""

    @patch.dict(
        os.environ,
        {"WORKFLOW_LOCAL_STATE_FILE": "true", "WORKFLOW_LOCAL_STATE_FILE_FORMAT": "MD"},
    )
    def test_get_file_operation_instructions_md_format(self):
        """Test get_file_operation_instructions generates MD filename and content."""
        # Create a session to export
        session_manager.create_session("default", "Test task")

        result = get_file_operation_instructions()

        assert result != ""
        assert "workflow_state.md" in result
        assert "# Workflow State" in result
        assert "Test task" in result

    @patch.dict(
        os.environ,
        {
            "WORKFLOW_LOCAL_STATE_FILE": "true",
            "WORKFLOW_LOCAL_STATE_FILE_FORMAT": "JSON",
        },
    )
    def test_get_file_operation_instructions_json_format(self):
        """Test get_file_operation_instructions generates JSON filename and content."""
        # Create a session to export
        session_manager.create_session("default", "Test task")

        result = get_file_operation_instructions()

        assert result != ""
        assert "workflow_state.json" in result
        assert (
            '"metadata"' in result or '"state"' in result
        )  # Should contain JSON structure

    @patch.dict(
        os.environ,
        {"WORKFLOW_LOCAL_STATE_FILE": "true", "WORKFLOW_LOCAL_STATE_FILE_FORMAT": "md"},
    )
    def test_get_file_operation_instructions_case_insensitive_md(self):
        """Test get_file_operation_instructions handles case-insensitive MD format."""
        session_manager.create_session("default", "Test task")

        result = get_file_operation_instructions()

        assert result != ""
        assert "workflow_state.md" in result
        assert "# Workflow State" in result

    @patch.dict(
        os.environ,
        {
            "WORKFLOW_LOCAL_STATE_FILE": "true",
            "WORKFLOW_LOCAL_STATE_FILE_FORMAT": "json",
        },
    )
    def test_get_file_operation_instructions_case_insensitive_json(self):
        """Test get_file_operation_instructions handles case-insensitive JSON format."""
        session_manager.create_session("default", "Test task")

        result = get_file_operation_instructions()

        assert result != ""
        assert "workflow_state.json" in result

    @patch.dict(
        os.environ,
        {
            "WORKFLOW_LOCAL_STATE_FILE": "true",
            "WORKFLOW_LOCAL_STATE_FILE_FORMAT": "INVALID",
        },
    )
    def test_get_file_operation_instructions_invalid_format_defaults_to_md(self):
        """Test get_file_operation_instructions defaults to MD for invalid format."""
        session_manager.create_session("default", "Test task")

        result = get_file_operation_instructions()

        assert result != ""
        assert "workflow_state.md" in result
        assert "# Workflow State" in result

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE": "true"})
    def test_get_file_operation_instructions_no_format_defaults_to_md(self):
        """Test get_file_operation_instructions defaults to MD when no format specified."""
        session_manager.create_session("default", "Test task")

        result = get_file_operation_instructions()

        assert result != ""
        assert "workflow_state.md" in result
        assert "# Workflow State" in result

    @patch.dict(
        os.environ,
        {"WORKFLOW_LOCAL_STATE_FILE": "true", "WORKFLOW_LOCAL_STATE_FILE_FORMAT": "MD"},
    )
    def test_get_file_operation_instructions_no_session(self):
        """Test get_file_operation_instructions when no session exists."""
        # Don't create any session
        result = get_file_operation_instructions()

        # Should still return instructions but may be empty content or handle gracefully
        # Exact behavior depends on implementation - should not crash
        assert isinstance(result, str)

    @patch.dict(
        os.environ,
        {
            "WORKFLOW_LOCAL_STATE_FILE": "true",
            "WORKFLOW_LOCAL_STATE_FILE_FORMAT": "JSON",
        },
    )
    def test_get_file_operation_instructions_json_structure_validation(self):
        """Test get_file_operation_instructions JSON contains valid structure."""
        session_manager.create_session("default", "Test task")
        session = session_manager.get_session("default")
        session.plan = "Test plan"
        session.add_log_entry("Test log entry")

        result = get_file_operation_instructions()

        assert result != ""
        assert "workflow_state.json" in result

        # Should contain JSON content with expected structure
        # Look for key JSON structure indicators
        json_indicators = ['"metadata"', '"state"', '"plan"', '"items"', '"log"']
        found_indicators = sum(
            1 for indicator in json_indicators if indicator in result
        )
        assert (
            found_indicators >= 3
        )  # Should find at least 3 of the 5 main JSON structure elements

    @patch.dict(
        os.environ,
        {"WORKFLOW_LOCAL_STATE_FILE": "true", "WORKFLOW_LOCAL_STATE_FILE_FORMAT": "MD"},
    )
    def test_get_file_operation_instructions_md_structure_validation(self):
        """Test get_file_operation_instructions MD contains expected markdown structure."""
        session_manager.create_session("default", "Test task")
        session = session_manager.get_session("default")
        session.plan = "Test plan"
        session.add_log_entry("Test log entry")

        result = get_file_operation_instructions()

        assert result != ""
        assert "workflow_state.md" in result

        # Should contain markdown content with expected structure
        md_indicators = ["# Workflow State", "## State", "Phase:", "Status:"]
        found_indicators = sum(1 for indicator in md_indicators if indicator in result)
        assert (
            found_indicators >= 3
        )  # Should find at least 3 of the 4 main markdown structure elements

    @patch.dict(
        os.environ,
        {
            "WORKFLOW_LOCAL_STATE_FILE": "true",
            "WORKFLOW_LOCAL_STATE_FILE_FORMAT": "JSON",
        },
    )
    def test_get_file_operation_instructions_format_consistency(self):
        """Test that file operation instructions are consistent for same session in JSON format."""
        session_manager.create_session("default", "Consistent task")

        result1 = get_file_operation_instructions()
        result2 = get_file_operation_instructions()

        # Results should be identical for same session state
        assert result1 == result2
        assert "workflow_state.json" in result1
        assert "workflow_state.json" in result2

    @patch.dict(
        os.environ,
        {"WORKFLOW_LOCAL_STATE_FILE": "true", "WORKFLOW_LOCAL_STATE_FILE_FORMAT": "MD"},
    )
    def test_get_file_operation_instructions_format_consistency_md(self):
        """Test that file operation instructions are consistent for same session in MD format."""
        session_manager.create_session("default", "Consistent task")

        result1 = get_file_operation_instructions()
        result2 = get_file_operation_instructions()

        # Results should be identical for same session state
        assert result1 == result2
        assert "workflow_state.md" in result1
        assert "workflow_state.md" in result2
