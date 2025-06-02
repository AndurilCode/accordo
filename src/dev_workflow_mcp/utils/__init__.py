"""Utilities package for workflow management."""

from .config_utils import get_workflow_config
from .markdown_generator import (
    export_session_report,
    format_workflow_state_for_display,
    generate_summary_markdown,
    generate_workflow_markdown,
)
from .path_utils import (
    get_project_config_path,
    get_workflow_dir,
    get_workflow_state_path,
    migrate_config_file,
    migrate_workflow_state_files,
)

# New session-based utilities
from .session_manager import (
    add_item_to_session,
    add_log_to_session,
    cleanup_completed_sessions,
    delete_session,
    export_session_to_markdown,
    get_all_sessions,
    get_session,
    get_session_stats,
    mark_item_completed_in_session,
    update_session,
)
from .state_manager import StateManager
from .validators import validate_project_config, validate_project_files

__all__ = [
    # Legacy compatibility
    "StateManager",
    "validate_project_config",
    "validate_project_files",
    # Configuration
    "get_workflow_config",
    # Session management
    "get_session",
    "update_session",
    "delete_session",
    "get_all_sessions",
    "export_session_to_markdown",
    "add_log_to_session",
    "add_item_to_session",
    "mark_item_completed_in_session",
    "get_session_stats",
    "cleanup_completed_sessions",
    # Path utilities
    "get_workflow_dir",
    "get_project_config_path",
    "get_workflow_state_path",
    "migrate_config_file",
    "migrate_workflow_state_files",
    # Markdown generation
    "generate_workflow_markdown",
    "format_workflow_state_for_display",
    "generate_summary_markdown",
    "export_session_report",
]
