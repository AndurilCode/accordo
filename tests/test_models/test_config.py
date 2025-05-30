"""Tests for configuration models."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.dev_workflow_mcp.models.config import WorkflowConfig


class TestWorkflowConfig:
    """Test WorkflowConfig model."""

    def test_default_configuration(self):
        """Test WorkflowConfig with default settings."""
        config = WorkflowConfig()
        assert config.auto_approve_plans is False

    @patch.dict(os.environ, {}, clear=True)
    def test_no_environment_variable(self):
        """Test WorkflowConfig when no environment variable is set."""
        config = WorkflowConfig()
        assert config.auto_approve_plans is False

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "false"})
    def test_env_var_false(self):
        """Test WorkflowConfig when environment variable is explicitly false."""
        config = WorkflowConfig()
        assert config.auto_approve_plans is False

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "true"})
    def test_env_var_true(self):
        """Test WorkflowConfig when environment variable is true."""
        config = WorkflowConfig()
        assert config.auto_approve_plans is True

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "TRUE"})
    def test_env_var_uppercase_true(self):
        """Test WorkflowConfig when environment variable is uppercase TRUE."""
        config = WorkflowConfig()
        assert config.auto_approve_plans is True

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "False"})
    def test_env_var_mixed_case_false(self):
        """Test WorkflowConfig when environment variable is mixed case False."""
        config = WorkflowConfig()
        assert config.auto_approve_plans is False

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "yes"})
    def test_env_var_invalid_value(self):
        """Test WorkflowConfig with invalid environment variable value."""
        config = WorkflowConfig()
        # Only "true" (case insensitive) should be considered True
        assert config.auto_approve_plans is False

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": ""})
    def test_env_var_empty_string(self):
        """Test WorkflowConfig when environment variable is empty string."""
        config = WorkflowConfig()
        assert config.auto_approve_plans is False

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "1"})
    def test_env_var_numeric_value(self):
        """Test WorkflowConfig with numeric environment variable value."""
        config = WorkflowConfig()
        # Only "true" should be considered True
        assert config.auto_approve_plans is False

    def test_serialization(self):
        """Test that WorkflowConfig can be serialized."""
        config = WorkflowConfig()
        data = config.model_dump()
        assert "auto_approve_plans" in data
        assert isinstance(data["auto_approve_plans"], bool)

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "true"})
    def test_serialization_with_true(self):
        """Test serialization when auto_approve_plans is True."""
        config = WorkflowConfig()
        data = config.model_dump()
        assert data["auto_approve_plans"] is True

    def test_model_creation_with_explicit_value(self):
        """Test creating WorkflowConfig with explicit value."""
        config = WorkflowConfig(auto_approve_plans=True)
        assert config.auto_approve_plans is True

        config = WorkflowConfig(auto_approve_plans=False)
        assert config.auto_approve_plans is False

    def test_field_description(self):
        """Test that the field has proper description."""
        field_info = WorkflowConfig.model_fields["auto_approve_plans"]
        assert "WORKFLOW_AUTO_APPROVE_PLANS" in field_info.description
        assert "env var" in field_info.description.lower()

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "true"})
    def test_multiple_instances_same_env(self):
        """Test that multiple instances read the same environment variable."""
        config1 = WorkflowConfig()
        config2 = WorkflowConfig()
        assert config1.auto_approve_plans is True
        assert config2.auto_approve_plans is True
        assert config1.auto_approve_plans == config2.auto_approve_plans

    @patch.dict(os.environ, {"OTHER_ENV_VAR": "true"})
    def test_unrelated_env_var_ignored(self):
        """Test that unrelated environment variables don't affect config."""
        config = WorkflowConfig()
        assert config.auto_approve_plans is False


class TestWorkflowConfigLocalStateFileFormat:
    """Test WorkflowConfig local_state_file_format field."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_local_state_file_format(self):
        """Test local_state_file_format defaults to MD when no env var set."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "MD"

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE_FORMAT": "MD"})
    def test_env_var_md_format(self):
        """Test local_state_file_format reads MD from environment variable."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "MD"

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE_FORMAT": "JSON"})
    def test_env_var_json_format(self):
        """Test local_state_file_format reads JSON from environment variable."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "JSON"

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE_FORMAT": "md"})
    def test_env_var_lowercase_md(self):
        """Test local_state_file_format is case-insensitive for MD."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "MD"

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE_FORMAT": "json"})
    def test_env_var_lowercase_json(self):
        """Test local_state_file_format is case-insensitive for JSON."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "JSON"

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE_FORMAT": "Json"})
    def test_env_var_mixed_case_json(self):
        """Test local_state_file_format handles mixed case JSON."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "JSON"

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE_FORMAT": "INVALID"})
    def test_env_var_invalid_format_defaults_to_md(self):
        """Test local_state_file_format defaults to MD for invalid environment values."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "MD"

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE_FORMAT": "xml"})
    def test_env_var_unsupported_format_defaults_to_md(self):
        """Test local_state_file_format defaults to MD for unsupported environment values."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "MD"

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE_FORMAT": ""})
    def test_env_var_empty_string_defaults_to_md(self):
        """Test local_state_file_format defaults to MD for empty environment string."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "MD"

    def test_serialization_includes_local_state_file_format(self):
        """Test that serialization includes local_state_file_format field."""
        config = WorkflowConfig()
        data = config.model_dump()
        assert "local_state_file_format" in data
        assert data["local_state_file_format"] == "MD"

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE_FORMAT": "JSON"})
    def test_serialization_with_json_format(self):
        """Test serialization when local_state_file_format is JSON."""
        config = WorkflowConfig()
        data = config.model_dump()
        assert data["local_state_file_format"] == "JSON"

    def test_explicit_value_creation(self):
        """Test creating WorkflowConfig with explicit local_state_file_format value."""
        config = WorkflowConfig(local_state_file_format="JSON")
        assert config.local_state_file_format == "JSON"

        config = WorkflowConfig(local_state_file_format="MD")
        assert config.local_state_file_format == "MD"

    def test_explicit_invalid_value_raises_error(self):
        """Test creating WorkflowConfig with explicit invalid value raises error."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig(local_state_file_format="INVALID")

        error = exc_info.value
        assert "local_state_file_format must be 'MD' or 'JSON'" in str(error)

    def test_field_description(self):
        """Test that local_state_file_format field has proper description."""
        field_info = WorkflowConfig.model_fields["local_state_file_format"]
        assert "WORKFLOW_LOCAL_STATE_FILE_FORMAT" in field_info.description
        assert "env var" in field_info.description.lower()
        assert "MD" in field_info.description
        assert "JSON" in field_info.description

    @patch.dict(os.environ, {"WORKFLOW_LOCAL_STATE_FILE_FORMAT": "JSON"})
    def test_multiple_instances_same_env_format(self):
        """Test that multiple instances read the same format environment variable."""
        config1 = WorkflowConfig()
        config2 = WorkflowConfig()
        assert config1.local_state_file_format == "JSON"
        assert config2.local_state_file_format == "JSON"
        assert config1.local_state_file_format == config2.local_state_file_format

    @patch.dict(os.environ, {"OTHER_ENV_VAR": "JSON"})
    def test_unrelated_env_var_ignored_format(self):
        """Test that unrelated environment variables don't affect local_state_file_format."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "MD"  # Should be default
