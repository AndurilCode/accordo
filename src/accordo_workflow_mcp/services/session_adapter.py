"""Session adapter service providing legacy session_manager.py interface compatibility.

This module provides backward compatibility during the migration from legacy
session_manager.py to direct service usage. All functions delegate to the
modern SessionRepository service while maintaining exact legacy signatures.
"""

import threading
from datetime import UTC, datetime
from typing import Any

from ..models.workflow_state import DynamicWorkflowState
from ..models.yaml_workflow import WorkflowDefinition
from ..services import get_session_repository, initialize_session_services
from ..services.dependency_injection import DependencyInjectionError, has_service
from ..services.session_repository import SessionRepository

# Thread locks for compatibility
_server_config_lock = threading.Lock()
_cache_manager_lock = threading.Lock()
session_lock = threading.Lock()

# Global variables for legacy compatibility
_server_config = None
_cache_manager = None


def _ensure_services_initialized():
    """Ensure services are initialized before use."""
    try:
        # Check if services are registered
        if not has_service(SessionRepository):
            # Services not registered, initialize them
            initialize_session_services()

        # Try to get a service to verify they work
        get_session_repository()
    except DependencyInjectionError:
        # Services not initialized properly, re-initialize them
        initialize_session_services()
    except Exception:
        pass


def _get_server_config_from_service():
    """Get server configuration from the modern configuration service."""
    try:
        from ..services.config_service import get_configuration_service

        config_service = get_configuration_service()
        return config_service.to_legacy_server_config()
    except Exception:
        return None


def _get_effective_server_config():
    """Get effective server configuration using modern service or legacy fallback."""
    # Try modern configuration service first
    service_config = _get_server_config_from_service()
    if service_config:
        return service_config

    # Fallback to legacy global variable
    global _server_config
    with _server_config_lock:
        return _server_config


def set_server_config(server_config) -> None:
    """Set the server configuration for auto-sync functionality."""
    global _server_config, _cache_manager
    with _server_config_lock:
        _server_config = server_config

        # Initialize cache manager if cache mode is enabled
        if server_config.enable_cache_mode:
            _initialize_cache_manager(server_config)


def _initialize_cache_manager(server_config) -> bool:
    """Initialize the cache manager with server configuration."""
    global _cache_manager

    with _cache_manager_lock:
        if _cache_manager is not None:
            return True  # Already initialized

        try:
            from ..utils.cache_manager import WorkflowCacheManager

            # Ensure cache directory exists
            if not server_config.ensure_cache_dir():
                return False

            _cache_manager = WorkflowCacheManager(
                db_path=str(server_config.cache_dir),
                collection_name=server_config.cache_collection_name,
                embedding_model=server_config.cache_embedding_model,
                max_results=server_config.cache_max_results,
            )

            return True

        except Exception:
            return False


def get_cache_manager():
    """Get the cache manager instance."""
    global _cache_manager
    
    with _cache_manager_lock:
        if _cache_manager is not None:
            return _cache_manager

    # Try to get from cache service
    try:
        from ..services.cache_service import get_cache_service
        cache_service = get_cache_service()
        if cache_service.is_available():
            return cache_service.get_cache_manager()
    except Exception:
        pass

    return None


# Session Repository Functions - delegate to modern service
def get_session(session_id: str) -> DynamicWorkflowState | None:
    """Get a session by ID."""
    _ensure_services_initialized()
    return get_session_repository().get_session(session_id)


def create_dynamic_session(
    client_id: str,
    task_description: str,
    workflow_def: WorkflowDefinition,
    workflow_file: str | None = None,
) -> DynamicWorkflowState:
    """Create a new dynamic session."""
    _ensure_services_initialized()
    return get_session_repository().create_session(
        client_id, task_description, workflow_def, workflow_file
    )


def update_session(session_id: str, **kwargs: Any) -> bool:
    """Update session with provided fields."""
    _ensure_services_initialized()
    return get_session_repository().update_session(session_id, **kwargs)


def delete_session(session_id: str) -> bool:
    """Delete a session by ID."""
    _ensure_services_initialized()
    return get_session_repository().delete_session(session_id)


def get_sessions_by_client(client_id: str) -> list[DynamicWorkflowState]:
    """Get all sessions for a client."""
    _ensure_services_initialized()
    return get_session_repository().get_sessions_by_client(client_id)


def get_all_sessions() -> dict[str, DynamicWorkflowState]:
    """Get all sessions."""
    _ensure_services_initialized()
    return get_session_repository().get_all_sessions()


def get_session_stats() -> dict[str, int]:
    """Get session statistics."""
    _ensure_services_initialized()
    return get_session_repository().get_session_stats()


def get_session_type(session_id: str) -> str | None:
    """Get session type."""
    _ensure_services_initialized()
    return get_session_repository().get_session_type(session_id)


# Compatibility proxy objects for tests
class _SessionsProxy:
    """Proxy object to provide test compatibility with the old sessions dict."""

    def clear(self) -> None:
        """Clear all sessions (for test compatibility)."""
        _ensure_services_initialized()
        all_sessions = get_all_sessions()
        for session_id in all_sessions:
            delete_session(session_id)

    def get(self, session_id: str, default=None):
        """Get session by ID (for test compatibility)."""
        _ensure_services_initialized()
        session = get_session(session_id)
        return session if session is not None else default

    def __getitem__(self, session_id: str):
        """Get session by ID using dict syntax."""
        _ensure_services_initialized()
        session = get_session(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def __setitem__(self, session_id: str, session: DynamicWorkflowState):
        """Set session using dict syntax (for test compatibility only)."""
        _ensure_services_initialized()
        repository = get_session_repository()

        # For test compatibility, directly store the session
        with repository._lock:
            repository._sessions[session_id] = session

        # Register with client if needed
        repository._register_session_for_client(session.client_id, session_id)

    def __contains__(self, session_id: str) -> bool:
        """Check if session exists."""
        _ensure_services_initialized()
        return get_session(session_id) is not None

    def keys(self):
        """Get all session IDs."""
        _ensure_services_initialized()
        return get_all_sessions().keys()

    def values(self):
        """Get all sessions."""
        _ensure_services_initialized()
        return get_all_sessions().values()

    def items(self):
        """Get all session items."""
        _ensure_services_initialized()
        return get_all_sessions().items()


class _ClientSessionRegistryProxy:
    """Proxy for client session registry compatibility."""

    def clear(self) -> None:
        """Clear all client sessions (for test compatibility)."""
        _ensure_services_initialized()
        # This is handled automatically by the session repository
        pass

    def get(self, client_id: str, default=None):
        """Get sessions for client."""
        sessions = get_sessions_by_client(client_id)
        return [s.session_id for s in sessions] if sessions else (default or [])

    def __contains__(self, item: str) -> bool:
        """Check if client ID exists in registry or session ID exists."""
        _ensure_services_initialized()
        all_sessions = get_all_sessions()

        # Check if it's a client ID
        client_ids = set(session.client_id for session in all_sessions.values())
        if item in client_ids:
            return True

        # Check if it's a session ID
        return item in all_sessions

    def keys(self):
        """Get all client IDs."""
        _ensure_services_initialized()
        all_sessions = get_all_sessions()
        return set(session.client_id for session in all_sessions.values())

    def values(self):
        """Get all session lists."""
        _ensure_services_initialized()
        client_ids = self.keys()
        return [self.get(client_id, []) for client_id in client_ids]

    def items(self):
        """Get all client-session mappings."""
        _ensure_services_initialized()
        client_ids = self.keys()
        return [(client_id, self.get(client_id, [])) for client_id in client_ids]

    def __getitem__(self, client_id: str):
        """Get sessions for client using dict syntax."""
        return self.get(client_id, [])

    def __setitem__(self, client_id: str, session_ids: list[str]):
        """Set sessions for client (not supported in new architecture)."""
        pass  # Legacy compatibility - not implemented


# Global proxy instances for compatibility
sessions = _SessionsProxy()
client_session_registry = _ClientSessionRegistryProxy()


# Additional session functionality that may be used
def sync_session(session_id: str) -> bool:
    """Sync session to cache and file systems."""
    _ensure_services_initialized()
    try:
        from ..services import get_session_sync_service
        sync_service = get_session_sync_service()
        return sync_service.sync_session(session_id)
    except Exception:
        return False


def auto_restore_sessions_on_startup() -> int:
    """Auto restore sessions on startup."""
    _ensure_services_initialized()
    try:
        from ..services import get_session_lifecycle_manager
        lifecycle_manager = get_session_lifecycle_manager()
        return lifecycle_manager.auto_restore_sessions_on_startup()
    except Exception:
        return 0


def restore_sessions_from_cache(client_id: str | None = None) -> int:
    """Restore sessions from cache."""
    _ensure_services_initialized()
    try:
        from ..services import get_session_lifecycle_manager
        lifecycle_manager = get_session_lifecycle_manager()
        return lifecycle_manager.restore_sessions_from_cache(client_id)
    except Exception:
        return 0


def list_cached_sessions(client_id: str | None = None) -> list[dict]:
    """List cached sessions."""
    _ensure_services_initialized()
    try:
        from ..services import get_session_lifecycle_manager
        lifecycle_manager = get_session_lifecycle_manager()
        return lifecycle_manager.list_cached_sessions(client_id)
    except Exception:
        return []


# Workflow definition cache functions
def store_workflow_definition_in_cache(
    session_id: str, workflow_def: WorkflowDefinition
) -> None:
    """Store workflow definition in cache."""
    _ensure_services_initialized()
    try:
        from ..services import get_workflow_definition_cache
        cache = get_workflow_definition_cache()
        cache.store_workflow_definition(session_id, workflow_def)
    except Exception:
        pass


def get_workflow_definition_from_cache(session_id: str) -> WorkflowDefinition | None:
    """Get workflow definition from cache."""
    _ensure_services_initialized()
    try:
        from ..services import get_workflow_definition_cache
        cache = get_workflow_definition_cache()
        return cache.get_workflow_definition(session_id)
    except Exception:
        return None


def clear_workflow_definition_cache(session_id: str) -> None:
    """Clear workflow definition cache."""
    _ensure_services_initialized()
    try:
        from ..services import get_workflow_definition_cache
        cache = get_workflow_definition_cache()
        cache.clear_workflow_definition_cache(session_id)
    except Exception:
        pass


# Session utility functions
def add_item_to_session(session_id: str, item: str) -> bool:
    """Add item to session (compatibility function)."""
    _ensure_services_initialized()
    session = get_session(session_id)
    if session:
        session.items.append(item)
        return update_session(session_id, items=session.items)
    return False


def add_log_to_session(session_id: str, log_entry: str) -> bool:
    """Add log entry to session."""
    _ensure_services_initialized()
    session = get_session(session_id)
    if session:
        session.log.append({"timestamp": datetime.now(UTC), "message": log_entry})
        return update_session(session_id, log=session.log)
    return False


def mark_item_completed_in_session(session_id: str, item: str) -> bool:
    """Mark item as completed in session (compatibility function)."""
    _ensure_services_initialized()
    session = get_session(session_id)
    if session and item in session.items:
        # This is a simplified implementation for compatibility
        # In practice, you might want to track completed items separately
        return add_log_to_session(session_id, f"Completed: {item}")
    return False


def cleanup_completed_sessions() -> int:
    """Clean up completed sessions."""
    _ensure_services_initialized()
    try:
        from ..services import get_session_lifecycle_manager
        lifecycle_manager = get_session_lifecycle_manager()
        return lifecycle_manager.cleanup_completed_sessions()
    except Exception:
        return 0


def export_session_to_markdown(session_id: str) -> str:
    """Export session to markdown format."""
    _ensure_services_initialized()
    session = get_session(session_id)
    if not session:
        return f"Session {session_id} not found"
        
    # Basic markdown export
    lines = [
        f"# Session: {session_id}",
        f"**Client ID:** {session.client_id}",
        f"**Created:** {session.created_at}",
        f"**Status:** {session.status}",
        f"**Current Node:** {session.current_node}",
        "",
        "## Task Description",
        session.current_item,
        "",
        "## Log Entries",
    ]
    
    for entry in session.log:
        if isinstance(entry, dict):
            timestamp = entry.get("timestamp", "Unknown")
            message = entry.get("message", "")
            lines.append(f"- **{timestamp}**: {message}")
        else:
            lines.append(f"- {entry}")
    
    return "\n".join(lines)


# Additional compatibility functions for legacy code
def _register_session_for_client(client_id: str, session_id: str) -> None:
    """Register session for client (delegation to repository method)."""
    _ensure_services_initialized()
    repository = get_session_repository()
    repository._register_session_for_client(client_id, session_id)


def _unregister_session_for_client(client_id: str, session_id: str) -> None:
    """Unregister session for client (delegation to repository method)."""
    _ensure_services_initialized()
    repository = get_session_repository()
    repository._unregister_session_for_client(client_id, session_id)


def _restore_workflow_definition(
    session: DynamicWorkflowState, workflows_dir: str = ".accordo/workflows"
) -> None:
    """Restore workflow definition for session."""
    # Delegate to workflow definition cache
    _ensure_services_initialized()
    try:
        from ..services import get_workflow_definition_cache
        cache = get_workflow_definition_cache()
        if hasattr(cache, '_restore_workflow_definition'):
            cache._restore_workflow_definition(session, workflows_dir)
    except Exception:
        pass 