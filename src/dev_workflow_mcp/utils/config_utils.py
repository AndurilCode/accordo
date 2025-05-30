"""Configuration utility functions for workflow MCP server."""

from ..models.config import WorkflowConfig


def get_workflow_config() -> WorkflowConfig:
    """Get workflow configuration instance.
    
    Returns:
        WorkflowConfig: Configuration instance with environment variables loaded
    """
    return WorkflowConfig() 