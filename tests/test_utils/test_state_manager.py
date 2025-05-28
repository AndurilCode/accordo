"""Tests for state_manager utilities."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.dev_workflow_mcp.utils.state_manager import StateManager


class TestStateManager:
    """Test StateManager class."""

    def test_init_default_file(self):
        """Test StateManager initialization with default file."""
        manager = StateManager()
        assert manager.state_file == Path("workflow_state.md")

    def test_init_custom_file(self):
        """Test StateManager initialization with custom file."""
        manager = StateManager("custom_state.md")
        assert manager.state_file == Path("custom_state.md")

    def test_file_exists_true(self, temp_workflow_file):
        """Test file_exists returns True when file exists."""
        # Create the file
        temp_workflow_file.touch()

        manager = StateManager(str(temp_workflow_file))
        assert manager.file_exists() is True

    def test_file_exists_false(self, temp_workflow_file):
        """Test file_exists returns False when file doesn't exist."""
        manager = StateManager(str(temp_workflow_file))
        assert manager.file_exists() is False

    def test_read_state_existing_file(self, temp_workflow_file):
        """Test reading state from existing file."""
        content = "# Test workflow state\nSome content"
        temp_workflow_file.write_text(content)

        manager = StateManager(str(temp_workflow_file))
        result = manager.read_state()

        assert result == content

    def test_read_state_nonexistent_file(self, temp_workflow_file):
        """Test reading state from non-existent file returns None."""
        manager = StateManager(str(temp_workflow_file))
        result = manager.read_state()

        assert result is None

    @patch("src.dev_workflow_mcp.utils.state_manager.datetime")
    def test_create_initial_state_with_template(self, mock_datetime, temp_dir):
        """Test creating initial state with template file."""
        mock_datetime.now.return_value.strftime.return_value = "2024-12-19"

        # Create a real template file in the expected location
        templates_dir = temp_dir / "src" / "dev_workflow_mcp" / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        template_path = templates_dir / "workflow_state_template.md"
        template_content = "# workflow_state.md\n_Last updated: {timestamp}_\n\nTask: {task_description}"
        template_path.write_text(template_content)

        state_file = temp_dir / "workflow_state.md"

        # Patch the __file__ path to point to our temp directory structure
        with patch(
            "src.dev_workflow_mcp.utils.state_manager.__file__",
            str(temp_dir / "src" / "dev_workflow_mcp" / "utils" / "state_manager.py"),
        ):
            manager = StateManager(str(state_file))
            manager.create_initial_state("Test task")

        # Verify file was created with correct content
        assert state_file.exists()
        content = state_file.read_text()
        assert "2024-12-19" in content
        assert "Test task" in content

    @patch("src.dev_workflow_mcp.utils.state_manager.datetime")
    def test_create_initial_state_fallback(self, mock_datetime, temp_workflow_file):
        """Test creating initial state with fallback when template doesn't exist."""
        mock_datetime.now.return_value.strftime.return_value = "2024-12-19"

        manager = StateManager(str(temp_workflow_file))
        manager.create_initial_state("Test task")

        # Verify file was created
        assert temp_workflow_file.exists()
        content = temp_workflow_file.read_text()
        assert "2024-12-19" in content
        assert "Test task" in content
        assert "## State" in content
        assert "## Plan" in content

    def test_update_state_section_success(self, temp_workflow_file):
        """Test successful state section update."""
        initial_content = """# workflow_state.md
_Last updated: 2024-12-18_

## State
Phase: INIT  
Status: READY  
CurrentItem: Old task  

## Plan
Some plan content
"""
        temp_workflow_file.write_text(initial_content)

        manager = StateManager(str(temp_workflow_file))
        result = manager.update_state_section("ANALYZE", "RUNNING", "New task")

        assert result is True

        updated_content = temp_workflow_file.read_text()
        assert "Phase: ANALYZE" in updated_content
        assert "Status: RUNNING" in updated_content
        assert "CurrentItem: New task" in updated_content
        # Note: The current implementation doesn't update timestamp in update_state_section

    def test_update_state_section_no_current_item(self, temp_workflow_file):
        """Test state section update with None current_item."""
        initial_content = """# workflow_state.md
_Last updated: 2024-12-18_

## State
Phase: INIT  
Status: READY  
CurrentItem: Old task  

## Plan
Some plan content
"""
        temp_workflow_file.write_text(initial_content)

        manager = StateManager(str(temp_workflow_file))
        result = manager.update_state_section("ANALYZE", "RUNNING", None)

        assert result is True

        updated_content = temp_workflow_file.read_text()
        assert "CurrentItem: null" in updated_content

    def test_update_state_section_file_not_found(self, temp_workflow_file):
        """Test state section update when file doesn't exist."""
        manager = StateManager(str(temp_workflow_file))
        result = manager.update_state_section("ANALYZE", "RUNNING", "Task")

        assert result is False

    def test_update_state_section_no_state_section(self, temp_workflow_file):
        """Test state section update when State section is missing."""
        content = """# workflow_state.md
_Last updated: 2024-12-18_

## Plan
Some plan content
"""
        temp_workflow_file.write_text(content)

        manager = StateManager(str(temp_workflow_file))
        result = manager.update_state_section("ANALYZE", "RUNNING", "Task")

        assert result is False

    def test_append_to_log_success(self, temp_workflow_file):
        """Test successful log entry append."""
        initial_content = """# workflow_state.md

## State
Phase: INIT  

## Log
Existing log entry

## ArchiveLog
Archive content
"""
        temp_workflow_file.write_text(initial_content)

        manager = StateManager(str(temp_workflow_file))
        result = manager.append_to_log("New log entry")

        assert result is True

        updated_content = temp_workflow_file.read_text()
        assert "New log entry" in updated_content
        assert "[" in updated_content  # Should have timestamp

    def test_append_to_log_file_not_found(self, temp_workflow_file):
        """Test log append when file doesn't exist."""
        manager = StateManager(str(temp_workflow_file))
        result = manager.append_to_log("New entry")

        assert result is False

    def test_append_to_log_no_log_section(self, temp_workflow_file):
        """Test log append when Log section is missing."""
        content = """# workflow_state.md

## State
Phase: INIT  

## Plan
Some plan
"""
        temp_workflow_file.write_text(content)

        manager = StateManager(str(temp_workflow_file))
        result = manager.append_to_log("New entry")

        assert result is False

    def test_get_fallback_template(self, temp_workflow_file):
        """Test fallback template generation."""
        manager = StateManager(str(temp_workflow_file))
        template = manager._get_fallback_template("Test task")

        assert "# workflow_state.md" in template
        assert "Test task" in template
        assert "## State" in template
        assert "## Plan" in template
        assert "## Items" in template
        assert "## Log" in template
        assert "## ArchiveLog" in template

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_read_state_permission_error(self, mock_file, temp_workflow_file):
        """Test read_state raises permission errors."""
        temp_workflow_file.touch()  # Create the file

        manager = StateManager(str(temp_workflow_file))
        # The current implementation doesn't handle permission errors gracefully
        # It will raise the exception
        with pytest.raises(PermissionError):
            manager.read_state()

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_update_state_section_permission_error(self, mock_file, temp_workflow_file):
        """Test update_state_section raises permission errors."""
        temp_workflow_file.touch()  # Create the file

        manager = StateManager(str(temp_workflow_file))
        # The current implementation doesn't handle permission errors gracefully
        # It will raise the exception
        with pytest.raises(PermissionError):
            manager.update_state_section("ANALYZE", "RUNNING", "Task")
