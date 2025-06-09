"""Tests for validation utilities."""

from src.accordo_mcp.utils.validators import (
    validate_project_config,
    validate_project_files,
)


class TestValidateProjectConfig:
    """Test validate_project_config function."""

    def test_validate_valid_project_config(
        self, temp_project_config_file, valid_project_config_content
    ):
        """Test validation of a valid project config file."""
        temp_project_config_file.write_text(valid_project_config_content)

        is_valid, issues = validate_project_config(str(temp_project_config_file))

        assert is_valid is True
        assert issues == []

    def test_validate_nonexistent_config_file(self, temp_project_config_file):
        """Test validation when config file doesn't exist."""
        is_valid, issues = validate_project_config(str(temp_project_config_file))

        assert is_valid is False
        assert len(issues) == 1
        assert "does not exist" in issues[0]

    def test_validate_missing_config_sections(self, temp_project_config_file):
        """Test validation when required sections are missing."""
        content = """# Project Configuration

## Project Info
- **Name**: Test Project

# Missing Dependencies, Test Commands, and Changelog sections
"""
        temp_project_config_file.write_text(content)

        is_valid, issues = validate_project_config(str(temp_project_config_file))

        assert is_valid is False
        assert len(issues) == 3  # Missing 3 sections
        assert any(
            "Missing required section: ## Dependencies" in issue for issue in issues
        )
        assert any(
            "Missing required section: ## Test Commands" in issue for issue in issues
        )
        assert any(
            "Missing required section: ## Changelog" in issue for issue in issues
        )

    def test_validate_config_file_read_error(self, temp_project_config_file):
        """Test validation when config file cannot be read."""
        # Test with a directory instead of a file to simulate read error
        temp_dir = temp_project_config_file.parent / "not_a_file"
        temp_dir.mkdir()

        is_valid, issues = validate_project_config(str(temp_dir))

        assert is_valid is False
        assert len(issues) == 1
        assert "Could not read file:" in issues[0]


class TestValidateProjectFiles:
    """Test validate_project_files function."""

    def test_validate_project_config_valid(
        self, temp_project_config_file, valid_project_config_content
    ):
        """Test validation when project config is valid."""
        temp_project_config_file.write_text(valid_project_config_content)

        is_valid, issues = validate_project_files(str(temp_project_config_file))

        assert is_valid is True
        assert issues == []

    def test_validate_project_config_missing(self, temp_dir):
        """Test validation when project config file is missing."""
        workflow_dir = temp_dir / ".accordo"
        workflow_dir.mkdir(exist_ok=True)
        config_path = workflow_dir / "missing_config.md"

        is_valid, issues = validate_project_files(str(config_path))

        assert is_valid is False
        assert len(issues) == 1
        assert "project_config.md file does not exist" in issues[0]

    def test_validate_project_config_invalid(self, temp_project_config_file):
        """Test validation when project config is invalid."""
        invalid_content = """# Project Configuration

## Project Info
- **Name**: Test Project

# Missing required sections
"""
        temp_project_config_file.write_text(invalid_content)

        is_valid, issues = validate_project_files(str(temp_project_config_file))

        assert is_valid is False
        assert len(issues) == 3  # Missing 3 sections
        assert all("project_config.md:" in issue for issue in issues)
        assert any("Dependencies" in issue for issue in issues)
        assert any("Test Commands" in issue for issue in issues)
        assert any("Changelog" in issue for issue in issues)
