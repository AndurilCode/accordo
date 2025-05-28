"""State manager for workflow state file operations - now with session-based backend."""

from pathlib import Path
from typing import Optional

from ..models.workflow_state import WorkflowPhase, WorkflowStatus
from .session_manager import (
    add_log_to_session,
    export_session_to_markdown,
    get_or_create_session,
    migrate_session_from_markdown,
    update_session_state,
)


class StateManager:
    """Manages workflow state with session-based backend for backward compatibility."""

    def __init__(self, state_file: str = "workflow_state.md", client_id: str = "default"):
        """Initialize state manager with state file path and client ID."""
        self.state_file = Path(state_file)
        self.client_id = client_id

    def file_exists(self) -> bool:
        """Check if workflow state file exists (now checks session)."""
        # For backward compatibility, always return True if session exists
        session = get_or_create_session(self.client_id, "Default task")
        return session is not None

    def create_initial_state(self, task_description: str) -> None:
        """Create initial workflow state (now creates session)."""
        # Create session which will initialize the state
        get_or_create_session(self.client_id, task_description)

    def read_state(self) -> Optional[str]:
        """Read the current workflow state as markdown."""
        # Ensure session exists before exporting
        get_or_create_session(self.client_id, "Default task")
        return export_session_to_markdown(self.client_id)

    def update_state_section(
        self, phase: str, status: str, current_item: Optional[str] = None
    ) -> bool:
        """Update the State section of the workflow (now updates session)."""
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
        """Append an entry to the Log section (now updates session)."""
        # Ensure session exists before adding log
        get_or_create_session(self.client_id, "Default task")
        return add_log_to_session(self.client_id, entry)

    def _get_fallback_template(self, task_description: str) -> str:
        """Get fallback template if template file doesn't exist."""
        # This method is kept for backward compatibility but delegates to session
        session = get_or_create_session(self.client_id, task_description)
        return session.to_markdown()

    def migrate_from_file(self) -> bool:
        """Migrate existing workflow_state.md file to session."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    content = f.read()
                return migrate_session_from_markdown(self.client_id, content)
            except Exception:
                return False
        return False

    def export_to_file(self) -> bool:
        """Export current session to workflow_state.md file."""
        markdown = export_session_to_markdown(self.client_id)
        if markdown:
            try:
                with open(self.state_file, 'w') as f:
                    f.write(markdown)
                return True
            except Exception:
                return False
        return False

    def get_client_id(self) -> str:
        """Get the client ID for this state manager."""
        return self.client_id

    def set_client_id(self, client_id: str) -> None:
        """Set the client ID for this state manager."""
        self.client_id = client_id


# Legacy compatibility functions - maintained for existing code
def create_state_manager(state_file: str = "workflow_state.md", client_id: str = "default") -> StateManager:
    """Create a state manager instance with session backend."""
    return StateManager(state_file, client_id)


def migrate_file_to_session(file_path: str, client_id: str) -> bool:
    """Migrate a workflow state file to session."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return migrate_session_from_markdown(client_id, content)
    except Exception:
        return False


def export_session_to_file(client_id: str, file_path: str) -> bool:
    """Export a session to a file."""
    markdown = export_session_to_markdown(client_id)
    if markdown:
        try:
            with open(file_path, 'w') as f:
                f.write(markdown)
            return True
        except Exception:
            return False
    return False
