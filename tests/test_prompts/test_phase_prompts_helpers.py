"""Tests for phase_prompts.py helper functions to improve code coverage."""

from unittest.mock import Mock, patch

import pytest

from src.accordo_workflow_mcp.models.yaml_workflow import (
    WorkflowDefinition,
    WorkflowNode,
)
from src.accordo_workflow_mcp.prompts.phase_prompts import (
    _create_discovery_required_message,
    _determine_session_handling,
    # Evidence extraction functions
    _extract_automatic_evidence_from_session,
    _extract_criterion_evidence,
    _extract_evidence_from_activity_patterns,
    _extract_evidence_from_log_entry,
    _extract_evidence_from_tool_patterns,
    _extract_workflow_name_from_context,
    _extract_workflow_name_only,
    # Formatting functions
    _format_yaml_error_guidance,
    _get_criterion_keywords,
    _handle_cache_list_operation,
    _handle_cache_restore_operation,
    _handle_get_operation,
    _handle_update_operation,
    _handle_workflow_not_found_error,
    _looks_like_yaml,
    # Context parsing functions
    _parse_criteria_evidence_context,
    _parse_pure_yaml,
    _parse_standard_format,
    # Helper functions
    _sanitize_workflow_guidance_parameters,
    _sanitize_workflow_state_parameters,
    _try_restore_workflow_definition,
    _validate_and_reformat_yaml,
    format_enhanced_node_status,
    # YAML parsing functions
    parse_and_validate_yaml_context,
    # Session resolution
    resolve_session_context,
    # Validation functions
    validate_task_description,
)


class TestSessionResolution:
    """Test session resolution functions."""

    def test_resolve_session_context_with_explicit_session_id(self):
        """Test resolve_session_context with explicit session ID."""
        mock_ctx = Mock()
        mock_ctx.client_id = "test-client"

        session_id, client_id = resolve_session_context("session-123", "", mock_ctx)

        assert session_id == "session-123"
        assert client_id == "test-client"

    def test_resolve_session_context_with_context_session_id(self):
        """Test resolve_session_context with session ID in context."""
        mock_ctx = Mock()
        mock_ctx.client_id = "test-client"

        with patch(
            "src.accordo_workflow_mcp.prompts.phase_prompts.extract_session_id_from_context",
            return_value="abc-456",
        ):
            session_id, client_id = resolve_session_context(
                "", "session_id: abc-456", mock_ctx
            )

            assert session_id == "abc-456"
            assert client_id == "test-client"

    def test_resolve_session_context_no_session(self):
        """Test resolve_session_context with no session information."""
        mock_ctx = Mock()
        mock_ctx.client_id = "test-client"

        with patch(
            "src.accordo_workflow_mcp.prompts.phase_prompts.extract_session_id_from_context",
            return_value=None,
        ):
            session_id, client_id = resolve_session_context("", "", mock_ctx)

            assert session_id is None
            assert client_id == "test-client"

    def test_resolve_session_context_with_none_context(self):
        """Test resolve_session_context with None context."""
        session_id, client_id = resolve_session_context("", "", None)

        assert session_id is None
        assert client_id == "default"

    def test_resolve_session_context_with_field_objects(self):
        """Test resolve_session_context handling Field objects."""
        mock_session_id = Mock()
        mock_session_id.default = "field-session-123"

        mock_context = Mock()
        mock_context.default = "field-context"

        mock_ctx = Mock()
        mock_ctx.client_id = "test-client"

        session_id, client_id = resolve_session_context(
            mock_session_id, mock_context, mock_ctx
        )

        assert session_id == "field-session-123"
        assert client_id == "test-client"


class TestValidationFunctions:
    """Test validation functions."""

    def test_validate_task_description_valid_formats(self):
        """Test validate_task_description with valid formats."""
        valid_descriptions = [
            "Add: user authentication",
            "Fix: memory leak",
            "Update: documentation",
            "Remove: deprecated code",
            "Test: integration workflow",
        ]

        for description in valid_descriptions:
            result = validate_task_description(description)
            assert result == description

    def test_validate_task_description_invalid_none(self):
        """Test validate_task_description with None."""
        with pytest.raises(
            ValueError, match="Task description must be a non-empty string"
        ):
            validate_task_description(None)

    def test_validate_task_description_invalid_non_string(self):
        """Test validate_task_description with non-string."""
        with pytest.raises(ValueError, match="Task description must be a string"):
            validate_task_description(123)

    def test_validate_task_description_empty_string(self):
        """Test validate_task_description with empty string."""
        with pytest.raises(
            ValueError, match="Task description must be a non-empty string"
        ):
            validate_task_description("")

    def test_validate_task_description_no_colon(self):
        """Test validate_task_description without colon."""
        with pytest.raises(
            ValueError, match="must follow the format 'Action: Brief description'"
        ):
            validate_task_description("Add user authentication")

    def test_validate_task_description_empty_action(self):
        """Test validate_task_description with empty action."""
        with pytest.raises(
            ValueError, match="must follow the format 'Action: Brief description'"
        ):
            validate_task_description(": description")

    def test_validate_task_description_lowercase_action(self):
        """Test validate_task_description with lowercase action."""
        with pytest.raises(
            ValueError, match="must follow the format 'Action: Brief description'"
        ):
            validate_task_description("add: user authentication")

    def test_validate_task_description_non_alpha_action(self):
        """Test validate_task_description with non-alphabetic action."""
        with pytest.raises(
            ValueError, match="must follow the format 'Action: Brief description'"
        ):
            validate_task_description("Add123: user authentication")

    def test_validate_task_description_no_space_after_colon(self):
        """Test validate_task_description without space after colon."""
        with pytest.raises(
            ValueError, match="must follow the format 'Action: Brief description'"
        ):
            validate_task_description("Add:user authentication")

    def test_validate_task_description_empty_details(self):
        """Test validate_task_description with empty details."""
        with pytest.raises(
            ValueError, match="must follow the format 'Action: Brief description'"
        ):
            validate_task_description("Add: ")


class TestYAMLParsingFunctions:
    """Test YAML parsing functions."""

    def test_parse_and_validate_yaml_context_standard_format(self):
        """Test parse_and_validate_yaml_context with standard format."""
        context = """workflow: Test Workflow
yaml: name: Test Workflow
description: A test workflow
workflow:
  goal: Test goal
  root: start
  tree:
    start:
      goal: Start task
      next_allowed_nodes: []"""

        workflow_name, yaml_content, error_msg = parse_and_validate_yaml_context(
            context
        )

        assert workflow_name == "Test Workflow"
        assert yaml_content is not None
        assert "name: Test Workflow" in yaml_content
        assert error_msg is None

    def test_parse_and_validate_yaml_context_pure_yaml(self):
        """Test parse_and_validate_yaml_context with pure YAML."""
        yaml_context = """name: Pure YAML Workflow
description: A workflow in pure YAML
workflow:
  goal: Pure YAML goal
  root: start
  tree:
    start:
      goal: Start task
      next_allowed_nodes: []"""

        workflow_name, yaml_content, error_msg = parse_and_validate_yaml_context(
            yaml_context
        )

        assert workflow_name == "Pure YAML Workflow"
        assert yaml_content == yaml_context
        assert error_msg is None

    def test_parse_and_validate_yaml_context_workflow_name_only(self):
        """Test parse_and_validate_yaml_context with workflow name only."""
        context = "workflow: Test Workflow Only"

        workflow_name, yaml_content, error_msg = parse_and_validate_yaml_context(
            context
        )

        # The function returns None for workflow name when only name is provided without yaml content
        assert workflow_name is None
        assert yaml_content is None
        assert "Could not extract workflow name from YAML content" in error_msg

    def test_parse_and_validate_yaml_context_invalid_format(self):
        """Test parse_and_validate_yaml_context with invalid format."""
        context = "invalid format without workflow marker"

        workflow_name, yaml_content, error_msg = parse_and_validate_yaml_context(
            context
        )

        assert workflow_name is None
        assert yaml_content is None
        assert "Unrecognized context format" in error_msg

    def test_parse_standard_format_success(self):
        """Test _parse_standard_format with valid input."""
        context = """workflow: Standard Format Test
yaml: name: Standard Format Test
workflow:
  goal: Test
  root: start"""

        name, yaml = _parse_standard_format(context)

        assert name == "Standard Format Test"
        assert "name: Standard Format Test" in yaml

    def test_parse_standard_format_failure(self):
        """Test _parse_standard_format with invalid input."""
        context = "invalid format"

        name, yaml = _parse_standard_format(context)

        assert name is None
        assert yaml is None

    def test_parse_pure_yaml_success(self):
        """Test _parse_pure_yaml with valid YAML."""
        yaml_content = """name: Pure YAML Test
workflow:
  goal: Test goal"""

        name, yaml = _parse_pure_yaml(yaml_content)

        assert name == "Pure YAML Test"
        assert yaml == yaml_content

    def test_parse_pure_yaml_failure(self):
        """Test _parse_pure_yaml with invalid YAML."""
        invalid_yaml = "invalid: yaml: content:"

        name, yaml = _parse_pure_yaml(invalid_yaml)

        assert name is None
        assert yaml is None

    def test_extract_workflow_name_only(self):
        """Test _extract_workflow_name_only."""
        context = "workflow: Extracted Name"

        name = _extract_workflow_name_only(context)

        assert name == "Extracted Name"

    def test_looks_like_yaml_true(self):
        """Test _looks_like_yaml returns True for YAML-like content."""
        yaml_content = "name: Test\nworkflow:\n  goal: Test goal"

        assert _looks_like_yaml(yaml_content) is True

    def test_looks_like_yaml_false(self):
        """Test _looks_like_yaml returns False for non-YAML content."""
        non_yaml = "this is just plain text without yaml indicators"

        assert _looks_like_yaml(non_yaml) is False

    def test_validate_and_reformat_yaml_valid(self):
        """Test _validate_and_reformat_yaml with valid YAML."""
        valid_yaml = """name: Valid YAML
workflow:
  tree:
    start:
      goal: Start"""

        result = _validate_and_reformat_yaml(valid_yaml)

        assert result is not None
        assert "name: Valid YAML" in result

    def test_validate_and_reformat_yaml_invalid(self):
        """Test _validate_and_reformat_yaml with invalid YAML."""
        invalid_yaml = "invalid: yaml: structure"

        result = _validate_and_reformat_yaml(invalid_yaml)

        assert result is None


class TestContextParsingFunctions:
    """Test context parsing functions."""

    def test_parse_criteria_evidence_context_json_format(self):
        """Test _parse_criteria_evidence_context with JSON format."""
        json_context = '{"choose": "test_node", "criteria_evidence": {"test_criterion": "test evidence"}, "user_approval": true}'

        choice, evidence, approval = _parse_criteria_evidence_context(json_context)

        assert choice == "test_node"
        assert evidence == {"test_criterion": "test evidence"}
        assert approval is True

    def test_parse_criteria_evidence_context_legacy_format(self):
        """Test _parse_criteria_evidence_context with legacy format."""
        legacy_context = "choose: legacy_node"

        with patch(
            "src.accordo_workflow_mcp.prompts.phase_prompts.extract_choice_from_context",
            return_value="legacy_node",
        ):
            choice, evidence, approval = _parse_criteria_evidence_context(
                legacy_context
            )

            assert choice == "legacy_node"
            assert evidence is None
            assert approval is False

    def test_parse_criteria_evidence_context_invalid_json(self):
        """Test _parse_criteria_evidence_context with invalid JSON."""
        invalid_json = '{"choose": "test", invalid json'

        choice, evidence, approval = _parse_criteria_evidence_context(invalid_json)

        assert choice is None
        assert evidence is None
        assert approval is False

    def test_parse_criteria_evidence_context_empty(self):
        """Test _parse_criteria_evidence_context with empty input."""
        choice, evidence, approval = _parse_criteria_evidence_context("")

        assert choice is None
        assert evidence is None
        assert approval is False


class TestEvidenceExtractionFunctions:
    """Test evidence extraction functions."""

    def test_extract_automatic_evidence_from_session(self):
        """Test _extract_automatic_evidence_from_session."""
        mock_session = Mock()
        mock_session.log = [
            "Analysis completed successfully",
            "Requirements gathered",
            "Testing performed",
        ]

        acceptance_criteria = {
            "analysis_complete": "Complete analysis",
            "requirements_clear": "Clear requirements",
        }

        evidence = _extract_automatic_evidence_from_session(
            mock_session, "test_node", acceptance_criteria
        )

        assert isinstance(evidence, dict)
        assert len(evidence) <= len(acceptance_criteria)

    def test_extract_criterion_evidence(self):
        """Test _extract_criterion_evidence."""
        recent_logs = [
            "Analysis phase completed with thorough investigation",
            "Requirements documented in detail",
        ]
        mock_session = Mock()
        mock_session.execution_context = {}

        evidence = _extract_criterion_evidence(
            "analysis_complete",
            "Complete analysis",
            recent_logs,
            mock_session,
            "test_node",
        )

        # Evidence might be None or a string depending on log content
        assert evidence is None or isinstance(evidence, str)

    def test_get_criterion_keywords(self):
        """Test _get_criterion_keywords."""
        keywords = _get_criterion_keywords(
            "analysis_complete", "Complete thorough analysis of requirements"
        )

        assert isinstance(keywords, list)
        assert "analysis_complete" in keywords
        assert "analysis complete" in keywords
        assert "analysiscomplete" in keywords

    def test_extract_evidence_from_log_entry(self):
        """Test _extract_evidence_from_log_entry."""
        log_entry = "[14:30:25] Performed detailed analysis of the codebase structure"

        evidence = _extract_evidence_from_log_entry(
            log_entry, "analysis", "Analysis description"
        )

        assert evidence is not None
        assert "Session activity:" in evidence
        assert "Performed detailed analysis" in evidence

    def test_extract_evidence_from_log_entry_filtered(self):
        """Test _extract_evidence_from_log_entry filters system logs."""
        system_log = "[14:30:25] Transitioned from analyze to blueprint"

        evidence = _extract_evidence_from_log_entry(
            system_log, "analysis", "Analysis description"
        )

        assert evidence is None

    def test_extract_evidence_from_activity_patterns(self):
        """Test _extract_evidence_from_activity_patterns."""
        recent_logs = [
            "Analyzed codebase structure",
            "Reviewed test coverage",
            "Examined database schema",
        ]

        evidence = _extract_evidence_from_activity_patterns(
            recent_logs, "analysis", "Analysis description", "analyze_node"
        )

        assert evidence is not None
        assert "activities in analyze_node phase" in evidence

    def test_extract_evidence_from_tool_patterns(self):
        """Test _extract_evidence_from_tool_patterns."""
        recent_logs = [
            "Implemented new feature functionality",
            "Tested integration endpoints",
            "Documented API changes",
        ]

        evidence = _extract_evidence_from_tool_patterns(
            recent_logs, "implementation", "Implementation description"
        )

        assert evidence is not None
        assert (
            "implementation" in evidence
            or "testing" in evidence
            or "documentation" in evidence
        )


class TestFormattingFunctions:
    """Test formatting functions."""

    def test_format_yaml_error_guidance(self):
        """Test _format_yaml_error_guidance."""
        error_msg = "Invalid YAML structure"
        workflow_name = "Test Workflow"

        result = _format_yaml_error_guidance(error_msg, workflow_name)

        assert "❌ **YAML Format Error:**" in result
        assert error_msg in result
        assert workflow_name in result
        assert "EXPECTED FORMAT:" in result

    def test_format_enhanced_node_status(self):
        """Test format_enhanced_node_status."""
        mock_node = Mock(spec=WorkflowNode)
        mock_node.goal = "Test goal"
        mock_node.acceptance_criteria = {"test": "test criteria"}
        mock_node.next_allowed_nodes = ["next_node"]

        mock_workflow = Mock(spec=WorkflowDefinition)
        mock_workflow.workflow = Mock()
        mock_workflow.workflow.tree = {"next_node": Mock()}

        mock_session = Mock()
        mock_session.session_id = "test-session-123"
        mock_session.inputs = {}

        with (
            patch(
                "src.accordo_workflow_mcp.prompts.phase_prompts.analyze_node_from_schema"
            ) as mock_analyze,
            patch(
                "src.accordo_workflow_mcp.prompts.phase_prompts.get_available_transitions"
            ) as mock_transitions,
            patch(
                "src.accordo_workflow_mcp.prompts.phase_prompts.export_session_to_markdown"
            ) as mock_export,
        ):
            mock_analyze.return_value = {
                "goal": "Test goal",
                "acceptance_criteria": {"test": "test criteria"},
            }
            mock_transitions.return_value = [{"name": "next_node", "goal": "Next goal"}]
            mock_export.return_value = "# Session State"

            result = format_enhanced_node_status(mock_node, mock_workflow, mock_session)

            assert "Test goal" in result
            assert "ACCEPTANCE CRITERIA:" in result
            assert "Available Next Steps:" in result


class TestHelperFunctions:
    """Test helper functions."""

    def test_sanitize_workflow_guidance_parameters(self):
        """Test _sanitize_workflow_guidance_parameters."""
        # Test with normal strings
        action, context, session_id, options = _sanitize_workflow_guidance_parameters(
            "start", "test context", "session-123", "test options"
        )

        assert action == "start"
        assert context == "test context"
        assert session_id == "session-123"
        assert options == "test options"

    def test_sanitize_workflow_guidance_parameters_with_field_objects(self):
        """Test _sanitize_workflow_guidance_parameters with Field objects."""
        mock_action = Mock()
        mock_action.default = "start"

        mock_context = Mock()
        mock_context.default = "test context"

        action, context, session_id, options = _sanitize_workflow_guidance_parameters(
            mock_action, mock_context, "", ""
        )

        assert action == "start"
        assert context == "test context"
        assert session_id == ""
        assert options == ""

    def test_sanitize_workflow_guidance_parameters_with_none(self):
        """Test _sanitize_workflow_guidance_parameters with None values."""
        action, context, session_id, options = _sanitize_workflow_guidance_parameters(
            None, None, None, None
        )

        assert action == ""
        assert context == ""
        assert session_id == ""
        assert options == ""

    @patch("src.accordo_workflow_mcp.prompts.phase_prompts.get_session")
    @patch("src.accordo_workflow_mcp.prompts.phase_prompts.get_session_type")
    def test_determine_session_handling_with_explicit_session(
        self, mock_get_type, mock_get_session
    ):
        """Test _determine_session_handling with explicit session ID."""
        mock_session = Mock()
        mock_get_session.return_value = mock_session

        session_id, session, session_type = _determine_session_handling(
            "explicit-123", "client-1", "test task"
        )

        assert session_id == "explicit-123"
        assert session == mock_session
        assert session_type == "dynamic"

    @patch("src.accordo_workflow_mcp.prompts.phase_prompts._get_latest_active_session")
    def test_determine_session_handling_with_latest_active_session(
        self, mock_get_latest
    ):
        """Test _determine_session_handling with latest active session."""
        mock_session = Mock()
        mock_session.session_id = "latest-session-456"
        mock_get_latest.return_value = ("latest-session-456", mock_session)

        session_id, session, session_type = _determine_session_handling(
            None, "client-1", "test task"
        )

        assert session_id == "latest-session-456"
        assert session == mock_session
        assert session_type == "dynamic"

    @patch("src.accordo_workflow_mcp.prompts.phase_prompts._get_latest_active_session")
    def test_determine_session_handling_no_session(self, mock_get_latest):
        """Test _determine_session_handling with no active session."""
        mock_get_latest.return_value = (None, None)

        session_id, session, session_type = _determine_session_handling(
            None, "default", "test task"
        )

        assert session_id is None
        assert session is None
        assert session_type is None

    @patch(
        "src.accordo_workflow_mcp.prompts.phase_prompts.get_dynamic_session_workflow_def"
    )
    def test_try_restore_workflow_definition_success(self, mock_get_def):
        """Test _try_restore_workflow_definition success case."""
        mock_session = Mock()
        mock_session.workflow_name = "Test Workflow"

        mock_config = Mock()
        mock_config.workflows_dir = "/test/workflows"

        mock_workflow_def = Mock()
        mock_get_def.return_value = mock_workflow_def

        with patch(
            "src.accordo_workflow_mcp.utils.session_manager._restore_workflow_definition"
        ):
            result = _try_restore_workflow_definition(
                mock_session, "session-123", mock_config
            )

            assert result == mock_workflow_def

    def test_try_restore_workflow_definition_no_workflow_name(self):
        """Test _try_restore_workflow_definition with no workflow name."""
        mock_session = Mock()
        mock_session.workflow_name = None

        result = _try_restore_workflow_definition(mock_session, "session-123", None)

        assert result is None

    def test_try_restore_workflow_definition_exception(self):
        """Test _try_restore_workflow_definition with exception."""
        mock_session = Mock()
        mock_session.workflow_name = "Test Workflow"

        with patch(
            "src.accordo_workflow_mcp.utils.session_manager._restore_workflow_definition",
            side_effect=Exception("Test error"),
        ):
            result = _try_restore_workflow_definition(mock_session, "session-123", None)

            assert result is None

    def test_create_discovery_required_message(self):
        """Test _create_discovery_required_message."""
        result = _create_discovery_required_message("Test task", "Test context")

        assert "❌ **No Active Workflow Session**" in result
        assert "Test context" in result
        assert "Test task" in result
        assert "workflow_discovery" in result

    def test_extract_workflow_name_from_context(self):
        """Test _extract_workflow_name_from_context."""
        context = "workflow: Extracted Workflow\nother: content"

        result = _extract_workflow_name_from_context(context)

        assert result == "Extracted Workflow"

    def test_extract_workflow_name_from_context_no_workflow(self):
        """Test _extract_workflow_name_from_context with no workflow."""
        context = "no workflow here"

        result = _extract_workflow_name_from_context(context)

        assert result is None

    def test_handle_workflow_not_found_error(self):
        """Test _handle_workflow_not_found_error."""
        result = _handle_workflow_not_found_error("Missing Workflow", "Test task")

        assert "❌ **Workflow Not Found:** Missing Workflow" in result
        assert "Test task" in result
        assert "workflow_discovery" in result

    def test_sanitize_workflow_state_parameters(self):
        """Test _sanitize_workflow_state_parameters."""
        operation, updates, session_id = _sanitize_workflow_state_parameters(
            "get", '{"test": "value"}', "session-123"
        )

        assert operation == "get"
        assert updates == '{"test": "value"}'
        assert session_id == "session-123"

    @patch("src.accordo_workflow_mcp.prompts.phase_prompts.get_session")
    @patch("src.accordo_workflow_mcp.prompts.phase_prompts.add_session_id_to_response")
    @patch(
        "src.accordo_workflow_mcp.prompts.phase_prompts.get_dynamic_session_workflow_def"
    )
    @patch("src.accordo_workflow_mcp.prompts.phase_prompts.get_workflow_summary")
    @patch("src.accordo_workflow_mcp.prompts.phase_prompts.export_session_to_markdown")
    def test_handle_get_operation_with_session_id(
        self,
        mock_export,
        mock_summary,
        mock_get_def,
        mock_add_response,
        mock_get_session,
    ):
        """Test _handle_get_operation with explicit session ID."""
        mock_session = Mock()
        mock_session.current_node = "test_node"
        mock_get_session.return_value = mock_session

        mock_get_def.return_value = Mock()
        mock_summary.return_value = {
            "name": "Test Workflow",
            "root_node": "start",
            "all_nodes": ["test_node", "other_node"],
            "total_nodes": 2,
            "decision_nodes": ["test_node"],
            "terminal_nodes": ["other_node"],
        }
        mock_export.return_value = "# Session Export"
        mock_add_response.return_value = "Response with session"

        result = _handle_get_operation("session-123", "client-1", None)

        assert result == "Response with session"
        mock_get_session.assert_called_once_with("session-123")

    @patch("src.accordo_workflow_mcp.prompts.phase_prompts.add_session_id_to_response")
    @patch("src.accordo_workflow_mcp.prompts.phase_prompts.update_dynamic_session_node")
    @patch(
        "src.accordo_workflow_mcp.prompts.phase_prompts.get_dynamic_session_workflow_def"
    )
    def test_handle_update_operation_success(
        self, mock_get_def, mock_update, mock_add_response
    ):
        """Test _handle_update_operation with valid updates."""
        mock_add_response.return_value = "Update successful"
        mock_get_def.return_value = Mock()  # Mock workflow definition

        result = _handle_update_operation(
            '{"node": "test_node", "status": "RUNNING"}', "session-123", "client-1"
        )

        assert result == "Update successful"

    def test_handle_update_operation_invalid_json(self):
        """Test _handle_update_operation with invalid JSON."""
        with patch(
            "src.accordo_workflow_mcp.prompts.phase_prompts.add_session_id_to_response",
            return_value="JSON error",
        ):
            result = _handle_update_operation("invalid json", "session-123", "client-1")

            assert result == "JSON error"

    def test_handle_cache_restore_operation_success(self):
        """Test _handle_cache_restore_operation success."""
        with patch(
            "src.accordo_workflow_mcp.services.get_session_sync_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.restore_sessions_from_cache.return_value = 3
            mock_get_service.return_value = mock_service

            result = _handle_cache_restore_operation("client-1")

            assert "Successfully restored 3 workflow session(s)" in result

    def test_handle_cache_restore_operation_no_sessions(self):
        """Test _handle_cache_restore_operation with no sessions."""
        with patch(
            "src.accordo_workflow_mcp.services.get_session_sync_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.restore_sessions_from_cache.return_value = 0
            mock_get_service.return_value = mock_service

            result = _handle_cache_restore_operation("client-1")

            assert "No workflow sessions found in cache" in result

    def test_handle_cache_list_operation_success(self):
        """Test _handle_cache_list_operation success."""
        with patch(
            "src.accordo_workflow_mcp.services.get_session_sync_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_sessions = [
                {
                    "session_id": "session-123",
                    "workflow_name": "Test Workflow",
                    "status": "RUNNING",
                    "current_node": "start",
                    "task_description": "Test task",
                    "created_at": "2024-01-01T12:00:00Z",
                    "last_updated": "2024-01-01T12:30:00Z",
                }
            ]
            mock_service.list_cached_sessions.return_value = mock_sessions
            mock_get_service.return_value = mock_service

            result = _handle_cache_list_operation("client-1")

            assert "Cached Sessions for client 'client-1'" in result
            assert "session-" in result  # Check for part of session ID
            assert "Test Workflow" in result

    def test_handle_cache_list_operation_no_sessions(self):
        """Test _handle_cache_list_operation with no sessions."""
        with patch(
            "src.accordo_workflow_mcp.services.get_session_sync_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.list_cached_sessions.return_value = []
            mock_get_service.return_value = mock_service

            result = _handle_cache_list_operation("client-1")

            assert "No cached sessions found" in result
