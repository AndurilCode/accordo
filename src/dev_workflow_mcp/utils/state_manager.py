"""State manager for workflow state operations - now purely session-based."""

from ..models.workflow_state import WorkflowPhase, WorkflowStatus
from .session_manager import (
    add_log_to_session,
    export_session_to_markdown,
    get_or_create_session,
    update_session_state,
)


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
        return export_session_to_markdown(self.client_id)

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
