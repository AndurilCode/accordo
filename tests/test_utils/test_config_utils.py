"""Tests for configuration utility functions."""

from src.accordo_mcp.config import ServerConfig
from src.accordo_mcp.models.config import WorkflowConfig
from src.accordo_mcp.utils.config_utils import get_workflow_config


class TestConfigUtils:
    """Test configuration utility functions."""

    def test_get_workflow_config_returns_config_instance(self):
        """Test that get_workflow_config returns a WorkflowConfig instance."""
        config = get_workflow_config()
        assert isinstance(config, WorkflowConfig)

    def test_get_workflow_config_default_behavior(self):
        """Test get_workflow_config with default settings."""
        config = get_workflow_config()
        assert config.local_state_file is False
        assert config.local_state_file_format == "MD"

    def test_get_workflow_config_with_server_config_enabled(self):
        """Test get_workflow_config with server_config for enabled state file."""
        server_config = ServerConfig(
            enable_local_state_file=True, local_state_file_format="JSON"
        )
        config = get_workflow_config(server_config)
        assert config.local_state_file is True
        assert config.local_state_file_format == "JSON"

    def test_get_workflow_config_with_server_config_disabled(self):
        """Test get_workflow_config with server_config for disabled state file."""
        server_config = ServerConfig(
            enable_local_state_file=False, local_state_file_format="MD"
        )
        config = get_workflow_config(server_config)
        assert config.local_state_file is False
        assert config.local_state_file_format == "MD"

    def test_get_workflow_config_no_server_config(self):
        """Test get_workflow_config when no server_config is provided."""
        config = get_workflow_config(None)
        assert config.local_state_file is False
        assert config.local_state_file_format == "MD"

    def test_get_workflow_config_multiple_calls(self):
        """Test that multiple calls to get_workflow_config work consistently."""
        config1 = get_workflow_config()
        config2 = get_workflow_config()

        # Both should be WorkflowConfig instances
        assert isinstance(config1, WorkflowConfig)
        assert isinstance(config2, WorkflowConfig)

        # Both should have the same values
        assert config1.local_state_file == config2.local_state_file
        assert config1.local_state_file_format == config2.local_state_file_format

    def test_get_workflow_config_multiple_calls_with_server_config(self):
        """Test multiple calls with server_config."""
        server_config = ServerConfig(
            enable_local_state_file=True, local_state_file_format="JSON"
        )
        config1 = get_workflow_config(server_config)
        config2 = get_workflow_config(server_config)

        assert config1.local_state_file is True
        assert config2.local_state_file is True
        assert config1.local_state_file_format == "JSON"
        assert config2.local_state_file_format == "JSON"

    def test_function_signature_and_docstring(self):
        """Test that the function has proper signature and documentation."""
        import inspect

        # Test function exists and is callable
        assert callable(get_workflow_config)

        # Test function signature
        sig = inspect.signature(get_workflow_config)
        assert len(sig.parameters) == 1  # Should have server_config parameter
        assert "server_config" in sig.parameters

        # Test return type annotation
        assert sig.return_annotation == WorkflowConfig

        # Test docstring exists
        assert get_workflow_config.__doc__ is not None
        assert "WorkflowConfig" in get_workflow_config.__doc__

    def test_backward_compatibility(self):
        """Test that the function maintains backward compatibility."""
        # Should work without any arguments (positional or keyword)
        config = get_workflow_config()
        assert isinstance(config, WorkflowConfig)

        # Should work with None explicitly
        config = get_workflow_config(None)
        assert isinstance(config, WorkflowConfig)

    def test_from_server_config_integration(self):
        """Test integration with WorkflowConfig.from_server_config method."""
        server_config = ServerConfig(
            enable_local_state_file=True, local_state_file_format="JSON"
        )

        # Direct call should match get_workflow_config result
        direct_config = WorkflowConfig.from_server_config(server_config)
        util_config = get_workflow_config(server_config)

        assert direct_config.local_state_file == util_config.local_state_file
        assert (
            direct_config.local_state_file_format == util_config.local_state_file_format
        )
