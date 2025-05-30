"""State manager for workflow state operations - now purely session-based."""

from ..models.config import WorkflowConfig
from ..models.workflow_state import WorkflowPhase, WorkflowStatus
from .session_manager import (
    add_log_to_session,
    export_session,
    get_or_create_session,
    update_session_state,
)


def get_file_operation_instructions(client_id: str = "default") -> str:
    """Generate mandatory file operation instructions when local state file is enabled.
    
    Args:
        client_id: Client ID for session management.
        
    Returns:
        Formatted file operation instructions or empty string if disabled.
    """
    config = WorkflowConfig()
    if not config.local_state_file:
        return ""
    
    # Get current state content from session using the configured format
    state_content = export_session(client_id, config.local_state_file_format)
    if not state_content:
        return ""
    
    # Determine filename and content type based on format
    if config.local_state_file_format == "JSON":
        filename = "workflow_state.json"
        content_type = "JSON"
    else:
        filename = "workflow_state.md"
        content_type = "markdown"
    
    return f"""

**🚨 MANDATORY FILE OPERATION - CANNOT BE SKIPPED:**

Since `WORKFLOW_LOCAL_STATE_FILE=true`, you MUST update the local workflow state file:

**⚠️ REQUIRED ACTION:**
```
Edit or create the file: {filename}

Content to write:
{state_content}
```

**📋 FILE OPERATION CHECKLIST:**
- [ ] Create or update `{filename}` in your working directory
- [ ] Write the complete {content_type} content exactly as shown above
- [ ] Verify the file was written successfully
- [ ] Continue with the guided workflow

**🚨 CRITICAL:** This file operation is MANDATORY when local state is enabled. The MCP server maintains the authoritative state in memory, but you must also maintain the local file as instructed.
"""


class StateManager:
    """Manages workflow state with session-based backend."""

    def __init__(self, state_file: str = "workflow_state.md", client_id: str = "default"):
        """Initialize state manager with client ID.
        
        Args:
            state_file: Deprecated parameter kept for backward compatibility, ignored.
            client_id: Client ID for session management.
        """
        # state_file parameter is kept for backward compatibility but ignored
        self.client_id = client_id

    def create_initial_state(self, task_description: str) -> None:
        """Create initial workflow state (creates session)."""
        get_or_create_session(self.client_id, task_description)

    def read_state(self) -> str | None:
        """Read the current workflow state as markdown."""
        # Ensure session exists before exporting
        get_or_create_session(self.client_id, "Default task")
        return export_session(self.client_id, "MD")

    def update_state_section(
        self, phase: str, status: str, current_item: str | None = None
    ) -> bool:
        """Update the State section of the workflow (updates session)."""
        try:
            phase_enum = WorkflowPhase(phase)
            status_enum = WorkflowStatus(status)
            
            # Ensure session exists before updating
            get_or_create_session(self.client_id, current_item or "Default task")
            
            return update_session_state(
                client_id=self.client_id,
                phase=phase_enum,
                status=status_enum,
                current_item=current_item
            )
        except ValueError:
            return False

    def append_to_log(self, entry: str) -> bool:
        """Append an entry to the Log section (updates session)."""
        # Ensure session exists before adding log
        get_or_create_session(self.client_id, "Default task")
        return add_log_to_session(self.client_id, entry)

    def get_client_id(self) -> str:
        """Get the client ID for this state manager."""
        return self.client_id

    def set_client_id(self, client_id: str) -> None:
        """Set the client ID for this state manager."""
        self.client_id = client_id


# Legacy compatibility function - maintained for existing code
def create_state_manager(state_file: str = "workflow_state.md", client_id: str = "default") -> StateManager:
    """Create a state manager instance with session backend.
    
    Args:
        state_file: Deprecated parameter kept for backward compatibility, ignored.
        client_id: Client ID for session management.
    """
    return StateManager(state_file, client_id)
