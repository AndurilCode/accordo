"""Tests for state manager utility functions."""

from src.dev_workflow_mcp.utils import session_manager
from src.dev_workflow_mcp.utils.state_manager import StateManager


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
