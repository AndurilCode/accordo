"""Tests for state manager utility functions."""

import tempfile
from pathlib import Path

import pytest

from src.dev_workflow_mcp.utils import session_manager
from src.dev_workflow_mcp.utils.state_manager import StateManager


class TestStateManager:
    """Test StateManager class functionality."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_init_default_file(self):
        """Test StateManager initialization with default file."""
        manager = StateManager()
        assert str(manager.state_file) == "workflow_state.md"
        assert manager.client_id == "default"

    def test_init_custom_file(self):
        """Test StateManager initialization with custom file and client."""
        manager = StateManager("custom.md", "test-client")
        assert str(manager.state_file) == "custom.md"
        assert manager.client_id == "test-client"

    def test_file_exists_true(self, temp_workflow_file):
        """Test file_exists returns True when session can be created."""
        manager = StateManager(str(temp_workflow_file), "test-client")
        # With session backend, file_exists always returns True if session can be created
        assert manager.file_exists() is True

    def test_file_exists_false(self, temp_workflow_file):
        """Test file_exists behavior with session backend."""
        manager = StateManager(str(temp_workflow_file), "test-client-2")
        # With session backend, file_exists always returns True for any valid client_id
        assert manager.file_exists() is True

    def test_read_state_session_based(self, temp_workflow_file):
        """Test reading state returns session markdown."""
        manager = StateManager(str(temp_workflow_file), "test-read-client")
        result = manager.read_state()

        # Should return markdown from session, not file content
        assert result is not None
        assert "# workflow_state.md" in result
        assert "## State" in result

    def test_read_state_creates_session(self, temp_workflow_file):
        """Test reading state creates session if it doesn't exist."""
        manager = StateManager(str(temp_workflow_file), "test-create-client")
        result = manager.read_state()

        # Should create session and return markdown
        assert result is not None
        assert "test-create-client" in result or "Default task" in result

    def test_create_initial_state_creates_session(self, temp_workflow_file):
        """Test creating initial state creates session."""
        manager = StateManager(str(temp_workflow_file), "test-init-client")
        manager.create_initial_state("Test initialization task")

        # Should create session
        result = manager.read_state()
        assert result is not None
        assert "Test initialization task" in result

    def test_update_state_section_success(self, temp_workflow_file):
        """Test successful state section update via session."""
        manager = StateManager(str(temp_workflow_file), "test-update-client")
        # First create a session
        manager.create_initial_state("Update test task")
        
        result = manager.update_state_section("ANALYZE", "RUNNING", "New task")
        assert result is True

        # Verify update in session
        updated_content = manager.read_state()
        assert "Phase: ANALYZE" in updated_content
        assert "Status: RUNNING" in updated_content
        assert "CurrentItem: New task" in updated_content

    def test_update_state_section_no_current_item(self, temp_workflow_file):
        """Test state section update with None current_item."""
        manager = StateManager(str(temp_workflow_file), "test-null-client")
        manager.create_initial_state("Null test task")
        
        result = manager.update_state_section("ANALYZE", "RUNNING", None)
        assert result is True

        updated_content = manager.read_state()
        assert "CurrentItem: null" in updated_content

    def test_update_state_section_creates_session(self, temp_workflow_file):
        """Test state section update creates session if needed."""
        manager = StateManager(str(temp_workflow_file), "test-auto-create-client")
        result = manager.update_state_section("ANALYZE", "RUNNING", "Task")

        # Should succeed and create session
        assert result is True

    def test_append_to_log_success(self, temp_workflow_file):
        """Test successful log entry append via session."""
        manager = StateManager(str(temp_workflow_file), "test-log-client")
        manager.create_initial_state("Log test task")
        
        result = manager.append_to_log("New log entry")
        assert result is True

        updated_content = manager.read_state()
        assert "New log entry" in updated_content
        assert "[" in updated_content  # Should have timestamp

    def test_append_to_log_creates_session(self, temp_workflow_file):
        """Test log append creates session if needed."""
        manager = StateManager(str(temp_workflow_file), "test-log-create-client")
        result = manager.append_to_log("New entry")

        # Should succeed and create session
        assert result is True

    def test_get_fallback_template(self, temp_workflow_file):
        """Test fallback template generation via session."""
        manager = StateManager(str(temp_workflow_file), "test-template-client")
        template = manager._get_fallback_template("Test task")

        assert "# workflow_state.md" in template
        assert "Test task" in template
        assert "## State" in template
        assert "## Plan" in template
        assert "## Items" in template
        assert "## Log" in template
        assert "## ArchiveLog" in template

    def test_migrate_from_file(self, temp_workflow_file):
        """Test migrating from file to session."""
        # Create a file with content
        file_content = """# workflow_state.md
_Last updated: 2024-12-19_

## State
Phase: INIT
Status: READY
CurrentItem: File task

## Plan
Some plan

## Items
| id | description | status |
|----|-------------|--------|
| 1 | File task | pending |

## Log
File log entry

## ArchiveLog
Archive content
"""
        temp_workflow_file.write_text(file_content)
        
        manager = StateManager(str(temp_workflow_file), "test-migrate-client")
        result = manager.migrate_from_file()
        
        # Should succeed in migration
        assert result is True
        
        # Verify session has file content
        session_content = manager.read_state()
        assert "File task" in session_content

    def test_export_to_file(self, temp_workflow_file):
        """Test exporting session to file."""
        manager = StateManager(str(temp_workflow_file), "test-export-client")
        manager.create_initial_state("Export test task")
        
        result = manager.export_to_file()
        assert result is True
        
        # Verify file was created with session content
        assert temp_workflow_file.exists()
        file_content = temp_workflow_file.read_text()
        assert "Export test task" in file_content

    def test_client_id_operations(self, temp_workflow_file):
        """Test client ID getter and setter."""
        manager = StateManager(str(temp_workflow_file), "original-client")
        assert manager.get_client_id() == "original-client"
        
        manager.set_client_id("new-client")
        assert manager.get_client_id() == "new-client"

    @pytest.fixture
    def temp_workflow_file(self):
        """Create temporary workflow file for testing."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir_path:
            yield Path(temp_dir_path)
