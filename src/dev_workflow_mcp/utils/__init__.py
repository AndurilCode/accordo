"""Utilities package for workflow management."""

from .markdown_generator import (
    export_session_report,
    format_workflow_state_for_display,
    generate_summary_markdown,
    generate_workflow_markdown,
)

# New session-based utilities
from .session_manager import (
    add_item_to_session,
    add_log_to_session,
    cleanup_completed_sessions,
    create_session,
    delete_session,
    export_session_to_markdown,
    get_all_sessions,
    get_or_create_session,
    get_session,
    get_session_stats,
    mark_item_completed_in_session,
    migrate_session_from_markdown,
    update_session,
    update_session_state,
)
from .state_manager import StateManager
from .validators import validate_project_config

__all__ = [
    # Legacy compatibility
    "StateManager",
    "validate_project_config",
    
    # Session management
    "get_session",
    "create_session", 
    "update_session",
    "delete_session",
    "get_all_sessions",
    "export_session_to_markdown",
    "get_or_create_session",
    "add_log_to_session",
    "update_session_state",
    "add_item_to_session",
    "mark_item_completed_in_session",
    "get_session_stats",
    "cleanup_completed_sessions",
    "migrate_session_from_markdown",
    
    # Markdown generation
    "generate_workflow_markdown",
    "format_workflow_state_for_display", 
    "generate_summary_markdown",
    "export_session_report",
]
