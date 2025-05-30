"""Integration tests for workflow functionality."""

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


class TestWorkflowLifecycle:
    """Test the complete workflow lifecycle."""

    def setup_method(self):
        """Clear session state before each test."""
        session_manager.client_sessions.clear()

    def test_complete_workflow_cycle(self):
        """Test a complete workflow from init to completion."""
        # Create state manager
        state_manager = StateManager(client_id="test-lifecycle-client")

        # Initialize workflow
        task_description = "Test complete workflow cycle"
        state_manager.create_initial_state(task_description)

        # Verify initial state
        content = state_manager.read_state()
        assert task_description in content
        assert "Phase: INIT" in content
        assert "Status: READY" in content

        # Move to analyze phase
        assert state_manager.update_state_section(
            "ANALYZE", "RUNNING", task_description
        )
        content = state_manager.read_state()
        assert "Phase: ANALYZE" in content
        assert "Status: RUNNING" in content

        # Add analysis log
        assert state_manager.append_to_log("Analysis started")
        content = state_manager.read_state()
        assert "Analysis started" in content

        # Move to blueprint phase
        assert state_manager.update_state_section(
            "BLUEPRINT", "RUNNING", task_description
        )
        content = state_manager.read_state()
        assert "Phase: BLUEPRINT" in content

        # Move to construct phase
        assert state_manager.update_state_section(
            "CONSTRUCT", "RUNNING", task_description
        )
        content = state_manager.read_state()
        assert "Phase: CONSTRUCT" in content

        # Add construction log
        assert state_manager.append_to_log("Implementation in progress")
        content = state_manager.read_state()
        assert "Implementation in progress" in content

        # Move to validate phase
        assert state_manager.update_state_section(
            "VALIDATE", "RUNNING", task_description
        )
        content = state_manager.read_state()
        assert "Phase: VALIDATE" in content

        # Complete workflow
        assert state_manager.update_state_section(
            "VALIDATE", "COMPLETED", task_description
        )
        final_content = state_manager.read_state()
        assert "Status: COMPLETED" in final_content

    def test_workflow_error_handling(self):
        """Test workflow error handling and recovery."""
        state_manager = StateManager(client_id="test-error-client")

        # Initialize workflow
        task_description = "Test error handling"
        state_manager.create_initial_state(task_description)

        # Simulate error
        assert state_manager.update_state_section(
            "CONSTRUCT", "ERROR", task_description
        )
        content = state_manager.read_state()
        assert "Phase: CONSTRUCT" in content
        assert "Status: ERROR" in content

        # Log error details
        assert state_manager.append_to_log("Error: Test error occurred")
        content = state_manager.read_state()
        assert "Error: Test error occurred" in content

        # Recover from error
        assert state_manager.update_state_section(
            "CONSTRUCT", "RUNNING", task_description
        )
        content = state_manager.read_state()
        assert "Status: RUNNING" in content

    def test_multiple_workflow_items(self):
        """Test workflow with multiple items."""
        state_manager = StateManager(client_id="test-multi-items-client")

        # Initialize with multiple tasks
        state_manager.create_initial_state("Multi-item workflow test")

        # Simulate multiple workflow cycles
        for i in range(3):
            task_desc = f"Task {i + 1}"
            state_manager.update_state_section("ANALYZE", "RUNNING", task_desc)
            state_manager.append_to_log(f"Analyzing {task_desc}")
            state_manager.update_state_section("CONSTRUCT", "RUNNING", task_desc)
            state_manager.append_to_log(f"Implementing {task_desc}")
            state_manager.update_state_section("VALIDATE", "COMPLETED", task_desc)

        # Verify final state
        final_content = state_manager.read_state()
        assert "Task 1" in final_content
        assert "Task 2" in final_content
        assert "Task 3" in final_content

    def test_session_isolation(self):
        """Test that different clients have isolated sessions."""
        # Create multiple state managers with different clients
        manager1 = StateManager(client_id="client-1")
        manager2 = StateManager(client_id="client-2")

        # Initialize different tasks
        manager1.create_initial_state("Task for client 1")
        manager2.create_initial_state("Task for client 2")

        # Verify isolation
        content1 = manager1.read_state()
        content2 = manager2.read_state()

        assert "Task for client 1" in content1
        assert "Task for client 1" not in content2
        assert "Task for client 2" in content2
        assert "Task for client 2" not in content1

    def test_state_manager_client_id_management(self):
        """Test state manager client ID management."""
        # Test default client ID
        manager = StateManager()
        assert manager.get_client_id() == "default"

        # Test custom client ID
        manager = StateManager(client_id="custom-client")
        assert manager.get_client_id() == "custom-client"

        # Test setting client ID
        manager.set_client_id("new-client")
        assert manager.get_client_id() == "new-client"

    def test_log_accumulation(self):
        """Test that logs accumulate properly over time."""
        state_manager = StateManager(client_id="test-log-client")
        state_manager.create_initial_state("Log accumulation test")

        # Add multiple log entries
        log_entries = [
            "First log entry",
            "Second log entry",
            "Third log entry",
            "Fourth log entry",
        ]

        for entry in log_entries:
            state_manager.append_to_log(entry)

        # Verify all entries are present
        content = state_manager.read_state()
        for entry in log_entries:
            assert entry in content

    def test_state_transitions(self):
        """Test valid state transitions."""
        state_manager = StateManager(client_id="test-transitions-client")
        state_manager.create_initial_state("State transition test")

        # Test valid phase transitions
        valid_transitions = [
            ("INIT", "READY"),
            ("ANALYZE", "RUNNING"),
            ("BLUEPRINT", "RUNNING"),
            ("CONSTRUCT", "RUNNING"),
            ("VALIDATE", "RUNNING"),
            ("VALIDATE", "COMPLETED"),
        ]

        for phase, status in valid_transitions:
            result = state_manager.update_state_section(phase, status, "test item")
            assert result is True

            content = state_manager.read_state()
            assert f"Phase: {phase}" in content
            assert f"Status: {status}" in content

    @pytest.mark.asyncio
    async def test_auto_approval_workflow(self):
        """Test auto-approval workflow that skips NEEDS_PLAN_APPROVAL state."""
        import os
        from unittest.mock import Mock, patch

        from fastmcp import Context, FastMCP

        from src.dev_workflow_mcp.prompts.phase_prompts import register_phase_prompts

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
                ctx=context,
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

            # Create .workflow-commander directory
            workflow_dir = os.path.join(temp_dir, ".workflow-commander")
            os.makedirs(workflow_dir, exist_ok=True)
            config_file = os.path.join(workflow_dir, "project_config.md")

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
