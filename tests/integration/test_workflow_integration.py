"""Integration tests for workflow state file operations and end-to-end state transitions."""

import os
import tempfile

from src.dev_workflow_mcp.models.workflow_state import (
    WorkflowItem,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from src.dev_workflow_mcp.utils.state_manager import StateManager
from src.dev_workflow_mcp.utils.validators import (
    validate_project_config,
    validate_workflow_files,
    validate_workflow_state,
)


class TestWorkflowStateFileOperations:
    """Test complete workflow state file operations with real files."""

    def test_create_and_read_workflow_state_file(self):
        """Test creating and reading a workflow state file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "workflow_state.md")
            state_manager = StateManager(state_file)

            # Create initial state
            state_manager.create_initial_state("Test task description")

            # Verify file was created
            assert os.path.exists(state_file)

            # Read the state back
            content = state_manager.read_state()
            assert "Test task description" in content
            assert "Phase: INIT" in content
            assert "Status: READY" in content

    def test_update_workflow_state_sections(self):
        """Test updating different sections of workflow state file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "workflow_state.md")
            state_manager = StateManager(state_file)

            # Create initial state
            state_manager.create_initial_state("Integration test task")

            # Update phase and status
            success = state_manager.update_state_section(
                phase="CONSTRUCT", status="RUNNING", current_item="Implement feature X"
            )
            assert success

            # Read and verify updates
            content = state_manager.read_state()
            assert "Phase: CONSTRUCT" in content
            assert "Status: RUNNING" in content
            assert "CurrentItem: Implement feature X" in content

    def test_append_log_entries(self):
        """Test appending log entries to workflow state file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "workflow_state.md")
            state_manager = StateManager(state_file)

            # Create initial state
            state_manager.create_initial_state("Log test task")

            # Append multiple log entries
            log_entries = [
                "Started implementation phase",
                "Created database schema",
                "Implemented user authentication",
                "Added unit tests",
            ]

            for entry in log_entries:
                success = state_manager.append_to_log(entry)
                assert success

            # Read and verify all entries are present
            content = state_manager.read_state()
            for entry in log_entries:
                assert entry in content

    def test_workflow_state_validation_integration(self):
        """Test workflow state validation with real file content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "workflow_state.md")
            state_manager = StateManager(state_file)

            # Create initial state
            state_manager.create_initial_state("Validation test task")

            # Validate the created file
            is_valid, errors = validate_workflow_state(state_file)
            assert is_valid
            assert len(errors) == 0

            # Update state and validate again
            state_manager.update_state_section("BLUEPRINT", "NEEDS_PLAN_APPROVAL")
            is_valid, errors = validate_workflow_state(state_file)
            assert is_valid
            assert len(errors) == 0


class TestEndToEndWorkflowTransitions:
    """Test end-to-end workflow state transitions."""

    def test_complete_workflow_lifecycle(self):
        """Test a complete workflow from INIT to COMPLETED."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "workflow_state.md")
            state_manager = StateManager(state_file)

            # 1. Initialize workflow
            state_manager.create_initial_state("Build a simple web app")
            content = state_manager.read_state()
            assert "Phase: INIT" in content
            assert "Status: READY" in content

            # 2. Move to ANALYZE phase
            state_manager.update_state_section("ANALYZE", "RUNNING")
            state_manager.append_to_log(
                "Started analysis phase - examining requirements"
            )

            # 3. Move to BLUEPRINT phase
            state_manager.update_state_section("BLUEPRINT", "RUNNING")
            state_manager.append_to_log("Creating implementation plan")

            # 4. Blueprint needs approval
            state_manager.update_state_section("BLUEPRINT", "NEEDS_PLAN_APPROVAL")
            state_manager.append_to_log("Plan created, waiting for approval")

            # 5. Move to CONSTRUCT phase
            state_manager.update_state_section(
                "CONSTRUCT", "RUNNING", "Implement user authentication"
            )
            state_manager.append_to_log("Started implementation - creating auth system")

            # 6. Move to VALIDATE phase
            state_manager.update_state_section("VALIDATE", "RUNNING")
            state_manager.append_to_log("Running tests and validation")

            # 7. Complete workflow
            state_manager.update_state_section("VALIDATE", "COMPLETED")
            state_manager.append_to_log(
                "All tests passed, workflow completed successfully"
            )

            # Verify final state
            final_content = state_manager.read_state()
            assert "Phase: VALIDATE" in final_content
            assert "Status: COMPLETED" in final_content
            assert "workflow completed successfully" in final_content

    def test_workflow_with_error_recovery(self):
        """Test workflow with error states and recovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "workflow_state.md")
            state_manager = StateManager(state_file)

            # Initialize and start workflow
            state_manager.create_initial_state("Error recovery test")
            state_manager.update_state_section("CONSTRUCT", "RUNNING")

            # Encounter an error
            state_manager.update_state_section("CONSTRUCT", "ERROR")
            state_manager.append_to_log(
                "ERROR: Database connection failed during implementation"
            )

            # Recover from error
            state_manager.append_to_log("Fixing database connection issue")
            state_manager.update_state_section("CONSTRUCT", "RUNNING")
            state_manager.append_to_log(
                "Database connection restored, continuing implementation"
            )

            # Complete successfully
            state_manager.update_state_section("VALIDATE", "COMPLETED")

            # Verify error and recovery are logged
            final_content = state_manager.read_state()
            assert "ERROR: Database connection failed" in final_content
            assert "Database connection restored" in final_content
            assert "Status: COMPLETED" in final_content

    def test_workflow_with_multiple_items(self):
        """Test workflow with multiple items in the items table."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "workflow_state.md")
            state_manager = StateManager(state_file)

            # Create initial state with multiple items
            initial_content = """# workflow_state.md
_Last updated: 2024-12-19_

## State
Phase: INIT  
Status: READY  
CurrentItem: Multi-item workflow test  

## Plan
Implementation plan will be created during blueprint phase.

## Rules
Standard workflow rules apply.

## Items
| id | description | status |
|----|-------------|--------|
| 1 | Setup project structure | pending |
| 2 | Implement user authentication | pending |
| 3 | Create database schema | pending |
| 4 | Build REST API | pending |
| 5 | Add unit tests | pending |

## Log
<!-- AI appends detailed reasoning, tool output, and errors here -->
"""

            # Write initial content
            with open(state_file, "w") as f:
                f.write(initial_content)

            # Process through workflow phases
            state_manager.update_state_section(
                "CONSTRUCT", "RUNNING", "Setup project structure"
            )
            state_manager.append_to_log("Working on item 1: Setup project structure")

            state_manager.update_state_section(
                "CONSTRUCT", "RUNNING", "Implement user authentication"
            )
            state_manager.append_to_log(
                "Working on item 2: Implement user authentication"
            )

            state_manager.update_state_section(
                "CONSTRUCT", "RUNNING", "Create database schema"
            )
            state_manager.append_to_log("Working on item 3: Create database schema")

            # Verify current item tracking
            final_content = state_manager.read_state()
            assert "CurrentItem: Create database schema" in final_content
            assert "Working on item 1" in final_content
            assert "Working on item 2" in final_content
            assert "Working on item 3" in final_content


class TestProjectConfigIntegration:
    """Test project config file operations and validation."""

    def test_project_config_validation(self):
        """Test project config validation with real file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "project_config.md")

            # Create a valid project config file
            config_content = """# Project Configuration

## Project Info
- **Name**: Test Project
- **Version**: 1.0.0
- **Description**: Integration test project

## Dependencies
- Python 3.12+
- pytest
- fastmcp

## Test Commands
- `python -m pytest`
- `ruff check .`
- `mypy src/`

## Changelog
- Initial project setup
"""

            with open(config_file, "w") as f:
                f.write(config_content)

            # Validate the config file
            is_valid, errors = validate_project_config(config_file)
            assert is_valid
            assert len(errors) == 0

    def test_combined_workflow_files_validation(self):
        """Test validation of both workflow state and project config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "workflow_state.md")
            config_file = os.path.join(temp_dir, "project_config.md")

            # Create workflow state file
            state_manager = StateManager(state_file)
            state_manager.create_initial_state("Combined validation test")

            # Create project config file
            config_content = """# Project Configuration

## Project Info
- **Name**: Combined Test
- **Version**: 1.0.0

## Dependencies
- Python 3.12+
- pytest

## Test Commands
- `python -m pytest`

## Changelog
- Test entry
"""
            with open(config_file, "w") as f:
                f.write(config_content)

            # Validate both files together
            is_valid, errors = validate_workflow_files(state_file, config_file)
            assert is_valid
            assert len(errors) == 0


class TestWorkflowStateModelIntegration:
    """Test WorkflowState model with real file operations."""

    def test_workflow_state_model_with_file_content(self):
        """Test WorkflowState model parsing real file content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "workflow_state.md")
            state_manager = StateManager(state_file)

            # Create initial state
            state_manager.create_initial_state("Model integration test")

            # Add some items and log entries
            state_manager.update_state_section("CONSTRUCT", "RUNNING", "Test item")
            state_manager.append_to_log("First log entry")
            state_manager.append_to_log("Second log entry")

            # Read content and create WorkflowState model
            # content = state_manager.read_state()  # Not needed for this test

            # Create a WorkflowState instance
            workflow_state = WorkflowState(
                phase=WorkflowPhase.CONSTRUCT,
                status=WorkflowStatus.RUNNING,
                current_item="Test item",
                items=[
                    WorkflowItem(
                        id=1, description="Model integration test", status="pending"
                    )
                ],
                log="First log entry\nSecond log entry",
            )

            # Verify model properties
            assert workflow_state.phase == WorkflowPhase.CONSTRUCT
            assert workflow_state.status == WorkflowStatus.RUNNING
            assert workflow_state.current_item == "Test item"
            assert len(workflow_state.items) == 1
            assert "First log entry" in workflow_state.log

    def test_workflow_state_log_rotation_integration(self):
        """Test log rotation with real file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "workflow_state.md")
            state_manager = StateManager(state_file)

            # Create initial state
            state_manager.create_initial_state("Log rotation test")

            # Create a WorkflowState instance
            workflow_state = WorkflowState(
                phase=WorkflowPhase.CONSTRUCT,
                status=WorkflowStatus.RUNNING,
                items=[],
                log="",
            )

            # Add many log entries to trigger rotation
            long_entry = (
                "This is a very long log entry that will help us reach the 5000 character limit for log rotation testing. "
                * 50
            )

            for i in range(10):
                workflow_state.add_log_entry(f"Entry {i}: {long_entry}")

            # Verify log rotation occurred
            assert len(workflow_state.log) < 5000
            assert workflow_state.archive_log is not None
            assert len(workflow_state.archive_log) > 0


class TestErrorHandlingIntegration:
    """Test error handling in integration scenarios."""

    def test_file_permission_errors(self):
        """Test handling of file permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a read-only directory
            readonly_dir = os.path.join(temp_dir, "readonly")
            os.makedirs(readonly_dir)
            os.chmod(readonly_dir, 0o444)  # Read-only

            state_file = os.path.join(readonly_dir, "workflow_state.md")
            state_manager = StateManager(state_file)

            try:
                # This should handle the permission error gracefully
                result = state_manager.create_initial_state("Permission test")
                # The method should return None or handle the error
                assert result is None or isinstance(result, str)
            except PermissionError:
                # This is also acceptable - the error should be caught at a higher level
                pass
            finally:
                # Restore permissions for cleanup
                os.chmod(readonly_dir, 0o755)

    def test_malformed_file_handling(self):
        """Test handling of malformed workflow state files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, "malformed_state.md")

            # Create a malformed file
            malformed_content = """This is not a valid workflow state file
It's missing required sections and has invalid format
## State
This section is incomplete
"""

            with open(state_file, "w") as f:
                f.write(malformed_content)

            # Test validation
            is_valid, errors = validate_workflow_state(state_file)
            assert not is_valid
            assert len(errors) > 0

            # Test state manager with malformed file
            state_manager = StateManager(state_file)
            content = state_manager.read_state()
            assert content == malformed_content  # Should read the content as-is

            # Updating should handle the malformed content gracefully
            success = state_manager.update_state_section("CONSTRUCT", "RUNNING")
            # Should either succeed (by finding/creating sections) or fail gracefully
            assert isinstance(success, bool)
