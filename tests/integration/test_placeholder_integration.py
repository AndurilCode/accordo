"""Integration tests for placeholder replacement in the workflow system."""

from src.dev_workflow_mcp.models.workflow_state import DynamicWorkflowState
from src.dev_workflow_mcp.prompts.phase_prompts import format_enhanced_node_status
from src.dev_workflow_mcp.utils.yaml_loader import WorkflowLoader


class TestPlaceholderIntegration:
    """Integration tests for placeholder replacement across the workflow system."""

    def test_default_coding_workflow_placeholder_replacement(self):
        """Test that placeholders work in the default coding workflow."""
        # Load the default coding workflow
        loader = WorkflowLoader("docs/workflows")
        workflow = loader.load_workflow("docs/workflows/default-coding.yaml")

        assert workflow is not None, "Failed to load default coding workflow"

        # Create a session with test inputs
        session = DynamicWorkflowState(
            client_id="test-client",
            workflow_name=workflow.name,
            current_node="analyze",
            status="READY",
            inputs={
                "task_description": "Implement: JWT authentication with refresh tokens",
                "project_config_path": ".workflow-commander/test_config.md",
            },
            current_item="Test implementation",
        )

        # Test analyze phase
        analyze_node = workflow.workflow.tree.get("analyze")
        assert analyze_node is not None

        formatted_status = format_enhanced_node_status(analyze_node, workflow, session)

        # Verify placeholders were replaced
        assert "Implement: JWT authentication with refresh tokens" in formatted_status
        assert ".workflow-commander/test_config.md" in formatted_status
        assert "${{ inputs.task_description }}" not in formatted_status
        assert "${{ inputs.project_config_path }}" not in formatted_status

    def test_placeholder_replacement_preserves_workflow_structure(self):
        """Test that placeholder replacement doesn't modify the original workflow."""
        # Load a workflow
        loader = WorkflowLoader("docs/workflows")
        workflow = loader.load_workflow("docs/workflows/default-coding.yaml")

        assert workflow is not None

        # Store original goal content
        original_goal = workflow.workflow.tree["analyze"].goal
        assert "${{ inputs.task_description }}" in original_goal

        # Create a session and format status
        session = DynamicWorkflowState(
            client_id="test-client",
            workflow_name=workflow.name,
            current_node="analyze",
            status="READY",
            inputs={
                "task_description": "Test modification",
                "project_config_path": "/test",
            },
            current_item="Test",
        )

        analyze_node = workflow.workflow.tree.get("analyze")
        formatted_status = format_enhanced_node_status(analyze_node, workflow, session)

        # Verify the formatted output has replacements
        assert "Test modification" in formatted_status

        # Verify the original workflow is unchanged
        assert workflow.workflow.tree["analyze"].goal == original_goal
        assert (
            "${{ inputs.task_description }}" in workflow.workflow.tree["analyze"].goal
        )
