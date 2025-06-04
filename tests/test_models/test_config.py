"""Tests for configuration models."""

import pytest
from pydantic import ValidationError

from src.dev_workflow_mcp.config import ServerConfig
from src.dev_workflow_mcp.models.config import WorkflowConfig


class TestWorkflowConfig:
    """Test WorkflowConfig model."""

    def test_default_configuration(self):
        """Test WorkflowConfig with default settings."""
        config = WorkflowConfig()
        assert config.local_state_file is False
        assert config.local_state_file_format == "MD"

    def test_from_server_config_enabled(self):
        """Test WorkflowConfig.from_server_config with enabled settings."""
        server_config = ServerConfig(
            enable_local_state_file=True, local_state_file_format="JSON"
        )
        config = WorkflowConfig.from_server_config(server_config)
        assert config.local_state_file is True
        assert config.local_state_file_format == "JSON"

    def test_from_server_config_disabled(self):
        """Test WorkflowConfig.from_server_config with disabled settings."""
        server_config = ServerConfig(
            enable_local_state_file=False, local_state_file_format="MD"
        )
        config = WorkflowConfig.from_server_config(server_config)
        assert config.local_state_file is False
        assert config.local_state_file_format == "MD"

    def test_explicit_value_creation(self):
        """Test creating WorkflowConfig with explicit values."""
        config = WorkflowConfig(local_state_file=True, local_state_file_format="JSON")
        assert config.local_state_file is True
        assert config.local_state_file_format == "JSON"

        config = WorkflowConfig(local_state_file=False, local_state_file_format="MD")
        assert config.local_state_file is False
        assert config.local_state_file_format == "MD"

    def test_serialization(self):
        """Test that WorkflowConfig can be serialized."""
        config = WorkflowConfig()
        data = config.model_dump()
        assert "local_state_file" in data
        assert "local_state_file_format" in data
        assert isinstance(data["local_state_file"], bool)
        assert isinstance(data["local_state_file_format"], str)

    def test_invalid_format_raises_error(self):
        """Test creating WorkflowConfig with invalid format raises error."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig(local_state_file_format="INVALID")

        error = exc_info.value
        assert "local_state_file_format must be 'MD' or 'JSON'" in str(error)

    def test_format_case_validation(self):
        """Test that format validation is case-insensitive during creation."""
        # These should work (case variations)
        config = WorkflowConfig(local_state_file_format="md")
        assert config.local_state_file_format == "MD"

        config = WorkflowConfig(local_state_file_format="json")
        assert config.local_state_file_format == "JSON"

        config = WorkflowConfig(local_state_file_format="Json")
        assert config.local_state_file_format == "JSON"


class TestWorkflowConfigLocalStateFileFormat:
    """Test WorkflowConfig local_state_file_format field specifically."""

    def test_default_local_state_file_format(self):
        """Test local_state_file_format defaults to MD."""
        config = WorkflowConfig()
        assert config.local_state_file_format == "MD"

    def test_explicit_md_format(self):
        """Test explicit MD format."""
        config = WorkflowConfig(local_state_file_format="MD")
        assert config.local_state_file_format == "MD"

    def test_explicit_json_format(self):
        """Test explicit JSON format."""
        config = WorkflowConfig(local_state_file_format="JSON")
        assert config.local_state_file_format == "JSON"

    def test_lowercase_formats(self):
        """Test that lowercase formats are normalized."""
        config = WorkflowConfig(local_state_file_format="md")
        assert config.local_state_file_format == "MD"

        config = WorkflowConfig(local_state_file_format="json")
        assert config.local_state_file_format == "JSON"

    def test_mixed_case_formats(self):
        """Test that mixed case formats are normalized."""
        config = WorkflowConfig(local_state_file_format="Md")
        assert config.local_state_file_format == "MD"

        config = WorkflowConfig(local_state_file_format="Json")
        assert config.local_state_file_format == "JSON"

    def test_invalid_format_validation(self):
        """Test that invalid formats raise ValidationError."""
        with pytest.raises(ValidationError):
            WorkflowConfig(local_state_file_format="INVALID")

        with pytest.raises(ValidationError):
            WorkflowConfig(local_state_file_format="xml")

        with pytest.raises(ValidationError):
            WorkflowConfig(local_state_file_format="")

    def test_serialization_includes_format(self):
        """Test that serialization includes local_state_file_format field."""
        config = WorkflowConfig()
        data = config.model_dump()
        assert "local_state_file_format" in data
        assert data["local_state_file_format"] == "MD"

    def test_serialization_with_json_format(self):
        """Test serialization when local_state_file_format is JSON."""
        config = WorkflowConfig(local_state_file_format="JSON")
        data = config.model_dump()
        assert data["local_state_file_format"] == "JSON"

    def test_field_description(self):
        """Test that local_state_file_format field has proper description."""
        field_info = WorkflowConfig.model_fields["local_state_file_format"]
        assert "MD" in field_info.description
        assert "JSON" in field_info.description
        assert "markdown" in field_info.description.lower()


class TestServerConfig:
    """Test ServerConfig class functionality."""

    def test_default_server_config(self):
        """Test ServerConfig with default settings."""
        config = ServerConfig()
        assert config.enable_local_state_file is False
        assert config.local_state_file_format == "MD"
        assert config.repository_path.exists()

    def test_server_config_with_local_state_enabled(self):
        """Test ServerConfig with local state file enabled."""
        config = ServerConfig(
            enable_local_state_file=True, local_state_file_format="JSON"
        )
        assert config.enable_local_state_file is True
        assert config.local_state_file_format == "JSON"

    def test_server_config_format_validation(self):
        """Test ServerConfig format validation."""
        with pytest.raises(ValueError) as exc_info:
            ServerConfig(local_state_file_format="INVALID")
        assert "must be 'MD' or 'JSON'" in str(exc_info.value)

    def test_server_config_sessions_dir(self):
        """Test ServerConfig sessions_dir property."""
        config = ServerConfig()
        sessions_dir = config.sessions_dir
        assert sessions_dir.name == "sessions"
        assert sessions_dir.parent.name == ".workflow-commander"

    def test_ensure_sessions_dir(self):
        """Test ServerConfig.ensure_sessions_dir method."""
        config = ServerConfig()
        # This should not raise an error
        result = config.ensure_sessions_dir()
        assert isinstance(result, bool)
