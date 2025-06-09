"""State manager for workflow state operations - now purely session-based."""

from ..models.config import WorkflowConfig
from .session_manager import (
    add_log_to_session,
    export_session,
    get_or_create_dynamic_session,
)


def get_file_operation_instructions(
    client_id: str = "default", server_config=None
) -> str:
    """Generate mandatory file operation instructions when local state file is enabled.

    Args:
        client_id: Client ID for session management.
        server_config: ServerConfig instance with CLI-provided session storage settings.
                      If None, uses WorkflowConfig defaults (backwards compatibility).

    Returns:
        Formatted file operation instructions or empty string if disabled.
    """
    # Use server_config if provided (new CLI-based approach), otherwise fall back to WorkflowConfig
    if server_config:
        if not server_config.enable_local_state_file:
            return ""

        # Get current state content from session using the configured format
        state_content = export_session(client_id, server_config.local_state_file_format)
        if not state_content:
            return ""

        # Use repository-scoped sessions directory with session-specific naming
        # NOTE: Changed from client_id-based naming to avoid collisions in multi-chat environments
        format_ext = server_config.local_state_file_format.lower()

        # Generate session-aware filename to prevent collisions
        # If there's an active session, use session-based naming; otherwise use timestamp-based
        from .session_manager import get_sessions_by_client

        sessions = get_sessions_by_client(client_id)
        if sessions:
            # Use most recent session for filename
            latest_session = max(sessions, key=lambda s: s.last_updated)
            safe_session_id = latest_session.session_id.replace("-", "_")[
                :16
            ]  # Truncate for filesystem safety
            file_path = (
                server_config.sessions_dir / f"session_{safe_session_id}.{format_ext}"
            )
        else:
            # No active sessions - use timestamp-based naming
            from datetime import UTC, datetime

            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            file_path = (
                server_config.sessions_dir / f"workflow_{timestamp}.{format_ext}"
            )

        content_type = (
            "JSON" if server_config.local_state_file_format == "JSON" else "markdown"
        )
    else:
        # Backwards compatibility with WorkflowConfig (deprecated)
        config = WorkflowConfig()
        if not config.local_state_file:
            return ""

        # Get current state content from session using the configured format
        state_content = export_session(client_id, config.local_state_file_format)
        if not state_content:
            return ""

        # Use old path utilities for backwards compatibility
        from .path_utils import get_workflow_state_path

        file_path = get_workflow_state_path(format_type=config.local_state_file_format)
        content_type = (
            "JSON" if config.local_state_file_format == "JSON" else "markdown"
        )

    return f"""

**🚨 MANDATORY FILE OPERATION - CANNOT BE SKIPPED:**

Since local state file is enabled, you MUST update the local workflow state file:

**⚠️ REQUIRED ACTION:**
```
Edit or create the file: {file_path}

Content to write:
{state_content}
```

**📋 FILE OPERATION CHECKLIST:**
- [ ] Create or update `{file_path}` in your working directory
- [ ] Write the complete {content_type} content exactly as shown above
- [ ] Verify the file was written successfully
- [ ] Continue with the guided workflow

**🚨 CRITICAL:** This file operation is MANDATORY when local state is enabled. The MCP server maintains the authoritative state in memory, but you must also maintain the local file as instructed.
"""


class StateManager:
    """Manages workflow state with session-based backend."""

    def __init__(self, client_id: str = "default"):
        """Initialize state manager with client ID.

        Args:
            client_id: Client ID for session management.
        """
        self.client_id = client_id

    def create_initial_state(self, task_description: str) -> None:
        """Create initial workflow state (creates session)."""
        # Try to create a dynamic session, but don't fail if no workflows available
        get_or_create_dynamic_session(self.client_id, task_description)

    def read_state(self) -> str | None:
        """Read the current workflow state as markdown."""
        # Try to get existing session state
        return export_session(self.client_id, "MD")

    def update_state_section(
        self, phase: str, status: str, current_item: str | None = None
    ) -> bool:
        """Update the State section of the workflow (updates session)."""
        # Legacy method - no longer supported with YAML-only workflows
        # Return False to indicate operation not supported
        return False

    def append_to_log(self, entry: str) -> bool:
        """Append an entry to the Log section (updates session)."""
        # Only works if there's an existing dynamic session
        return add_log_to_session(self.client_id, entry)

    def get_client_id(self) -> str:
        """Get the client ID for this state manager."""
        return self.client_id

    def set_client_id(self, client_id: str) -> None:
        """Set the client ID for this state manager."""
        self.client_id = client_id
