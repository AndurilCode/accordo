"""Tests for path utilities functionality."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.accordo_mcp.utils.path_utils import (
    get_project_config_path,
    get_workflow_dir,
    get_workflow_state_path,
    migrate_config_file,
    migrate_workflow_state_files,
)


class TestPathUtils:
    """Test path utilities functions."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_get_workflow_dir_creates_directory(self, temp_dir):
        """Test get_workflow_dir creates .accordo directory."""
        workflow_dir = get_workflow_dir(temp_dir)

        assert workflow_dir.exists()
        assert workflow_dir.is_dir()
        assert workflow_dir.name == ".accordo"
        assert workflow_dir.parent == temp_dir

    def test_get_workflow_dir_existing_directory(self, temp_dir):
        """Test get_workflow_dir with existing .accordo directory."""
        # Create the directory first
        existing_dir = temp_dir / ".accordo"
        existing_dir.mkdir()

        workflow_dir = get_workflow_dir(temp_dir)

        assert workflow_dir == existing_dir
        assert workflow_dir.exists()

    def test_get_workflow_dir_default_path(self):
        """Test get_workflow_dir with default path."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            result = get_workflow_dir()

            mock_mkdir.assert_called_once_with(exist_ok=True)
            assert result.name == ".accordo"

    def test_get_workflow_dir_creation_fails(self, temp_dir):
        """Test get_workflow_dir when directory creation fails."""
        # Make the temp_dir read-only to cause mkdir to fail
        temp_dir.chmod(0o444)

        with patch("builtins.print") as mock_print:
            workflow_dir = get_workflow_dir(temp_dir)

            # Should fallback to base path
            assert workflow_dir == temp_dir
            # Check that warning messages were printed (exact message may vary by system)
            assert mock_print.call_count == 2
            assert (
                "Warning: Could not create .accordo directory:"
                in mock_print.call_args_list[0][0][0]
            )
            assert (
                "Falling back to current directory for workflow files"
                in mock_print.call_args_list[1][0][0]
            )

        # Restore permissions for cleanup
        temp_dir.chmod(0o755)

    def test_get_project_config_path(self, temp_dir):
        """Test get_project_config_path returns correct path."""
        config_path = get_project_config_path(temp_dir)

        expected_path = temp_dir / ".accordo" / "project_config.md"
        assert config_path == expected_path
        assert config_path.parent.exists()  # Directory should be created

    def test_get_project_config_path_default(self):
        """Test get_project_config_path with default base path."""
        with patch("src.accordo_mcp.utils.path_utils.get_workflow_dir") as mock_get_dir:
            # Create a mock that supports the / operator
            mock_workflow_dir = Mock()
            mock_workflow_dir.__truediv__ = Mock(
                return_value=Path("mocked/project_config.md")
            )
            mock_get_dir.return_value = mock_workflow_dir

            get_project_config_path()

            mock_get_dir.assert_called_once_with(".")
            mock_workflow_dir.__truediv__.assert_called_once_with("project_config.md")

    def test_get_workflow_state_path_md_format(self, temp_dir):
        """Test get_workflow_state_path with markdown format."""
        state_path = get_workflow_state_path("md", temp_dir)

        expected_path = temp_dir / ".accordo" / "workflow_state.md"
        assert state_path == expected_path
        assert state_path.parent.exists()

    def test_get_workflow_state_path_json_format(self, temp_dir):
        """Test get_workflow_state_path with JSON format."""
        state_path = get_workflow_state_path("json", temp_dir)

        expected_path = temp_dir / ".accordo" / "workflow_state.json"
        assert state_path == expected_path

    def test_get_workflow_state_path_default_format(self, temp_dir):
        """Test get_workflow_state_path with default format."""
        state_path = get_workflow_state_path(base_path=temp_dir)

        expected_path = temp_dir / ".accordo" / "workflow_state.md"
        assert state_path == expected_path

    def test_get_workflow_state_path_case_insensitive(self, temp_dir):
        """Test get_workflow_state_path is case insensitive for format."""
        state_path_upper = get_workflow_state_path("JSON", temp_dir)
        state_path_lower = get_workflow_state_path("json", temp_dir)

        assert state_path_upper == state_path_lower
        assert state_path_upper.suffix == ".json"

    def test_get_workflow_state_path_invalid_format(self, temp_dir):
        """Test get_workflow_state_path with invalid format defaults to md."""
        state_path = get_workflow_state_path("xml", temp_dir)

        expected_path = temp_dir / ".accordo" / "workflow_state.md"
        assert state_path == expected_path

    def test_migrate_config_file_no_existing_file(self, temp_dir):
        """Test migrate_config_file when old file doesn't exist."""
        old_path = temp_dir / "nonexistent_config.md"

        result = migrate_config_file(old_path, temp_dir)

        assert result is True

    def test_migrate_config_file_success(self, temp_dir):
        """Test migrate_config_file successful migration."""
        # Create old config file
        old_path = temp_dir / "project_config.md"
        old_path.write_text("# Old Config\nContent here")

        with patch("builtins.print") as mock_print:
            result = migrate_config_file(old_path, temp_dir)

        assert result is True
        assert not old_path.exists()

        new_path = temp_dir / ".accordo" / "project_config.md"
        assert new_path.exists()
        assert new_path.read_text() == "# Old Config\nContent here"

        mock_print.assert_called_once_with(f"Migrated {old_path} to {new_path}")

    def test_migrate_config_file_with_existing_target(self, temp_dir):
        """Test migrate_config_file when target file already exists."""
        # Create old config file
        old_path = temp_dir / "project_config.md"
        old_path.write_text("# Old Config")

        # Create existing target file
        workflow_dir = temp_dir / ".accordo"
        workflow_dir.mkdir()
        existing_target = workflow_dir / "project_config.md"
        existing_target.write_text("# Existing Config")

        with patch("builtins.print") as mock_print:
            result = migrate_config_file(old_path, temp_dir)

        assert result is True
        assert not old_path.exists()

        # Check backup was created
        backup_path = workflow_dir / "project_config.md.backup"
        assert backup_path.exists()
        assert backup_path.read_text() == "# Existing Config"

        # Check new file has old content
        assert existing_target.read_text() == "# Old Config"

        mock_print.assert_any_call(
            f"Backed up existing {existing_target} to {backup_path}"
        )
        mock_print.assert_any_call(f"Migrated {old_path} to {existing_target}")

    def test_migrate_config_file_failure(self, temp_dir):
        """Test migrate_config_file when migration fails."""
        # Create old config file
        old_path = temp_dir / "project_config.md"
        old_path.write_text("# Old Config")

        # Make workflow directory read-only to cause failure
        workflow_dir = temp_dir / ".accordo"
        workflow_dir.mkdir()
        workflow_dir.chmod(0o444)

        with patch("builtins.print") as mock_print:
            result = migrate_config_file(old_path, temp_dir)

        assert result is False
        assert old_path.exists()  # File should still exist

        mock_print.assert_called_once()
        assert "Warning: Could not migrate" in mock_print.call_args[0][0]

        # Restore permissions for cleanup
        workflow_dir.chmod(0o755)

    def test_migrate_workflow_state_files_no_files(self, temp_dir):
        """Test migrate_workflow_state_files when no files exist."""
        result = migrate_workflow_state_files(temp_dir)

        assert result is True

    def test_migrate_workflow_state_files_md_only(self, temp_dir):
        """Test migrate_workflow_state_files with only MD file."""
        # Create old MD file
        old_md = temp_dir / "workflow_state.md"
        old_md.write_text("# Workflow State MD")

        with patch("builtins.print") as mock_print:
            result = migrate_workflow_state_files(temp_dir)

        assert result is True
        assert not old_md.exists()

        new_md = temp_dir / ".accordo" / "workflow_state.md"
        assert new_md.exists()
        assert new_md.read_text() == "# Workflow State MD"

        mock_print.assert_called_once_with(f"Migrated {old_md} to {new_md}")

    def test_migrate_workflow_state_files_json_only(self, temp_dir):
        """Test migrate_workflow_state_files with only JSON file."""
        # Create old JSON file
        old_json = temp_dir / "workflow_state.json"
        old_json.write_text('{"state": "data"}')

        with patch("builtins.print") as mock_print:
            result = migrate_workflow_state_files(temp_dir)

        assert result is True
        assert not old_json.exists()

        new_json = temp_dir / ".accordo" / "workflow_state.json"
        assert new_json.exists()
        assert new_json.read_text() == '{"state": "data"}'

        mock_print.assert_called_once_with(f"Migrated {old_json} to {new_json}")

    def test_migrate_workflow_state_files_both_formats(self, temp_dir):
        """Test migrate_workflow_state_files with both MD and JSON files."""
        # Create both old files
        old_md = temp_dir / "workflow_state.md"
        old_md.write_text("# Workflow State MD")
        old_json = temp_dir / "workflow_state.json"
        old_json.write_text('{"state": "data"}')

        with patch("builtins.print") as mock_print:
            result = migrate_workflow_state_files(temp_dir)

        assert result is True
        assert not old_md.exists()
        assert not old_json.exists()

        new_md = temp_dir / ".accordo" / "workflow_state.md"
        new_json = temp_dir / ".accordo" / "workflow_state.json"
        assert new_md.exists()
        assert new_json.exists()

        assert mock_print.call_count == 2

    def test_migrate_workflow_state_files_with_existing_targets(self, temp_dir):
        """Test migrate_workflow_state_files when target files already exist."""
        # Create old files
        old_md = temp_dir / "workflow_state.md"
        old_md.write_text("# Old MD")
        old_json = temp_dir / "workflow_state.json"
        old_json.write_text('{"old": "json"}')

        # Create existing target files
        workflow_dir = temp_dir / ".accordo"
        workflow_dir.mkdir()
        existing_md = workflow_dir / "workflow_state.md"
        existing_md.write_text("# Existing MD")
        existing_json = workflow_dir / "workflow_state.json"
        existing_json.write_text('{"existing": "json"}')

        with patch("builtins.print"):
            result = migrate_workflow_state_files(temp_dir)

        assert result is True

        # Check backups were created
        backup_md = workflow_dir / "workflow_state.md.backup"
        backup_json = workflow_dir / "workflow_state.json.backup"
        assert backup_md.exists()
        assert backup_json.exists()
        assert backup_md.read_text() == "# Existing MD"
        assert backup_json.read_text() == '{"existing": "json"}'

        # Check new files have old content
        assert existing_md.read_text() == "# Old MD"
        assert existing_json.read_text() == '{"old": "json"}'

    def test_migrate_workflow_state_files_partial_failure(self, temp_dir):
        """Test migrate_workflow_state_files when one migration fails."""
        # Create old files
        old_md = temp_dir / "workflow_state.md"
        old_md.write_text("# Old MD")
        old_json = temp_dir / "workflow_state.json"
        old_json.write_text('{"old": "json"}')

        # Make workflow directory read-only to cause failure
        workflow_dir = temp_dir / ".accordo"
        workflow_dir.mkdir()
        workflow_dir.chmod(0o444)

        with patch("builtins.print") as mock_print:
            result = migrate_workflow_state_files(temp_dir)

        assert result is False
        assert old_md.exists()  # Files should still exist
        assert old_json.exists()

        # Should have warning messages
        assert mock_print.call_count >= 2

        # Restore permissions for cleanup
        workflow_dir.chmod(0o755)

    def test_path_types_string_and_pathlib(self, temp_dir):
        """Test that functions work with both string and Path objects."""
        # Test with string
        workflow_dir_str = get_workflow_dir(str(temp_dir))
        config_path_str = get_project_config_path(str(temp_dir))

        # Test with Path
        workflow_dir_path = get_workflow_dir(temp_dir)
        config_path_path = get_project_config_path(temp_dir)

        assert workflow_dir_str == workflow_dir_path
        assert config_path_str == config_path_path
