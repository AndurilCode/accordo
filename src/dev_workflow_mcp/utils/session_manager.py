"""Session manager for session-ID-based workflow state persistence."""

import re
import threading
from datetime import UTC, datetime
from pathlib import Path

from ..models.workflow_state import (
    DynamicWorkflowState,
    WorkflowItem,
)
from ..models.yaml_workflow import WorkflowDefinition
from ..utils.yaml_loader import WorkflowLoader

# Global session store with thread-safe access - NOW KEYED BY SESSION_ID
sessions: dict[str, DynamicWorkflowState] = {}
session_lock = threading.Lock()

# Client to session mapping for multi-session support
client_session_registry: dict[str, list[str]] = {}
registry_lock = threading.Lock()

# Global workflow definition cache for dynamically created workflows
workflow_definitions_cache: dict[str, WorkflowDefinition] = {}
workflow_cache_lock = threading.Lock()

# Global server configuration for auto-sync functionality
_server_config = None
_server_config_lock = threading.Lock()

# Global cache manager for workflow state persistence
_cache_manager = None
_cache_manager_lock = threading.Lock()


def set_server_config(server_config) -> None:
    """Set the server configuration for auto-sync functionality.

    Args:
        server_config: ServerConfig instance with session storage settings
    """
    global _server_config, _cache_manager
    with _server_config_lock:
        _server_config = server_config
        
        # Initialize cache manager if cache mode is enabled
        if server_config.enable_cache_mode:
            _initialize_cache_manager(server_config)


def _initialize_cache_manager(server_config) -> bool:
    """Initialize the cache manager with server configuration.
    
    Args:
        server_config: ServerConfig instance
        
    Returns:
        bool: True if initialization successful
    """
    global _cache_manager
    
    with _cache_manager_lock:
        if _cache_manager is not None:
            return True  # Already initialized
            
        try:
            from .cache_manager import WorkflowCacheManager
            
            # Ensure cache directory exists
            if not server_config.ensure_cache_dir():
                return False
                
            _cache_manager = WorkflowCacheManager(
                db_path=str(server_config.cache_dir),
                collection_name=server_config.cache_collection_name,
                embedding_model=server_config.cache_embedding_model,
                max_results=server_config.cache_max_results
            )
            
            return True
            
        except Exception as e:
            print(f"Warning: Failed to initialize cache manager: {e}")
            return False


def get_cache_manager():
    """Get the global cache manager instance.
    
    Returns:
        WorkflowCacheManager or None if not available
    """
    global _cache_manager
    with _cache_manager_lock:
        return _cache_manager


def restore_sessions_from_cache(client_id: str | None = None) -> int:
    """Restore workflow sessions from cache on startup.
    
    Args:
        client_id: Optional client ID to restore sessions for specific client only
        
    Returns:
        Number of sessions restored from cache
    """
    cache_manager = get_cache_manager()
    if not cache_manager or not cache_manager.is_available():
        return 0
        
    try:
        restored_count = 0
        
        if client_id:
            # Restore sessions for specific client
            client_session_metadata = cache_manager.get_all_sessions_for_client(client_id)
            for metadata in client_session_metadata:
                session_id = metadata.session_id
                restored_state = cache_manager.retrieve_workflow_state(session_id)
                if restored_state:
                    with session_lock:
                        sessions[session_id] = restored_state
                        _register_session_for_client(client_id, session_id)
                    restored_count += 1
                    
        return restored_count
        
    except Exception:
        # Non-blocking: don't break startup on cache restoration failures
        return 0


def list_cached_sessions(client_id: str | None = None) -> list[dict]:
    """List available sessions in cache for restoration.
    
    Args:
        client_id: Optional client ID to filter sessions
        
    Returns:
        List of session metadata dictionaries
    """
    cache_manager = get_cache_manager()
    if not cache_manager or not cache_manager.is_available():
        return []
        
    try:
        if client_id:
            session_metadata_list = cache_manager.get_all_sessions_for_client(client_id)
            sessions_info = []
            
            for metadata in session_metadata_list:
                sessions_info.append({
                    "session_id": metadata.session_id,
                    "workflow_name": metadata.workflow_name,
                    "status": metadata.status,
                    "current_node": metadata.current_node,
                    "created_at": metadata.created_at.isoformat(),
                    "last_updated": metadata.last_updated.isoformat(),
                    "task_description": metadata.current_item if metadata.current_item else "No description",
                })
            
            return sessions_info
        else:
            # Get cache stats to show available sessions
            cache_stats = cache_manager.get_cache_stats()
            if cache_stats:
                return [{
                    "total_cached_sessions": cache_stats.total_entries,
                    "active_sessions": cache_stats.active_sessions,
                    "completed_sessions": cache_stats.completed_sessions,
                    "oldest_entry": cache_stats.oldest_entry.isoformat() if cache_stats.oldest_entry else None,
                    "newest_entry": cache_stats.newest_entry.isoformat() if cache_stats.newest_entry else None,
                }]
            
        return []
        
    except Exception:
        return []


def _generate_unique_session_filename(
    session_id: str, format_ext: str, sessions_dir: Path
) -> str:
    """Generate a unique session filename with timestamp and counter.

    Args:
        session_id: Session identifier
        format_ext: File extension (e.g., 'json', 'md')
        sessions_dir: Directory where session files are stored

    Returns:
        str: Unique filename in format: {session_id}_{timestamp}_{counter}.{ext}
    """
    # Clean session_id for filesystem safety
    safe_session_id = re.sub(r"[^\w\-_]", "_", session_id)

    # Generate ISO timestamp for filename (replace : with - for filesystem compatibility)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")

    # Find existing files with same session_id and timestamp to generate counter
    pattern = f"{safe_session_id}_{timestamp}_*.{format_ext}"
    existing_files = list(sessions_dir.glob(pattern))

    # Generate next counter
    counter = len(existing_files) + 1

    return f"{safe_session_id}_{timestamp}_{counter:03d}.{format_ext}"


def _sync_session_to_file(
    session_id: str, session: DynamicWorkflowState | None = None
) -> bool:
    """Automatically sync session to filesystem when enabled.

    Args:
        session_id: Session ID for session lookup
        session: Optional session object to avoid lock re-acquisition

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

        # Get session content - avoid lock re-acquisition if session provided
        if session is None:
            session = get_session(session_id)
        if not session:
            return False

        # Determine file format and content
        format_ext = _server_config.local_state_file_format.lower()

        # Generate or use existing unique filename for this session
        if not session.session_filename:
            # Generate new unique filename and store it in session
            unique_filename = _generate_unique_session_filename(
                session_id, format_ext, _server_config.sessions_dir
            )
            session.session_filename = unique_filename

        session_file = _server_config.sessions_dir / session.session_filename

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


def _sync_session_to_cache(session_id: str, session: DynamicWorkflowState | None = None) -> bool:
    """Sync session to cache when enabled.
    
    Args:
        session_id: Session ID for session lookup
        session: Optional session object to avoid lock re-acquisition
        
    Returns:
        bool: True if sync succeeded or was skipped, False on error
    """
    cache_manager = get_cache_manager()
    if not cache_manager or not cache_manager.is_available():
        return True  # Skip if cache disabled or unavailable
        
    try:
        # Get session if not provided
        if session is None:
            session = get_session(session_id)
        if not session:
            return False
            
        # Store in cache
        result = cache_manager.store_workflow_state(session)
        return result.success
        
    except Exception as e:
        # Non-blocking: don't break workflow execution on cache failures
        print(f"Warning: Failed to sync session to cache: {e}")
        return False


def sync_session(session_id: str) -> bool:
    """Explicitly sync a session to filesystem and cache after manual modifications.
    
    Use this function after directly modifying session fields outside of 
    session_manager functions to ensure changes are persisted.
    
    Args:
        session_id: The session identifier
        
    Returns:
        bool: True if sync succeeded or was skipped, False on error
    """
    file_sync = _sync_session_to_file(session_id)
    cache_sync = _sync_session_to_cache(session_id)
    
    # Return True if at least one sync method succeeded
    return file_sync or cache_sync


def get_session(session_id: str) -> DynamicWorkflowState | None:
    """Get workflow session by session ID."""
    with session_lock:
        return sessions.get(session_id)


def get_sessions_by_client(client_id: str) -> list[DynamicWorkflowState]:
    """Get all sessions for a specific client."""
    with registry_lock:
        session_ids = client_session_registry.get(client_id, [])

    with session_lock:
        return [sessions[sid] for sid in session_ids if sid in sessions]


def _register_session_for_client(client_id: str, session_id: str) -> None:
    """Register a session ID for a client (internal function)."""
    with registry_lock:
        if client_id not in client_session_registry:
            client_session_registry[client_id] = []
        if session_id not in client_session_registry[client_id]:
            client_session_registry[client_id].append(session_id)


def _unregister_session_for_client(client_id: str, session_id: str) -> None:
    """Unregister a session ID for a client (internal function)."""
    with registry_lock:
        if client_id in client_session_registry:
            if session_id in client_session_registry[client_id]:
                client_session_registry[client_id].remove(session_id)
            # Clean up empty client entries
            if not client_session_registry[client_id]:
                del client_session_registry[client_id]


def create_dynamic_session(
    client_id: str,
    task_description: str,
    workflow_def: WorkflowDefinition,
    workflow_file: str | None = None,
) -> DynamicWorkflowState:
    """Create a new dynamic workflow session.

    Args:
        client_id: The client identifier
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

        # Create initial dynamic workflow state (session_id auto-generated by model)
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

        # Store in global sessions using session_id as key
        sessions[state.session_id] = state

        # Register session for client
        _register_session_for_client(client_id, state.session_id)

        # Auto-sync to filesystem and cache if enabled (pass session to avoid lock re-acquisition)
        _sync_session_to_file(state.session_id, state)
        _sync_session_to_cache(state.session_id, state)

        return state


def update_session(session_id: str, **kwargs) -> bool:
    """Update an existing session with new field values."""
    with session_lock:
        session = sessions.get(session_id)
        if not session:
            return False

        # Update fields
        for field, value in kwargs.items():
            if hasattr(session, field):
                setattr(session, field, value)

        # Update timestamp
        session.last_updated = datetime.now(UTC)

        # Auto-sync to filesystem and cache if enabled (pass session to avoid lock re-acquisition)
        _sync_session_to_file(session_id, session)
        _sync_session_to_cache(session_id, session)

        return True


def update_dynamic_session_node(
    session_id: str,
    new_node: str,
    workflow_def: WorkflowDefinition,
    status: str | None = None,
    outputs: dict | None = None,
) -> bool:
    """Update a dynamic session's current node with validation.

    Args:
        session_id: The session identifier
        new_node: The node to transition to
        workflow_def: The workflow definition for validation
        status: Optional new status
        outputs: Optional outputs from the previous node

    Returns:
        bool: True if successful
    """
    with session_lock:
        session = sessions.get(session_id)
        if not session or not isinstance(session, DynamicWorkflowState):
            return False

        # Complete current node with outputs if provided
        if outputs:
            session.complete_current_node(outputs)
        else:
            # Even if no outputs provided, mark node as completed with basic tracking
            # This ensures node_outputs has an entry for the completed node
            basic_outputs = {
                "goal_achieved": True,
                "completion_method": "automatic_transition",
                "completed_without_detailed_outputs": True,
            }
            session.complete_current_node(basic_outputs)

        # Transition to new node
        success = session.transition_to_node(new_node, workflow_def)

        if success and status:
            session.status = status

        # Auto-sync to filesystem and cache if enabled (pass session to avoid lock re-acquisition)
        if success:
            _sync_session_to_file(session_id, session)
            _sync_session_to_cache(session_id, session)

        return success


def delete_session(session_id: str) -> bool:
    """Delete a session."""
    with session_lock:
        session = sessions.get(session_id)
        if not session:
            return False

        client_id = session.client_id

        # Remove from sessions
        del sessions[session_id]

        # Unregister from client
        _unregister_session_for_client(client_id, session_id)

        return True


def get_all_sessions() -> dict[str, DynamicWorkflowState]:
    """Get all current sessions (returns a copy for safety)."""
    with session_lock:
        return sessions.copy()


def export_session_to_markdown(
    session_id: str, workflow_def: WorkflowDefinition | None = None
) -> str | None:
    """Export a session as markdown string."""
    with session_lock:
        session = sessions.get(session_id)
        if not session or not isinstance(session, DynamicWorkflowState):
            return None

        return session.to_markdown(workflow_def)


def export_session_to_json(session_id: str) -> str | None:
    """Export a session as JSON string."""
    with session_lock:
        session = sessions.get(session_id)
        if not session or not isinstance(session, DynamicWorkflowState):
            return None

        return session.to_json()


def export_session(
    session_id: str, format: str = "MD", workflow_def: WorkflowDefinition | None = None
) -> str | None:
    """Export a session in the specified format.

    Args:
        session_id: Session ID for session lookup.
        format: Export format - "MD" for markdown or "JSON" for JSON.
        workflow_def: Optional workflow definition for dynamic sessions

    Returns:
        Formatted string representation of session state or None if session doesn't exist.
    """
    format_upper = format.upper()

    if format_upper == "MD":
        return export_session_to_markdown(session_id, workflow_def)
    elif format_upper == "JSON":
        return export_session_to_json(session_id)
    else:
        # Default to markdown for unsupported formats
        return export_session_to_markdown(session_id, workflow_def)


def get_or_create_dynamic_session(
    client_id: str,
    task_description: str,
    workflow_name: str | None = None,
    workflows_dir: str = ".workflow-commander/workflows",
) -> DynamicWorkflowState | None:
    """Get existing session or create a new dynamic one if it doesn't exist.

    Args:
        client_id: The client identifier
        task_description: Description of the task
        workflow_name: Optional specific workflow name to use
        workflows_dir: Directory containing workflow definitions

    Returns:
        DynamicWorkflowState | None: The session or None if no workflows found
    """
    # NOTE: This function is now primarily for backward compatibility
    # The new approach should use create_dynamic_session directly with explicit session management

    # Check if client has any existing sessions
    existing_sessions = get_sessions_by_client(client_id)
    if existing_sessions:
        # Return the most recent session for backwards compatibility
        return max(existing_sessions, key=lambda s: s.last_updated)

    # No existing sessions, try to create one
    try:
        loader = WorkflowLoader(workflows_dir)
        workflows = loader.discover_workflows()

        if not workflows:
            return None

        # Use specified workflow or first available
        selected_workflow = None
        if workflow_name and workflow_name in workflows:
            selected_workflow = workflows[workflow_name]
        elif workflows:
            selected_workflow = next(iter(workflows.values()))

        if selected_workflow:
            return create_dynamic_session(
                client_id, task_description, selected_workflow
            )

    except Exception:
        pass  # Fallback gracefully

    return None


def add_log_to_session(session_id: str, entry: str) -> bool:
    """Add log entry to a session."""
    with session_lock:
        session = sessions.get(session_id)
        if not session:
            return False

        session.add_log_entry(entry)
        session.last_updated = datetime.now(UTC)

        # Auto-sync to filesystem and cache if enabled (pass session to avoid lock re-acquisition)
        _sync_session_to_file(session_id, session)
        _sync_session_to_cache(session_id, session)

        return True


def update_dynamic_session_status(
    session_id: str,
    status: str | None = None,
    current_item: str | None = None,
) -> bool:
    """Update dynamic session state fields."""
    updates = {}

    if status is not None:
        updates["status"] = status
    if current_item is not None:
        updates["current_item"] = current_item

    return update_session(session_id, **updates)


def add_item_to_session(session_id: str, description: str) -> bool:
    """Add an item to a session."""
    with session_lock:
        session = sessions.get(session_id)
        if not session:
            return False

        # Get next ID
        next_id = max([item.id for item in session.items], default=0) + 1

        # Add new item
        new_item = WorkflowItem(id=next_id, description=description, status="pending")
        session.items.append(new_item)
        session.last_updated = datetime.now(UTC)

        # Auto-sync to filesystem and cache if enabled (pass session to avoid lock re-acquisition)
        _sync_session_to_file(session_id, session)
        _sync_session_to_cache(session_id, session)

        return True


def mark_item_completed_in_session(session_id: str, item_id: int) -> bool:
    """Mark an item as completed in a session."""
    with session_lock:
        session = sessions.get(session_id)
        if not session:
            return False

        result = session.mark_item_completed(item_id)
        if result:
            session.last_updated = datetime.now(UTC)
            # Auto-sync to filesystem and cache if enabled (pass session to avoid lock re-acquisition)
            _sync_session_to_file(session_id, session)
            _sync_session_to_cache(session_id, session)

        return result


def get_session_type(session_id: str) -> str | None:
    """Get the type of session.

    Args:
        session_id: The session identifier

    Returns:
        str | None: "dynamic" or None if session doesn't exist
    """
    with session_lock:
        session = sessions.get(session_id)
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
            "total_sessions": len(sessions),
            "dynamic_sessions": 0,
            "sessions_by_status": {},
        }

        for session in sessions.values():
            if isinstance(session, DynamicWorkflowState):
                stats["dynamic_sessions"] += 1
                # For dynamic sessions, track by status
                status = session.status
                stats["sessions_by_status"][status] = (
                    stats["sessions_by_status"].get(status, 0) + 1
                )

        return stats


def _archive_session_file(session: DynamicWorkflowState) -> bool:
    """Archive a completed session file by adding completion timestamp to filename.

    Args:
        session: The session to archive

    Returns:
        bool: True if archiving succeeded, False otherwise
    """
    global _server_config

    with _server_config_lock:
        if not _server_config or not _server_config.enable_local_state_file:
            return True  # Skip if disabled

    try:
        if not session.session_filename:
            return True  # No file to archive

        sessions_dir = _server_config.sessions_dir
        current_file = sessions_dir / session.session_filename

        if not current_file.exists():
            return True  # File doesn't exist, nothing to archive

        # Generate archived filename with completion timestamp
        completion_timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
        base_name = session.session_filename.rsplit(".", 1)[0]  # Remove extension
        extension = session.session_filename.rsplit(".", 1)[1]  # Get extension

        archived_filename = f"{base_name}_COMPLETED_{completion_timestamp}.{extension}"
        archived_file = sessions_dir / archived_filename

        # Move current file to archived location
        current_file.rename(archived_file)

        return True

    except Exception:
        # Non-blocking: don't break workflow execution on archive failures
        return False


def cleanup_completed_sessions(
    keep_recent_hours: int = 24, archive_before_cleanup: bool = True
) -> int:
    """Clean up old completed sessions with optional archiving.

    Args:
        keep_recent_hours: Keep sessions modified within this many hours
        archive_before_cleanup: Whether to archive session files before cleanup

    Returns:
        Number of sessions cleaned up
    """
    cutoff_time = datetime.now(UTC).timestamp() - (keep_recent_hours * 3600)
    cleaned_count = 0

    with session_lock:
        sessions_to_remove = []

        for session_id, session in sessions.items():
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
                # Archive the session file before removing from memory
                if archive_before_cleanup:
                    _archive_session_file(session)

                sessions_to_remove.append(session_id)

        # Remove the sessions from memory and registry
        for session_id in sessions_to_remove:
            session = sessions[session_id]
            client_id = session.client_id

            del sessions[session_id]
            _unregister_session_for_client(client_id, session_id)
            cleaned_count += 1

    return cleaned_count


def get_dynamic_session_workflow_def(session_id: str) -> WorkflowDefinition | None:
    """Get the workflow definition for a dynamic session.

    Args:
        session_id: The session identifier

    Returns:
        WorkflowDefinition | None: The workflow definition or None if not available
    """
    with session_lock:
        session = sessions.get(session_id)
        if not session or not isinstance(session, DynamicWorkflowState):
            return None

        # First check the cache for dynamically created workflows
        cached_def = get_workflow_definition_from_cache(session_id)
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
    session_id: str, workflow_def: WorkflowDefinition
) -> None:
    """Store a workflow definition in the cache for a session.

    Args:
        session_id: The session identifier
        workflow_def: The workflow definition to store
    """
    with workflow_cache_lock:
        workflow_definitions_cache[session_id] = workflow_def


def get_workflow_definition_from_cache(session_id: str) -> WorkflowDefinition | None:
    """Get a workflow definition from the cache for a session.

    Args:
        session_id: The session identifier

    Returns:
        WorkflowDefinition | None: The cached workflow definition or None
    """
    with workflow_cache_lock:
        return workflow_definitions_cache.get(session_id)


def clear_workflow_definition_cache(session_id: str) -> None:
    """Clear the workflow definition cache for a session.

    Args:
        session_id: The session identifier
    """
    with workflow_cache_lock:
        workflow_definitions_cache.pop(session_id, None)


def detect_session_conflict(client_id: str) -> dict[str, any] | None:
    """Detect if there are existing sessions for a client.

    Args:
        client_id: The client identifier

    Returns:
        dict: Session conflict information if sessions exist, None if no sessions

    The returned dict contains:
        - has_conflict: bool - Whether there are existing sessions
        - session_count: int - Number of existing sessions
        - sessions: list - List of session summaries
        - most_recent_session: dict - Details of most recent session
        - session_type: str - Type of the most recent session
        - workflow_name: str - Name of the workflow in the most recent session
        - phase_or_node: str - Current node/phase of the most recent session
        - status: str - Status of the most recent session
        - current_item: str - Current item in the most recent session
        - last_updated: str - Last updated timestamp of the most recent session
    """
    existing_sessions = get_sessions_by_client(client_id)

    if not existing_sessions:
        return None

    # Get most recent session
    most_recent = max(existing_sessions, key=lambda s: s.last_updated)

    session_summaries = []
    for session in existing_sessions:
        session_summaries.append(
            {
                "session_id": session.session_id,
                "workflow_name": session.workflow_name,
                "current_node": session.current_node,
                "status": session.status,
                "current_item": session.current_item or "No current item",
                "last_updated": session.last_updated.isoformat(),
            }
        )

    return {
        "has_conflict": True,
        "session_count": len(existing_sessions),
        "sessions": session_summaries,
        "most_recent_session": {
            "session_id": most_recent.session_id,
            "workflow_name": most_recent.workflow_name,
            "current_node": most_recent.current_node,
            "status": most_recent.status,
            "current_item": most_recent.current_item or "No current item",
            "last_updated": most_recent.last_updated.isoformat(),
        },
        # Top-level fields expected by discovery_prompts.py
        "session_type": "dynamic",  # All current sessions are dynamic type
        "workflow_name": most_recent.workflow_name,
        "phase_or_node": most_recent.current_node,
        "status": most_recent.status,
        "current_item": most_recent.current_item or "No current item",
        "last_updated": most_recent.last_updated.isoformat(),
    }


def get_session_summary(session_id: str) -> str:
    """Get a human-readable summary of a session state.

    Args:
        session_id: The session identifier

    Returns:
        str: Formatted summary of the session, or "Session not found" if none exists
    """
    session = get_session(session_id)
    if not session:
        return "Session not found"

    return (
        f"**{session.workflow_name}** (dynamic)\n"
        f"• Session ID: {session.session_id}\n"
        f"• Current: {session.current_node}\n"
        f"• Status: {session.status}\n"
        f"• Task: {session.current_item}\n"
        f"• Last Updated: {session.last_updated.isoformat()}"
    )


def clear_session_completely(session_id: str) -> dict[str, any]:
    """Completely clear a session and all associated data.

    This function provides atomic cleanup of all session-related data including
    the main session, workflow cache, and any other associated state.

    Args:
        session_id: The session identifier

    Returns:
        dict: Cleanup results with the following keys:
        - success: bool - Whether cleanup was successful
        - session_cleared: bool - Whether main session was removed
        - cache_cleared: bool - Whether workflow cache was cleared
        - session_type: str | None - Type of session that was cleared
        - error: str | None - Error message if cleanup failed
    """
    results = {
        "success": False,
        "session_cleared": False,
        "cache_cleared": False,
        "session_type": None,
        "error": None,
    }

    try:
        # Get session info before clearing
        session = get_session(session_id)
        if session:
            results["session_type"] = "dynamic"

        # Clear main session with thread safety
        success = delete_session(session_id)
        results["session_cleared"] = success

        # Clear workflow definition cache
        clear_workflow_definition_cache(session_id)
        results["cache_cleared"] = True

        # Mark as successful if session was cleared
        results["success"] = success

        return results

    except Exception as e:
        results["error"] = str(e)
        return results


def clear_all_client_sessions(client_id: str) -> dict[str, any]:
    """Clear all sessions for a specific client.

    Args:
        client_id: The client identifier

    Returns:
        dict: Cleanup results with the following keys:
        - success: bool - Whether cleanup was successful overall
        - sessions_cleared: int - Number of sessions cleared
        - failed_sessions: list - List of sessions that failed to clear
        - previous_session_type: str - Type of sessions that were cleared
        - error: str | None - Error message if cleanup failed
    """
    results = {
        "success": False,
        "sessions_cleared": 0,
        "failed_sessions": [],
        "previous_session_type": "dynamic",
        "error": None,
    }

    try:
        # Get all sessions for the client
        client_sessions = get_sessions_by_client(client_id)
        
        if not client_sessions:
            results["success"] = True
            return results

        # Clear each session
        for session in client_sessions:
            session_result = clear_session_completely(session.session_id)
            if session_result["success"]:
                results["sessions_cleared"] += 1
            else:
                results["failed_sessions"].append({
                    "session_id": session.session_id,
                    "error": session_result.get("error", "Unknown error")
                })

        # Mark as successful if all sessions were cleared
        results["success"] = len(results["failed_sessions"]) == 0

        return results

    except Exception as e:
        results["error"] = str(e)
        return results
