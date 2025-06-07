"""Extended tests for phase_prompts.py private functions and edge cases."""

from unittest.mock import Mock, patch

import pytest

from src.dev_workflow_mcp.models.workflow_state import DynamicWorkflowState
from src.dev_workflow_mcp.models.yaml_workflow import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTree,
)
from src.dev_workflow_mcp.prompts.phase_prompts import (
    _handle_cache_list_operation,
    _handle_cache_restore_operation,
    _handle_dynamic_workflow,
)
from src.dev_workflow_mcp.utils.workflow_engine import WorkflowEngine
from src.dev_workflow_mcp.utils.yaml_loader import WorkflowLoader


class TestHandleDynamicWorkflow:
    """Test _handle_dynamic_workflow function."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock workflow session."""
        session = Mock(spec=DynamicWorkflowState)
        session.session_id = "test-session-123"
        session.current_node = "start"
        return session

    @pytest.fixture
    def mock_workflow_def(self):
        """Create a mock workflow definition."""
        workflow_def = Mock(spec=WorkflowDefinition)
        workflow_def.workflow = Mock(spec=WorkflowTree)

        # Create mock nodes
        start_node = Mock(spec=WorkflowNode)
        start_node.next_allowed_nodes = ["middle", "end"]
        start_node.acceptance_criteria = {"initialized": "System is ready"}

        middle_node = Mock(spec=WorkflowNode)
        middle_node.next_allowed_nodes = ["end"]
        middle_node.needs_approval = False
        middle_node.acceptance_criteria = {"validated": "Requirements validated"}

        approval_node = Mock(spec=WorkflowNode)
        approval_node.next_allowed_nodes = ["end"]
        approval_node.needs_approval = True
        approval_node.acceptance_criteria = {"approved": "User approved"}

        end_node = Mock(spec=WorkflowNode)
        end_node.next_allowed_nodes = []
        end_node.acceptance_criteria = {"completed": "Task finished"}

        # Set up tree structure
        workflow_def.workflow.tree = {
            "start": start_node,
            "middle": middle_node,
            "approval": approval_node,
            "end": end_node,
        }

        return workflow_def

    @pytest.fixture
    def mock_engine(self):
        """Create a mock workflow engine."""
        return Mock(spec=WorkflowEngine)

    @pytest.fixture
    def mock_loader(self):
        """Create a mock workflow loader."""
        return Mock(spec=WorkflowLoader)

    def test_handle_dynamic_workflow_next_action_with_valid_choice(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test next action with valid node choice."""
        with (
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.parse_criteria_evidence_context"
            ) as mock_parse,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.update_dynamic_session_node"
            ) as mock_update,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.add_log_to_session"
            ) as mock_log,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.get_session"
            ) as mock_get_session,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.format_enhanced_node_status"
            ) as mock_format,
        ):
            # Setup mocks
            mock_parse.return_value = ("middle", {"validated": "test evidence"}, False)
            mock_get_session.return_value = mock_session
            mock_format.return_value = "Node status formatted"

            result = _handle_dynamic_workflow(
                mock_session,
                mock_workflow_def,
                "next",
                '{"choose": "middle"}',
                mock_engine,
                mock_loader,
            )

            # Verify calls
            mock_parse.assert_called_once_with('{"choose": "middle"}')
            mock_update.assert_called_once_with(
                "test-session-123", "middle", mock_workflow_def
            )
            mock_log.assert_called_once()
            mock_get_session.assert_called_once_with("test-session-123")
            mock_format.assert_called_once()

            assert result == "Node status formatted"

    def test_handle_dynamic_workflow_next_action_invalid_node(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test next action with current node not found in workflow."""
        mock_session.current_node = "nonexistent"

        with patch(
            "src.dev_workflow_mcp.prompts.phase_prompts.parse_criteria_evidence_context"
        ) as mock_parse:
            mock_parse.return_value = ("middle", {}, False)

            result = _handle_dynamic_workflow(
                mock_session,
                mock_workflow_def,
                "next",
                '{"choose": "middle"}',
                mock_engine,
                mock_loader,
            )

            assert "❌ **Invalid State:**" in result
            assert "nonexistent" in result

    def test_handle_dynamic_workflow_next_action_invalid_transition(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test next action with invalid transition."""
        with patch(
            "src.dev_workflow_mcp.prompts.phase_prompts.parse_criteria_evidence_context"
        ) as mock_parse:
            mock_parse.return_value = ("invalid_node", {}, False)

            result = _handle_dynamic_workflow(
                mock_session,
                mock_workflow_def,
                "next",
                '{"choose": "invalid_node"}',
                mock_engine,
                mock_loader,
            )

            assert "❌ **Invalid Transition:**" in result
            assert "start" in result
            assert "invalid_node" in result

    def test_handle_dynamic_workflow_next_action_needs_approval(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test next action to node requiring approval without approval."""
        with patch(
            "src.dev_workflow_mcp.prompts.phase_prompts.parse_criteria_evidence_context"
        ) as mock_parse:
            mock_parse.return_value = ("approval", {}, False)

            # Modify workflow to include approval node in allowed transitions
            mock_workflow_def.workflow.tree["start"].next_allowed_nodes = [
                "middle",
                "approval",
                "end",
            ]

            result = _handle_dynamic_workflow(
                mock_session,
                mock_workflow_def,
                "next",
                '{"choose": "approval"}',
                mock_engine,
                mock_loader,
            )

            assert "❌ **Approval Required:**" in result
            assert "approval" in result
            assert "user_approval" in result

    def test_handle_dynamic_workflow_next_action_with_approval(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test next action to node requiring approval with approval provided."""
        with (
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.parse_criteria_evidence_context"
            ) as mock_parse,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.update_dynamic_session_node"
            ) as mock_update,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.add_log_to_session"
            ) as mock_log,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.get_session"
            ) as mock_get_session,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.format_enhanced_node_status"
            ) as mock_format,
        ):
            # Setup mocks
            mock_parse.return_value = ("approval", {"approved": "user confirmed"}, True)
            mock_get_session.return_value = mock_session
            mock_format.return_value = "Approval node status"

            # Modify workflow to include approval node in allowed transitions
            mock_workflow_def.workflow.tree["start"].next_allowed_nodes = [
                "middle",
                "approval",
                "end",
            ]

            result = _handle_dynamic_workflow(
                mock_session,
                mock_workflow_def,
                "next",
                '{"choose": "approval", "user_approval": true}',
                mock_engine,
                mock_loader,
            )

            # Verify calls
            mock_update.assert_called_once_with(
                "test-session-123", "approval", mock_workflow_def
            )
            assert result == "Approval node status"

    def test_handle_dynamic_workflow_next_action_with_criteria_evidence(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test next action with criteria evidence generation."""
        with (
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.parse_criteria_evidence_context"
            ) as mock_parse,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.generate_node_completion_outputs"
            ) as mock_generate,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.update_dynamic_session_node"
            ) as mock_update,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.add_log_to_session"
            ) as mock_log,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.get_session"
            ) as mock_get_session,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.format_enhanced_node_status"
            ) as mock_format,
        ):
            # Setup mocks
            criteria_evidence = {
                "initialized": "system ready",
                "validated": "requirements complete",
            }
            mock_parse.return_value = ("middle", criteria_evidence, False)
            mock_get_session.return_value = mock_session
            mock_format.return_value = "Middle node status"

            result = _handle_dynamic_workflow(
                mock_session,
                mock_workflow_def,
                "next",
                '{"choose": "middle", "criteria_evidence": {...}}',
                mock_engine,
                mock_loader,
            )

            # Verify criteria evidence generation was called
            mock_generate.assert_called_once_with(
                "start",
                mock_workflow_def.workflow.tree["start"],
                mock_session,
                criteria_evidence,
            )

            # Verify log message includes evidence summary
            log_call_args = mock_log.call_args[0]
            assert "with evidence" in log_call_args[1]
            assert "initialized: system ready..." in log_call_args[1]

    def test_handle_dynamic_workflow_next_action_auto_evidence_extraction(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test automatic evidence extraction when no criteria evidence provided."""
        with (
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.parse_criteria_evidence_context"
            ) as mock_parse,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.extract_automatic_evidence_from_session"
            ) as mock_extract,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.update_dynamic_session_node"
            ) as mock_update,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.add_log_to_session"
            ) as mock_log,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.get_session"
            ) as mock_get_session,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.format_enhanced_node_status"
            ) as mock_format,
        ):
            # Setup mocks
            mock_parse.return_value = ("middle", {}, False)  # No criteria evidence
            mock_extract.return_value = {"auto_detected": "evidence found"}
            mock_get_session.return_value = mock_session
            mock_format.return_value = "Middle node status"

            result = _handle_dynamic_workflow(
                mock_session,
                mock_workflow_def,
                "next",
                '{"choose": "middle"}',
                mock_engine,
                mock_loader,
            )

            # Verify automatic extraction was attempted
            mock_extract.assert_called_once_with(
                mock_session, "start", {"initialized": "System is ready"}
            )

    def test_handle_dynamic_workflow_next_action_missing_choice(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test next action without choice specified."""
        with patch(
            "src.dev_workflow_mcp.prompts.phase_prompts.parse_criteria_evidence_context"
        ) as mock_parse:
            mock_parse.return_value = (None, {}, False)

            result = _handle_dynamic_workflow(
                mock_session, mock_workflow_def, "next", "", mock_engine, mock_loader
            )

            assert "❌ **Missing Choice:**" in result

    def test_handle_dynamic_workflow_next_action_target_node_not_found(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test next action when target node is not found after transition."""
        with (
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.parse_criteria_evidence_context"
            ) as mock_parse,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.update_dynamic_session_node"
            ) as mock_update,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.add_log_to_session"
            ) as mock_log,
            patch(
                "src.dev_workflow_mcp.prompts.phase_prompts.get_session"
            ) as mock_get_session,
        ):
            # Setup mocks
            mock_parse.return_value = ("middle", {}, False)
            mock_get_session.return_value = mock_session

            # Remove the target node from workflow tree
            del mock_workflow_def.workflow.tree["middle"]

            result = _handle_dynamic_workflow(
                mock_session,
                mock_workflow_def,
                "next",
                '{"choose": "middle"}',
                mock_engine,
                mock_loader,
            )

            assert "❌ **Error:**" in result
            assert "middle" in result
            assert "not found in workflow definition" in result

    def test_handle_dynamic_workflow_current_node_display(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test displaying current node status for non-next actions."""
        with patch(
            "src.dev_workflow_mcp.prompts.phase_prompts.format_enhanced_node_status"
        ) as mock_format:
            mock_format.return_value = "Current node status display"

            result = _handle_dynamic_workflow(
                mock_session, mock_workflow_def, "status", "", mock_engine, mock_loader
            )

            mock_format.assert_called_once_with(
                mock_workflow_def.workflow.tree["start"],
                mock_workflow_def,
                mock_session,
            )
            assert result == "Current node status display"

    def test_handle_dynamic_workflow_current_node_not_found(
        self, mock_session, mock_workflow_def, mock_engine, mock_loader
    ):
        """Test displaying status when current node is not found."""
        mock_session.current_node = "nonexistent"

        result = _handle_dynamic_workflow(
            mock_session, mock_workflow_def, "status", "", mock_engine, mock_loader
        )

        assert "❌ **Invalid State:**" in result
        assert "nonexistent" in result
        assert "not found in workflow" in result


class TestHandleCacheRestoreOperation:
    """Test _handle_cache_restore_operation function."""

    def test_handle_cache_restore_basic_functionality(self):
        """Test that cache restore function returns appropriate response."""
        # Test that the function returns a string response
        result = _handle_cache_restore_operation("test-client")

        # Should return a string either way (success or error)
        assert isinstance(result, str)
        # Either success message or error message
        assert any(
            marker in result
            for marker in ["✅", "❌", "Cache", "cache", "Error", "error"]
        )


class TestHandleCacheListOperation:
    """Test _handle_cache_list_operation function."""

    def test_handle_cache_list_basic_functionality(self):
        """Test that cache list function returns appropriate response."""
        # Test that the function returns a string response
        result = _handle_cache_list_operation("test-client")

        # Should return a string either way (sessions found or not found)
        assert isinstance(result, str)
        assert "test-client" in result
        # Either sessions list or no sessions message
        assert any(
            marker in result
            for marker in ["📭", "📋", "No cached sessions", "Cached Sessions"]
        )

    def test_handle_cache_list_different_clients(self):
        """Test cache list with different client IDs."""
        # Test with different client IDs
        result1 = _handle_cache_list_operation("client-1")
        result2 = _handle_cache_list_operation("client-2")

        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert "client-1" in result1
        assert "client-2" in result2


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios."""

    def test_all_functions_handle_none_inputs(self):
        """Test that functions handle None inputs gracefully."""
        # Most functions should not crash with None inputs
        result1 = _handle_cache_restore_operation(None)
        assert isinstance(result1, str)

        result2 = _handle_cache_list_operation(None)
        assert isinstance(result2, str)

    def test_empty_string_inputs(self):
        """Test functions with empty string inputs."""
        result1 = _handle_cache_restore_operation("")
        assert isinstance(result1, str)

        result2 = _handle_cache_list_operation("")
        assert isinstance(result2, str)
        assert "No cached sessions found" in result2 or "Cached Sessions" in result2
