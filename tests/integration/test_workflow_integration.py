"""Integration tests for workflow functionality with YAML-only architecture."""

import tempfile

from src.dev_workflow_mcp.models.workflow_state import (
    WorkflowItem,
    WorkflowState,
)
from src.dev_workflow_mcp.utils import session_manager
from src.dev_workflow_mcp.utils.state_manager import StateManager
from src.dev_workflow_mcp.utils.validators import (
    validate_project_config,
    validate_project_files,
)


class TestWorkflowLifecycle:
    """Test the workflow lifecycle with YAML-only architecture."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_state_manager_client_id_management(self):
        """Test state manager client ID management (still works)."""
        # Test default client ID
        manager = StateManager()
        assert manager.get_client_id() == "default"

        # Test custom client ID
        manager = StateManager(client_id="custom-client")
        assert manager.get_client_id() == "custom-client"

        # Test setting client ID
        manager.set_client_id("new-client")
        assert manager.get_client_id() == "new-client"


class TestProjectConfigIntegration:
    """Test project configuration validation (still works)."""

    def test_project_config_validation(self):
        """Test project configuration validation."""
        # Create a temporary project config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Project Configuration

## Project Info
Test project configuration.

## Dependencies
- Python 3.8+
- FastMCP

## Test Commands
```bash
pytest tests/
```

## Changelog
- Initial setup
""")
            config_path = f.name

        # Validate the configuration
        try:
            is_valid, issues = validate_project_config(config_path)
            assert is_valid is True
            assert len(issues) == 0
        finally:
            # Clean up
            import os

            os.unlink(config_path)

        # Test with non-existent file
        is_valid, issues = validate_project_config("non_existent_config.md")
        assert is_valid is False
        assert len(issues) > 0

        # Test project files validation
        is_valid, issues = validate_project_files()
        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)


class TestWorkflowStateModelIntegration:
    """Test workflow state model integration (data models still work)."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_workflow_state_model_with_session_content(self):
        """Test WorkflowState model functionality."""
        # Create a workflow state directly
        state = WorkflowState(
            phase="INIT",
            status="READY",
            current_item="Test workflow state model",
            plan="Test plan for model validation",
            items=[WorkflowItem(id=1, description="Model test task", status="pending")],
            log=["Model initialization log entry"],
        )

        # Test state properties
        assert state.phase == "INIT"
        assert state.status == "READY"
        assert state.current_item == "Test workflow state model"
        assert len(state.items) == 1
        assert len(state.log) == 1

        # Test markdown export
        markdown = state.to_markdown()
        assert "# Workflow State" in markdown
        assert "Test workflow state model" in markdown
        assert "Model test task" in markdown

        # Test JSON export
        json_str = state.to_json()
        assert '"phase": "INIT"' in json_str
        assert '"status": "READY"' in json_str


class TestSessionManagementIntegration:
    """Test session management with YAML-only architecture."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    # Note: Session creation tests removed as they required legacy session support
    # Current YAML-only architecture uses dynamic workflow sessions exclusively
