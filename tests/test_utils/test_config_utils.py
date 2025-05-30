"""Tests for configuration utility functions."""

import os
from unittest.mock import patch

from src.dev_workflow_mcp.models.config import WorkflowConfig
from src.dev_workflow_mcp.utils.config_utils import get_workflow_config


class TestConfigUtils:
    """Test configuration utility functions."""

    def test_get_workflow_config_returns_config_instance(self):
        """Test that get_workflow_config returns a WorkflowConfig instance."""
        config = get_workflow_config()
        assert isinstance(config, WorkflowConfig)

    def test_get_workflow_config_default_behavior(self):
        """Test get_workflow_config with default settings."""
        config = get_workflow_config()
        assert config.auto_approve_plans is False

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "true"})
    def test_get_workflow_config_with_env_var_true(self):
        """Test get_workflow_config when environment variable is true."""
        config = get_workflow_config()
        assert config.auto_approve_plans is True

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "false"})
    def test_get_workflow_config_with_env_var_false(self):
        """Test get_workflow_config when environment variable is false."""
        config = get_workflow_config()
        assert config.auto_approve_plans is False

    @patch.dict(os.environ, {}, clear=True)
    def test_get_workflow_config_no_env_vars(self):
        """Test get_workflow_config when no environment variables are set."""
        config = get_workflow_config()
        assert config.auto_approve_plans is False

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "TRUE"})
    def test_get_workflow_config_case_insensitive(self):
        """Test get_workflow_config with uppercase TRUE."""
        config = get_workflow_config()
        assert config.auto_approve_plans is True

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "invalid"})
    def test_get_workflow_config_invalid_env_value(self):
        """Test get_workflow_config with invalid environment variable."""
        config = get_workflow_config()
        assert config.auto_approve_plans is False

    def test_get_workflow_config_multiple_calls(self):
        """Test that multiple calls to get_workflow_config work consistently."""
        config1 = get_workflow_config()
        config2 = get_workflow_config()

        # Both should be WorkflowConfig instances
        assert isinstance(config1, WorkflowConfig)
        assert isinstance(config2, WorkflowConfig)

        # Both should have the same auto_approve_plans value
        assert config1.auto_approve_plans == config2.auto_approve_plans

    @patch.dict(os.environ, {"WORKFLOW_AUTO_APPROVE_PLANS": "true"})
    def test_get_workflow_config_multiple_calls_with_env(self):
        """Test multiple calls with environment variable set."""
        config1 = get_workflow_config()
        config2 = get_workflow_config()

        assert config1.auto_approve_plans is True
        assert config2.auto_approve_plans is True
        assert config1.auto_approve_plans == config2.auto_approve_plans

    def test_function_signature_and_docstring(self):
        """Test that the function has proper signature and documentation."""
        import inspect

        # Test function exists and is callable
        assert callable(get_workflow_config)

        # Test function signature
        sig = inspect.signature(get_workflow_config)
        assert len(sig.parameters) == 0  # Should have no parameters

        # Test return type annotation
        assert sig.return_annotation == WorkflowConfig

        # Test docstring exists
        assert get_workflow_config.__doc__ is not None
        assert "WorkflowConfig" in get_workflow_config.__doc__
