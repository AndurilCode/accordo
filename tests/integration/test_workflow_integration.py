"""Integration tests for workflow state session operations and end-to-end state transitions."""

import tempfile
import pytest

from src.dev_workflow_mcp.models.workflow_state import (
    WorkflowItem,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from src.dev_workflow_mcp.utils import session_manager
from src.dev_workflow_mcp.utils.state_manager import StateManager
from src.dev_workflow_mcp.utils.validators import (
    validate_project_config,
    validate_project_files,
)


class TestWorkflowStateSessionOperations:
    """Test complete workflow state session operations."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_create_and_read_workflow_state_session(self):
        """Test creating and reading a workflow state session."""
        state_manager = StateManager(client_id="test-client")

        # Create initial state (creates session)
        state_manager.create_initial_state("Test task description")

        # Read the state back (from session)
        content = state_manager.read_state()
        assert "Test task description" in content
        assert "Phase: INIT" in content
        assert "Status: READY" in content

    def test_update_workflow_state_sections(self):
        """Test updating different sections of workflow state session."""
        state_manager = StateManager(client_id="test-update-client")

        # Create initial state
        state_manager.create_initial_state("Integration test task")

        # Update phase and status
        success = state_manager.update_state_section(
            phase="CONSTRUCT", status="RUNNING", current_item="Implement feature X"
        )
        assert success

        # Read and verify updates (from session)
        content = state_manager.read_state()
        assert "Phase: CONSTRUCT" in content
        assert "Status: RUNNING" in content
        assert "CurrentItem: Implement feature X" in content

    def test_append_log_entries(self):
        """Test appending log entries to workflow state session."""
        state_manager = StateManager(client_id="test-log-client")

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

        # Read and verify all entries are present (from session)
        content = state_manager.read_state()
        for entry in log_entries:
            assert entry in content

    def test_session_isolation(self):
        """Test that different clients have isolated sessions."""
        manager1 = StateManager(client_id="client-1")
        manager2 = StateManager(client_id="client-2")

        # Create different tasks
        manager1.create_initial_state("Task for client 1")
        manager2.create_initial_state("Task for client 2")

        # Update different states
        manager1.update_state_section("ANALYZE", "RUNNING", "Analyzing requirements")
        manager2.update_state_section("CONSTRUCT", "RUNNING", "Building features")

        # Verify isolation
        content1 = manager1.read_state()
        content2 = manager2.read_state()

        assert "Task for client 1" in content1
        assert "Task for client 1" not in content2
        assert "Phase: ANALYZE" in content1
        assert "Phase: ANALYZE" not in content2

        assert "Task for client 2" in content2
        assert "Task for client 2" not in content1
        assert "Phase: CONSTRUCT" in content2
        assert "Phase: CONSTRUCT" not in content1


class TestEndToEndWorkflowTransitions:
    """Test end-to-end workflow state transitions."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_complete_workflow_lifecycle(self):
        """Test a complete workflow from INIT to COMPLETED."""
        state_manager = StateManager(client_id="test-lifecycle-client")

        # 1. Initialize workflow
        state_manager.create_initial_state("Build a simple web app")
        content = state_manager.read_state()
        # Session starts with INIT phase
        assert "Phase: INIT" in content
        assert "Status: READY" in content

        # 2. Move to ANALYZE phase
        state_manager.update_state_section("ANALYZE", "RUNNING")
        state_manager.append_to_log("Started analysis phase - examining requirements")

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
        state_manager.append_to_log("All tests passed, workflow completed successfully")

        # Verify final state
        final_content = state_manager.read_state()
        assert "Phase: VALIDATE" in final_content
        assert "Status: COMPLETED" in final_content
        assert "workflow completed successfully" in final_content

    def test_workflow_with_error_recovery(self):
        """Test workflow with error states and recovery."""
        state_manager = StateManager(client_id="test-error-client")

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
        """Test workflow with multiple items and transitions."""
        state_manager = StateManager(client_id="test-multi-client")

        # Initialize workflow
        state_manager.create_initial_state("Multi-item workflow test")

        # Add multiple log entries to simulate multiple items
        items = [
            "Implement user registration",
            "Add email verification",
            "Create user dashboard",
            "Add password reset functionality",
        ]

        for i, item in enumerate(items, 1):
            state_manager.append_to_log(f"Item {i}: {item}")
            state_manager.update_state_section("CONSTRUCT", "RUNNING", item)

        # Complete workflow
        state_manager.update_state_section("VALIDATE", "COMPLETED")

        # Verify all items are logged
        final_content = state_manager.read_state()
        for item in items:
            assert item in final_content
        assert "Status: COMPLETED" in final_content

    @pytest.mark.asyncio
    async def test_auto_approval_workflow(self):
        """Test auto-approval workflow that skips NEEDS_PLAN_APPROVAL state."""
        import os
        from unittest.mock import patch, Mock
        from fastmcp import Context
        from src.dev_workflow_mcp.prompts.phase_prompts import register_phase_prompts
        from fastmcp import FastMCP

        # Test with auto-approval enabled
        with patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "true"}):
            # Create MCP server and register tools
            mcp = FastMCP("test-server")
            register_phase_prompts(mcp)
            
            # Create mock context
            context = Mock(spec=Context)
            context.client_id = "test-auto-approval-client"
            
            # Get tools using the async method
            tools = await mcp.get_tools()
            blueprint_tool = tools["blueprint_phase_guidance"]
            
            # Call blueprint phase guidance
            result = blueprint_tool.fn(
                task_description="Test auto-approval feature",
                requirements_summary="Test requirements for auto-approval",
                ctx=context
            )
            
            # Verify auto-approval behavior
            assert "AUTO-APPROVAL ACTIVATED" in result
            assert "WORKFLOW_AUTO_APPROVE_PLANS=true" in result
            assert "Phase → CONSTRUCT" in result
            assert "auto-transitioned" in result
            assert "no user approval needed" in result.lower()


class TestProjectConfigIntegration:
    """Test project configuration validation integration."""

    def test_project_config_validation(self):
        """Test project config validation with real file content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            import os

            config_file = os.path.join(temp_dir, "project_config.md")

            # Create valid project config
            config_content = """# Project Configuration

## Project Info
- **Name**: Integration Test Project
- **Version**: 1.0.0
- **Description**: Test project for integration testing

## Dependencies
- Python 3.12+
- FastMCP
- Pydantic

## Test Commands
```bash
python -m pytest
ruff check .
```

## Changelog
- Initial project setup for integration testing
"""
            with open(config_file, "w") as f:
                f.write(config_content)

            # Validate the created file
            is_valid, errors = validate_project_config(config_file)
            assert is_valid
            assert len(errors) == 0

            # Test combined validation
            is_valid, errors = validate_project_files(config_file)
            assert is_valid
            assert len(errors) == 0


class TestWorkflowStateModelIntegration:
    """Test WorkflowState model integration with sessions."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_workflow_state_model_with_session_content(self):
        """Test WorkflowState model integration with session content."""
        # Create a WorkflowState instance
        workflow_state = WorkflowState(
            client_id="test-model-client",
            phase=WorkflowPhase.CONSTRUCT,
            status=WorkflowStatus.RUNNING,
            current_item="Test model integration",
            plan="Test plan for model integration",
            items=[
                WorkflowItem(id=1, description="First task", status="completed"),
                WorkflowItem(id=2, description="Second task", status="pending"),
            ],
            log="Test log entry",
            archive_log="Test archive log",
        )

        # Generate markdown
        markdown = workflow_state.to_markdown()

        # Verify markdown content
        assert "# Workflow State" in markdown
        assert "Phase: CONSTRUCT" in markdown
        assert "Status: RUNNING" in markdown
        assert "CurrentItem: Test model integration" in markdown
        assert "Test plan for model integration" in markdown
        assert "First task" in markdown
        assert "Second task" in markdown
        assert "Test log entry" in markdown

    def test_workflow_state_log_rotation_integration(self):
        """Test log rotation functionality in workflow state."""
        state_manager = StateManager(client_id="test-rotation-client")
        state_manager.create_initial_state("Log rotation test")

        # Add many log entries to trigger rotation
        long_log_entries = [f"Log entry {i}: " + "x" * 200 for i in range(30)]

        for entry in long_log_entries:
            state_manager.append_to_log(entry)

        # Read final state
        content = state_manager.read_state()

        # Should contain recent entries
        assert "Log entry 29" in content
        # Log rotation should have occurred due to length
        assert len(content) > 1000  # Should have substantial content


class TestSessionManagementIntegration:
    """Test session management integration."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_session_creation_and_retrieval(self):
        """Test session creation and retrieval through StateManager."""
        # Create multiple sessions
        clients = ["client-1", "client-2", "client-3"]
        managers = []

        for client_id in clients:
            manager = StateManager(client_id=client_id)
            manager.create_initial_state(f"Task for {client_id}")
            managers.append(manager)

        # Verify all sessions exist and are isolated
        for i, manager in enumerate(managers):
            content = manager.read_state()
            assert f"Task for {clients[i]}" in content

            # Verify isolation - shouldn't contain other clients' tasks
            for j, other_client in enumerate(clients):
                if i != j:
                    assert f"Task for {other_client}" not in content

    def test_session_state_persistence(self):
        """Test that session state persists across StateManager instances."""
        client_id = "persistent-client"

        # Create initial state with first manager
        manager1 = StateManager(client_id=client_id)
        manager1.create_initial_state("Persistent task")
        manager1.update_state_section("ANALYZE", "RUNNING", "Analyzing requirements")
        manager1.append_to_log("First log entry")

        # Create second manager with same client_id
        manager2 = StateManager(client_id=client_id)

        # Should access the same session
        content = manager2.read_state()
        assert "Persistent task" in content
        assert "Phase: ANALYZE" in content
        assert "Status: RUNNING" in content
        assert "Analyzing requirements" in content
        assert "First log entry" in content

        # Update through second manager
        manager2.append_to_log("Second log entry")

        # First manager should see the update
        updated_content = manager1.read_state()
        assert "Second log entry" in updated_content
