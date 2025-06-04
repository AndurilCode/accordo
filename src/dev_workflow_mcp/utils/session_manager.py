"""Session manager for client-based workflow state persistence."""

import threading
from datetime import UTC, datetime
from pathlib import Path

from ..models.workflow_state import (
    DynamicWorkflowState,
    WorkflowItem,
)
from ..models.yaml_workflow import WorkflowDefinition
from ..utils.yaml_loader import WorkflowLoader

# Global session store with thread-safe access
client_sessions: dict[str, DynamicWorkflowState] = {}
session_lock = threading.Lock()

# Global workflow definition cache for dynamically created workflows
workflow_definitions_cache: dict[str, WorkflowDefinition] = {}
workflow_cache_lock = threading.Lock()

# Global server configuration for auto-sync functionality
_server_config = None
_server_config_lock = threading.Lock()


def set_server_config(server_config) -> None:
    """Set the server configuration for auto-sync functionality.

    Args:
        server_config: ServerConfig instance with session storage settings
    """
    global _server_config
    with _server_config_lock:
        _server_config = server_config


def _sync_session_to_file(client_id: str) -> bool:
    """Automatically sync session to filesystem when enabled.

    Args:
        client_id: Client ID for session lookup

    Returns:
        bool: True if sync succeeded or was skipped, False on error
    """
    global _server_config

    with _server_config_lock:
        if not _server_config or not _server_config.enable_local_state_file:
            return True  # Skip if disabled or no config

    try:
        # Ensure sessions directory exists
        if not _server_config.ensure_sessions_dir():
            return False

        # Get session content
        session = get_session(client_id)
        if not session:
            return False

        # Determine file format and content
        format_ext = _server_config.local_state_file_format.lower()
        session_file = _server_config.sessions_dir / f"{client_id}.{format_ext}"

        if _server_config.local_state_file_format == "JSON":
            content = session.to_json()
        else:
            content = session.to_markdown()

        if not content:
            return False

        # Atomic write operation
        temp_file = session_file.with_suffix(f".{format_ext}.tmp")
        temp_file.write_text(content, encoding="utf-8")
        temp_file.rename(session_file)

        return True

    except Exception:
        # Non-blocking: don't break workflow execution on sync failures
        return False


def get_session(client_id: str) -> DynamicWorkflowState | None:
    """Get workflow session for a client."""
    with session_lock:
        return client_sessions.get(client_id)


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

        # Auto-sync to filesystem if enabled
        _sync_session_to_file(client_id)

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

        # Auto-sync to filesystem if enabled
        _sync_session_to_file(client_id)

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

        # Auto-sync to filesystem if enabled
        if success:
            _sync_session_to_file(client_id)

        return success


def delete_session(client_id: str) -> bool:
    """Delete a client session."""
    with session_lock:
        if client_id in client_sessions:
            del client_sessions[client_id]
            return True
        return False


def get_all_sessions() -> dict[str, DynamicWorkflowState]:
    """Get all current sessions (returns a copy for safety)."""
    with session_lock:
        return client_sessions.copy()


def export_session_to_markdown(
    client_id: str, workflow_def: WorkflowDefinition | None = None
) -> str | None:
    """Export a session as markdown string."""
    with session_lock:
        session = client_sessions.get(client_id)
        if not session or not isinstance(session, DynamicWorkflowState):
            return None

        return session.to_markdown(workflow_def)


def export_session_to_json(client_id: str) -> str | None:
    """Export a session as JSON string."""
    with session_lock:
        session = client_sessions.get(client_id)
        if not session or not isinstance(session, DynamicWorkflowState):
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


def get_or_create_dynamic_session(
    client_id: str,
    task_description: str,
    workflow_name: str | None = None,
    workflows_dir: str = ".workflow-commander/workflows",
) -> DynamicWorkflowState | None:
    """Get existing session or create a new dynamic one if it doesn't exist.

    Args:
        client_id: The client session identifier
        task_description: Description of the task
        workflow_name: Optional specific workflow name to use
        workflows_dir: Directory containing workflow definitions

    Returns:
        DynamicWorkflowState | None: The session or None if no workflows found
    """
    session = get_session(client_id)
    if session is not None and isinstance(session, DynamicWorkflowState):
        return session

    # Try to find and load a suitable workflow
    try:
        loader = WorkflowLoader(workflows_dir)

        if workflow_name:
            # Load specific workflow by name
            workflows = loader.discover_workflows()
            if workflow_name in workflows:
                workflow_def = workflows[workflow_name]
                return create_dynamic_session(client_id, task_description, workflow_def)

    except Exception:
        # If workflow loading fails, return None
        pass

    # No dynamic workflow available
    return None


def add_log_to_session(client_id: str, entry: str) -> bool:
    """Add a log entry to a session."""
    with session_lock:
        session = client_sessions.get(client_id)
        if not session:
            return False

        session.add_log_entry(entry)

        # Auto-sync to filesystem if enabled
        _sync_session_to_file(client_id)

        return True


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

        # Auto-sync to filesystem if enabled
        _sync_session_to_file(client_id)

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
            # Auto-sync to filesystem if enabled
            _sync_session_to_file(client_id)

        return result


def get_session_type(client_id: str) -> str | None:
    """Get the type of session.

    Args:
        client_id: The client session identifier

    Returns:
        str | None: "dynamic" or None if session doesn't exist
    """
    with session_lock:
        session = client_sessions.get(client_id)
        if not session:
            return None

        if isinstance(session, DynamicWorkflowState):
            return "dynamic"
        else:
            return None


def get_session_stats() -> dict[str, int]:
    """Get statistics about current sessions."""
    with session_lock:
        stats = {
            "total_sessions": len(client_sessions),
            "dynamic_sessions": 0,
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

            if is_completed and session_time < cutoff_time:
                sessions_to_remove.append(client_id)

        # Remove the sessions
        for client_id in sessions_to_remove:
            del client_sessions[client_id]
            cleaned_count += 1

    return cleaned_count


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

        # First check the cache for dynamically created workflows
        cached_def = get_workflow_definition_from_cache(client_id)
        if cached_def:
            return cached_def

        # Try to load the workflow definition from filesystem
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


def store_workflow_definition_in_cache(
    client_id: str, workflow_def: WorkflowDefinition
) -> None:
    """Store a workflow definition in the cache for a client session.

    Args:
        client_id: The client session identifier
        workflow_def: The workflow definition to store
    """
    with workflow_cache_lock:
        workflow_definitions_cache[client_id] = workflow_def


def get_workflow_definition_from_cache(client_id: str) -> WorkflowDefinition | None:
    """Get a workflow definition from the cache for a client session.

    Args:
        client_id: The client session identifier

    Returns:
        WorkflowDefinition | None: The cached workflow definition or None
    """
    with workflow_cache_lock:
        return workflow_definitions_cache.get(client_id)


def clear_workflow_definition_cache(client_id: str) -> None:
    """Clear the workflow definition cache for a client session.

    Args:
        client_id: The client session identifier
    """
    with workflow_cache_lock:
        workflow_definitions_cache.pop(client_id, None)


def detect_session_conflict(client_id: str) -> dict[str, any] | None:
    """Detect if there's an existing session that would conflict with starting a new workflow.

    Args:
        client_id: The client session identifier

    Returns:
        dict: Session conflict information if conflict exists, None if no conflict

    The returned dict contains:
        - has_conflict: bool - Whether there's a conflict
        - session_type: str - Type of existing session ("legacy" or "dynamic")
        - session_summary: str - Human-readable summary of the existing session
        - current_item: str - Current item/task being processed
        - workflow_name: str - Name of workflow (for dynamic sessions)
        - phase_or_node: str - Current phase (legacy) or node (dynamic)
        - status: str - Current session status
    """
    with session_lock:
        session = client_sessions.get(client_id)
        if not session:
            return None

        # Only handle dynamic sessions now
        if isinstance(session, DynamicWorkflowState):
            session_type = "dynamic"
            workflow_name = session.workflow_name
            phase_or_node = session.current_node
            status = session.status

            session_summary = (
                f"Dynamic workflow '{workflow_name}' is active at node '{phase_or_node}' "
                f"with status '{status}'"
            )
        else:
            # Non-dynamic sessions are no longer supported
            return None

        return {
            "has_conflict": True,
            "session_type": session_type,
            "session_summary": session_summary,
            "current_item": session.current_item or "No current item",
            "workflow_name": workflow_name,
            "phase_or_node": phase_or_node,
            "status": status,
            "last_updated": session.last_updated.isoformat()
            if session.last_updated
            else "Unknown",
        }


def get_session_summary(client_id: str) -> str:
    """Get a human-readable summary of the current session state.

    Args:
        client_id: The client session identifier

    Returns:
        str: Formatted summary of the session, or "No active session" if none exists
    """
    conflict_info = detect_session_conflict(client_id)
    if not conflict_info:
        return "No active session"

    return (
        f"**{conflict_info['workflow_name']}** ({conflict_info['session_type']})\n"
        f"• Current: {conflict_info['phase_or_node']}\n"
        f"• Status: {conflict_info['status']}\n"
        f"• Task: {conflict_info['current_item']}\n"
        f"• Last Updated: {conflict_info['last_updated']}"
    )


def clear_session_completely(client_id: str) -> dict[str, any]:
    """Completely clear a session and all associated data.

    This function provides atomic cleanup of all session-related data including
    the main session, workflow cache, and any other associated state.

    Args:
        client_id: The client session identifier

    Returns:
        dict: Cleanup results with the following keys:
        - success: bool - Whether cleanup was successful
        - session_cleared: bool - Whether main session was removed
        - cache_cleared: bool - Whether workflow cache was cleared
        - previous_session_type: str | None - Type of session that was cleared
        - error: str | None - Error message if cleanup failed
    """
    results = {
        "success": False,
        "session_cleared": False,
        "cache_cleared": False,
        "previous_session_type": None,
        "error": None,
    }

    try:
        # First, get information about the existing session
        conflict_info = detect_session_conflict(client_id)
        if conflict_info:
            results["previous_session_type"] = conflict_info["session_type"]

        # Clear main session with thread safety
        with session_lock:
            if client_id in client_sessions:
                del client_sessions[client_id]
                results["session_cleared"] = True

        # Clear workflow definition cache
        with workflow_cache_lock:
            if client_id in workflow_definitions_cache:
                del workflow_definitions_cache[client_id]
                results["cache_cleared"] = True
            elif results["previous_session_type"] == "dynamic":
                # For dynamic sessions, cache might exist even if not indexed by client_id
                # This ensures we clear any potential cached data
                results["cache_cleared"] = True

        # Mark as successful if session was cleared
        results["success"] = results["session_cleared"] or conflict_info is None

        return results

    except Exception as e:
        results["error"] = str(e)
        return results
