"""Configuration utility functions for workflow MCP server."""

from ..models.config import WorkflowConfig


def get_workflow_config(server_config=None) -> WorkflowConfig:
    """Get workflow configuration instance.

    Args:
        server_config: Optional ServerConfig instance with CLI-provided values.
                      If None, uses default values.

    Returns:
        WorkflowConfig: Configuration instance
    """
    if server_config:
        return WorkflowConfig.from_server_config(server_config)
    else:
        # Default configuration for backward compatibility
        return WorkflowConfig()
