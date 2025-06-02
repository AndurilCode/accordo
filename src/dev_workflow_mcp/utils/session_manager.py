"""Session manager for client-based workflow state persistence."""

import threading
from datetime import UTC, datetime
from pathlib import Path

from ..models.workflow_state import (
    DynamicWorkflowState,
    WorkflowItem,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from ..models.yaml_workflow import WorkflowDefinition
from ..utils.yaml_loader import WorkflowLoader

# Global session store with thread-safe access
client_sessions: dict[str, WorkflowState | DynamicWorkflowState] = {}
session_lock = threading.Lock()


def get_session(client_id: str) -> WorkflowState | DynamicWorkflowState | None:
    """Get workflow session for a client."""
    with session_lock:
        return client_sessions.get(client_id)


def create_session(client_id: str, task_description: str) -> WorkflowState:
    """Create a new workflow session for a client (legacy mode)."""
    with session_lock:
        # Create initial workflow state
        state = WorkflowState(
            client_id=client_id,
            phase=WorkflowPhase.INIT,
            status=WorkflowStatus.READY,
            current_item=task_description,
            items=[WorkflowItem(id=1, description=task_description, status="pending")],
        )

        # Store in global sessions
        client_sessions[client_id] = state

        return state


def create_dynamic_session(
    client_id: str,
    task_description: str,
    workflow_def: WorkflowDefinition,
    workflow_file: str | None = None,
) -> DynamicWorkflowState:
    """Create a new dynamic workflow session for a client.

    Args:
        client_id: The client session identifier
        task_description: Description of the task to be processed
        workflow_def: The workflow definition to use
        workflow_file: Optional path to the workflow YAML file

    Returns:
        DynamicWorkflowState: The created session state
    """
    with session_lock:
        # Validate and process workflow inputs
        inputs = {}
        try:
            # For now, we'll pass the task_description as the main input
            # In a real scenario, this might be more sophisticated
            if "task_description" in workflow_def.inputs:
                inputs = workflow_def.validate_inputs(
                    {"task_description": task_description}
                )
            else:
                # If no task_description input, create a generic one
                inputs = {"task": task_description}
        except ValueError as e:
            # If validation fails, log it but continue with basic inputs
            inputs = {"task_description": task_description, "error": str(e)}

        # Create initial dynamic workflow state
        state = DynamicWorkflowState(
            client_id=client_id,
            workflow_name=workflow_def.name,
            workflow_file=workflow_file,
            current_node=workflow_def.workflow.root,
            status="READY",
            inputs=inputs,
            current_item=task_description,
            items=[WorkflowItem(id=1, description=task_description, status="pending")],
        )

        # Add initial log entry
        state.add_log_entry(f"🚀 DYNAMIC WORKFLOW INITIALIZED: {workflow_def.name}")
        state.add_log_entry(f"📍 Starting at root node: {workflow_def.workflow.root}")

        # Store in global sessions
        client_sessions[client_id] = state

        return state


def update_session(client_id: str, **kwargs) -> bool:
    """Update an existing session with new field values."""
    with session_lock:
        session = client_sessions.get(client_id)
        if not session:
            return False

        # Update fields
        for field, value in kwargs.items():
            if hasattr(session, field):
                setattr(session, field, value)

        # Update timestamp
        session.last_updated = datetime.now(UTC)

        return True


def update_dynamic_session_node(
    client_id: str,
    new_node: str,
    workflow_def: WorkflowDefinition,
    status: str | None = None,
    outputs: dict | None = None,
) -> bool:
    """Update a dynamic session's current node with validation.

    Args:
        client_id: The client session identifier
        new_node: The node to transition to
        workflow_def: The workflow definition for validation
        status: Optional new status
        outputs: Optional outputs from the previous node

    Returns:
        bool: True if successful
    """
    with session_lock:
        session = client_sessions.get(client_id)
        if not session or not isinstance(session, DynamicWorkflowState):
            return False

        # Complete current node if outputs provided
        if outputs:
            session.complete_current_node(outputs)

        # Transition to new node
        success = session.transition_to_node(new_node, workflow_def)

        if success and status:
            session.status = status

        return success


def delete_session(client_id: str) -> bool:
    """Delete a client session."""
    with session_lock:
        if client_id in client_sessions:
            del client_sessions[client_id]
            return True
        return False


def get_all_sessions() -> dict[str, WorkflowState | DynamicWorkflowState]:
    """Get all current sessions (returns a copy for safety)."""
    with session_lock:
        return client_sessions.copy()


def export_session_to_markdown(
    client_id: str, workflow_def: WorkflowDefinition | None = None
) -> str | None:
    """Export a session as markdown string."""
    with session_lock:
        session = client_sessions.get(client_id)
        if not session:
            return None

        if isinstance(session, DynamicWorkflowState):
            return session.to_markdown(workflow_def)
        else:
            return session.to_markdown()


def export_session_to_json(client_id: str) -> str | None:
    """Export a session as JSON string."""
    with session_lock:
        session = client_sessions.get(client_id)
        if not session:
            return None

        return session.to_json()


def export_session(
    client_id: str, format: str = "MD", workflow_def: WorkflowDefinition | None = None
) -> str | None:
    """Export a session in the specified format.

    Args:
        client_id: Client ID for session lookup.
        format: Export format - "MD" for markdown or "JSON" for JSON.
        workflow_def: Optional workflow definition for dynamic sessions

    Returns:
        Formatted string representation of session state or None if session doesn't exist.
    """
    format_upper = format.upper()

    if format_upper == "MD":
        return export_session_to_markdown(client_id, workflow_def)
    elif format_upper == "JSON":
        return export_session_to_json(client_id)
    else:
        # Default to markdown for unsupported formats
        return export_session_to_markdown(client_id, workflow_def)


def get_or_create_session(
    client_id: str, task_description: str | None = None
) -> WorkflowState:
    """Get existing session or create new one if it doesn't exist (legacy mode)."""
    session = get_session(client_id)
    if session is None:
        # Create with default task if none provided
        default_task = task_description or "Default workflow task"
        session = create_session(client_id, default_task)

    return session


def get_or_create_dynamic_session(
    client_id: str,
    task_description: str,
    workflow_name: str | None = None,
    workflows_dir: str = ".workflow-commander/workflows",
) -> DynamicWorkflowState | WorkflowState:
    """Get existing session or create a new dynamic one if it doesn't exist.

    Args:
        client_id: The client session identifier
        task_description: Description of the task
        workflow_name: Optional specific workflow name to use
        workflows_dir: Directory containing workflow definitions

    Returns:
        Union[DynamicWorkflowState, WorkflowState]: The session (falls back to legacy if no workflows found)
    """
    session = get_session(client_id)
    if session is not None:
        return session

    # Try to find and load a suitable workflow
    try:
        loader = WorkflowLoader(workflows_dir)

        if workflow_name:
            # Load specific workflow by name
            workflows = loader.load_all_workflows()
            if workflow_name in workflows:
                workflow_def = workflows[workflow_name]
                return create_dynamic_session(client_id, task_description, workflow_def)
        else:
            # Find best matching workflow
            workflow_def = loader.find_best_workflow(task_description)
            if workflow_def:
                return create_dynamic_session(client_id, task_description, workflow_def)

    except Exception:
        # If workflow loading fails, fall back to legacy mode
        pass

    # Fall back to legacy workflow if no dynamic workflow available
    return create_session(client_id, task_description)


def add_log_to_session(client_id: str, entry: str) -> bool:
    """Add a log entry to a session."""
    with session_lock:
        session = client_sessions.get(client_id)
        if not session:
            return False

        session.add_log_entry(entry)
        return True


def update_session_state(
    client_id: str,
    phase: WorkflowPhase | None = None,
    status: WorkflowStatus | None = None,
    current_item: str | None = None,
) -> bool:
    """Update session state fields (for legacy sessions)."""
    updates = {}

    if phase is not None:
        updates["phase"] = phase
    if status is not None:
        updates["status"] = status
    # Always update current_item if the parameter was passed (even if None)
    # We need to use a sentinel value to distinguish between "not passed" and "passed as None"
    # For now, we'll always update current_item when this function is called
    updates["current_item"] = current_item

    return update_session(client_id, **updates)


def update_dynamic_session_status(
    client_id: str,
    status: str | None = None,
    current_item: str | None = None,
) -> bool:
    """Update dynamic session state fields."""
    updates = {}

    if status is not None:
        updates["status"] = status
    if current_item is not None:
        updates["current_item"] = current_item

    return update_session(client_id, **updates)


def add_item_to_session(client_id: str, description: str) -> bool:
    """Add a new item to session's workflow."""
    with session_lock:
        session = client_sessions.get(client_id)
        if not session:
            return False

        # Find next available ID
        next_id = 1
        if session.items:
            next_id = max(item.id for item in session.items) + 1

        # Add new item
        new_item = WorkflowItem(id=next_id, description=description, status="pending")
        session.items.append(new_item)
        session.last_updated = datetime.now(UTC)

        return True


def mark_item_completed_in_session(client_id: str, item_id: int) -> bool:
    """Mark an item as completed in a session."""
    with session_lock:
        session = client_sessions.get(client_id)
        if not session:
            return False

        result = session.mark_item_completed(item_id)
        if result:
            session.last_updated = datetime.now(UTC)

        return result


def get_session_type(client_id: str) -> str | None:
    """Get the type of session (legacy or dynamic).

    Args:
        client_id: The client session identifier

    Returns:
        str | None: "legacy", "dynamic", or None if session doesn't exist
    """
    with session_lock:
        session = client_sessions.get(client_id)
        if not session:
            return None

        if isinstance(session, DynamicWorkflowState):
            return "dynamic"
        else:
            return "legacy"


def get_session_stats() -> dict[str, int]:
    """Get statistics about current sessions."""
    with session_lock:
        stats = {
            "total_sessions": len(client_sessions),
            "legacy_sessions": 0,
            "dynamic_sessions": 0,
            "sessions_by_phase": {},
            "sessions_by_status": {},
        }

        for session in client_sessions.values():
            if isinstance(session, DynamicWorkflowState):
                stats["dynamic_sessions"] += 1
                # For dynamic sessions, track by status
                status = session.status
                stats["sessions_by_status"][status] = (
                    stats["sessions_by_status"].get(status, 0) + 1
                )
            else:
                stats["legacy_sessions"] += 1
                # For legacy sessions, track by phase
                phase = session.phase.value
                stats["sessions_by_phase"][phase] = (
                    stats["sessions_by_phase"].get(phase, 0) + 1
                )

        return stats


def cleanup_completed_sessions(keep_recent_hours: int = 24) -> int:
    """Clean up old completed sessions.

    Args:
        keep_recent_hours: Keep sessions modified within this many hours

    Returns:
        Number of sessions cleaned up
    """
    cutoff_time = datetime.now(UTC).timestamp() - (keep_recent_hours * 3600)
    cleaned_count = 0

    with session_lock:
        sessions_to_remove = []

        for client_id, session in client_sessions.items():
            # Check if session is completed and old enough
            session_time = session.last_updated.timestamp()

            is_completed = False
            if isinstance(session, DynamicWorkflowState):
                # For dynamic sessions, check if at a terminal node or status indicates completion
                is_completed = session.status.upper() in [
                    "COMPLETED",
                    "ERROR",
                    "FINISHED",
                ]
            else:
                # For legacy sessions
                is_completed = session.status == WorkflowStatus.COMPLETED

            if is_completed and session_time < cutoff_time:
                sessions_to_remove.append(client_id)

        # Remove the sessions
        for client_id in sessions_to_remove:
            del client_sessions[client_id]
            cleaned_count += 1

    return cleaned_count


def migrate_session_from_markdown(client_id: str, markdown_content: str) -> bool:
    """Migrate a session from markdown content (legacy mode only).

    Args:
        client_id: Client ID for the session
        markdown_content: Markdown content to parse

    Returns:
        bool: True if successful
    """
    try:
        with session_lock:
            session = WorkflowState.from_markdown(markdown_content, client_id)
            client_sessions[client_id] = session
            return True
    except Exception:
        return False


def get_dynamic_session_workflow_def(client_id: str) -> WorkflowDefinition | None:
    """Get the workflow definition for a dynamic session.

    Args:
        client_id: The client session identifier

    Returns:
        WorkflowDefinition | None: The workflow definition or None if not available
    """
    with session_lock:
        session = client_sessions.get(client_id)
        if not session or not isinstance(session, DynamicWorkflowState):
            return None

        # Try to load the workflow definition
        try:
            if session.workflow_file:
                # Load from specific file
                loader = WorkflowLoader()
                return loader.load_workflow(Path(session.workflow_file))
            else:
                # Load from workflows directory by name
                loader = WorkflowLoader()
                workflows = loader.load_all_workflows()
                return workflows.get(session.workflow_name)
        except Exception:
            return None
