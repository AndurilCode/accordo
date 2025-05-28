"""Utilities package for workflow management."""

from .state_manager import StateManager
from .validators import validate_project_config, validate_workflow_state

# New session-based utilities
from .session_manager import (
    get_session,
    create_session,
    update_session,
    delete_session,
    get_all_sessions,
    export_session_to_markdown,
    get_or_create_session,
    add_log_to_session,
    update_session_state,
    add_item_to_session,
    mark_item_completed_in_session,
    get_session_stats,
    cleanup_completed_sessions,
    migrate_session_from_markdown,
)

from .markdown_generator import (
    generate_workflow_markdown,
    format_workflow_state_for_display,
    generate_summary_markdown,
    export_session_report,
)

__all__ = [
    # Legacy compatibility
    "StateManager",
    "validate_workflow_state", 
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
