"""Tests for validation utilities."""

from src.dev_workflow_mcp.utils.validators import (
    validate_project_config,
    validate_workflow_files,
    validate_workflow_state,
)


class TestValidateWorkflowState:
    """Test validate_workflow_state function."""

    def test_validate_valid_workflow_state(
        self, temp_workflow_file, valid_workflow_state_content
    ):
        """Test validation of a valid workflow state file."""
        temp_workflow_file.write_text(valid_workflow_state_content)

        is_valid, issues = validate_workflow_state(str(temp_workflow_file))

        assert is_valid is True
        assert issues == []

    def test_validate_nonexistent_file(self, temp_workflow_file):
        """Test validation when file doesn't exist."""
        is_valid, issues = validate_workflow_state(str(temp_workflow_file))

        assert is_valid is False
        assert len(issues) == 1
        assert "does not exist" in issues[0]

    def test_validate_missing_required_sections(self, temp_workflow_file):
        """Test validation when required sections are missing."""
        content = """# workflow_state.md
_Last updated: 2024-12-19_

## State
Phase: INIT  
Status: READY  
CurrentItem: Test task  

## Plan
Test plan content
# Missing Rules, Items, Log, ArchiveLog sections
"""
        temp_workflow_file.write_text(content)

        is_valid, issues = validate_workflow_state(str(temp_workflow_file))

        assert is_valid is False
        assert len(issues) == 4  # Missing 4 sections
        assert any("Missing required section: ## Rules" in issue for issue in issues)
        assert any("Missing required section: ## Items" in issue for issue in issues)
        assert any("Missing required section: ## Log" in issue for issue in issues)
        assert any(
            "Missing required section: ## ArchiveLog" in issue for issue in issues
        )

    def test_validate_missing_state_fields(self, temp_workflow_file):
        """Test validation when State section fields are missing."""
        content = """# workflow_state.md
_Last updated: 2024-12-19_

## State
Phase: INIT  
# Missing Status and CurrentItem fields

## Plan
Test plan content

## Rules
Test rules

## Items
| id | description | status |
|----|-------------|--------|
| 1 | Test task | pending |

## Log
Test log

## ArchiveLog
Test archive
"""
        temp_workflow_file.write_text(content)

        is_valid, issues = validate_workflow_state(str(temp_workflow_file))

        assert is_valid is False
        assert len(issues) == 2  # Missing 2 fields
        assert any(
            "Missing field in State section: Status:" in issue for issue in issues
        )
        assert any(
            "Missing field in State section: CurrentItem:" in issue for issue in issues
        )

    def test_validate_missing_items_table_header(self, temp_workflow_file):
        """Test validation when Items section is missing table header."""
        content = """# workflow_state.md
_Last updated: 2024-12-19_

## State
Phase: INIT  
Status: READY  
CurrentItem: Test task  

## Plan
Test plan content

## Rules
Test rules

## Items
Some items but no table header

## Log
Test log

## ArchiveLog
Test archive
"""
        temp_workflow_file.write_text(content)

        is_valid, issues = validate_workflow_state(str(temp_workflow_file))

        assert is_valid is False
        assert len(issues) == 1
        assert "Items section missing proper table header" in issues[0]

    def test_validate_items_as_last_section(self, temp_workflow_file):
        """Test validation when Items is the last section."""
        content = """# workflow_state.md
_Last updated: 2024-12-19_

## State
Phase: INIT  
Status: READY  
CurrentItem: Test task  

## Plan
Test plan content

## Rules
Test rules

## Log
Test log

## ArchiveLog
Test archive

## Items
| id | description | status |
|----|-------------|--------|
| 1 | Test task | pending |
"""
        temp_workflow_file.write_text(content)

        is_valid, issues = validate_workflow_state(str(temp_workflow_file))

        assert is_valid is True
        assert issues == []

    def test_validate_file_read_error(self, temp_workflow_file):
        """Test validation when file cannot be read."""
        # Test with a directory instead of a file to simulate read error
        temp_dir = temp_workflow_file.parent / "not_a_file"
        temp_dir.mkdir()

        is_valid, issues = validate_workflow_state(str(temp_dir))

        assert is_valid is False
        assert len(issues) == 1
        assert "Could not read file:" in issues[0]

    def test_validate_unparseable_state_section(self, temp_workflow_file):
        """Test validation when State section cannot be parsed."""
        content = """# workflow_state.md
_Last updated: 2024-12-19_

## State
Malformed state content without proper structure

## Plan
Test plan content

## Rules
Test rules

## Items
| id | description | status |
|----|-------------|--------|
| 1 | Test task | pending |

## Log
Test log

## ArchiveLog
Test archive
"""
        temp_workflow_file.write_text(content)

        is_valid, issues = validate_workflow_state(str(temp_workflow_file))

        assert is_valid is False
        # Should have issues for missing fields in state section
        assert len(issues) >= 3  # Missing Phase, Status, CurrentItem


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

# Missing Dependencies, Test Commands, Changelog sections
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


class TestValidateWorkflowFiles:
    """Test validate_workflow_files function."""

    def test_validate_both_files_valid(
        self,
        temp_workflow_file,
        temp_project_config_file,
        valid_workflow_state_content,
        valid_project_config_content,
    ):
        """Test validation when both files are valid."""
        temp_workflow_file.write_text(valid_workflow_state_content)
        temp_project_config_file.write_text(valid_project_config_content)

        # Change to the temp directory so the default file names are found
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_workflow_file.parent)
            is_valid, issues = validate_workflow_files()
        finally:
            os.chdir(original_cwd)

        assert is_valid is True
        assert issues == []

    def test_validate_both_files_missing(self, temp_dir):
        """Test validation when both files are missing."""
        # Change to a temp directory where files don't exist
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            is_valid, issues = validate_workflow_files()
        finally:
            os.chdir(original_cwd)

        assert is_valid is False
        assert len(issues) == 2
        assert any(
            "workflow_state.md: workflow_state.md file does not exist" in issue
            for issue in issues
        )
        assert any(
            "project_config.md: project_config.md file does not exist" in issue
            for issue in issues
        )

    def test_validate_workflow_state_invalid(
        self, temp_workflow_file, temp_project_config_file, valid_project_config_content
    ):
        """Test validation when workflow state is invalid but config is valid."""
        # Create invalid workflow state
        invalid_workflow_content = """# workflow_state.md
## State
Phase: INIT
# Missing other required sections
"""
        temp_workflow_file.write_text(invalid_workflow_content)
        temp_project_config_file.write_text(valid_project_config_content)

        # Change to the temp directory so the default file names are found
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_workflow_file.parent)
            is_valid, issues = validate_workflow_files()
        finally:
            os.chdir(original_cwd)

        assert is_valid is False
        assert len(issues) > 0
        assert any("workflow_state.md:" in issue for issue in issues)

    def test_validate_project_config_invalid(
        self, temp_workflow_file, temp_project_config_file, valid_workflow_state_content
    ):
        """Test validation when project config is invalid but workflow state is valid."""
        temp_workflow_file.write_text(valid_workflow_state_content)

        # Create invalid project config
        invalid_config_content = """# Project Configuration
## Project Info
- **Name**: Test Project
# Missing other required sections
"""
        temp_project_config_file.write_text(invalid_config_content)

        # Change to the temp directory so the default file names are found
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_workflow_file.parent)
            is_valid, issues = validate_workflow_files()
        finally:
            os.chdir(original_cwd)

        assert is_valid is False
        assert len(issues) > 0
        assert any("project_config.md:" in issue for issue in issues)
