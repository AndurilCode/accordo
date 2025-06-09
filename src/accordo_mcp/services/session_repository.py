"""Session repository service for core CRUD operations and session management."""

import threading
from datetime import UTC, datetime
from typing import Any, Protocol

from ..models.workflow_state import DynamicWorkflowState
from ..models.yaml_workflow import WorkflowDefinition


class SessionRepositoryProtocol(Protocol):
    """Protocol for session repository operations."""

    def get_session(self, session_id: str) -> DynamicWorkflowState | None:
        """Get a session by ID."""
        ...

    def create_session(
        self,
        client_id: str,
        task_description: str,
        workflow_def: WorkflowDefinition,
        workflow_file: str | None = None,
    ) -> DynamicWorkflowState:
        """Create a new dynamic session."""
        ...

    def update_session(self, session_id: str, **kwargs: Any) -> bool:
        """Update session with provided fields."""
        ...

    def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID."""
        ...

    def get_sessions_by_client(self, client_id: str) -> list[DynamicWorkflowState]:
        """Get all sessions for a client."""
        ...

    def get_all_sessions(self) -> dict[str, DynamicWorkflowState]:
        """Get all sessions."""
        ...

    def get_session_stats(self) -> dict[str, int]:
        """Get session statistics."""
        ...

    def get_session_type(self, session_id: str) -> str | None:
        """Get session type."""
        ...


class SessionRepository:
    """Session repository implementation with thread-safe operations."""

    def __init__(self) -> None:
        self._sessions: dict[str, DynamicWorkflowState] = {}
        self._client_session_registry: dict[str, list[str]] = {}
        self._lock = threading.Lock()
        self._registry_lock = threading.Lock()

    def get_session(self, session_id: str) -> DynamicWorkflowState | None:
        """Get a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def create_session(
        self,
        client_id: str,
        task_description: str,
        workflow_def: WorkflowDefinition,
        workflow_file: str | None = None,
    ) -> DynamicWorkflowState:
        """Create a new dynamic session."""
        from uuid import uuid4

        session_id = str(uuid4())

        # Prepare dynamic inputs
        inputs = self._prepare_dynamic_inputs(task_description, workflow_def)

        # Create the session
        session = DynamicWorkflowState(
            session_id=session_id,
            client_id=client_id,
            created_at=datetime.now(UTC),
            workflow_name=workflow_def.name,
            workflow_file=workflow_file,
            current_node=workflow_def.workflow.root,
            status="READY",
            inputs=inputs,
            node_outputs={},
            current_item=task_description,
            items=[],
            log=[],
            archive_log=[],
        )

        with self._lock:
            self._sessions[session_id] = session

        # Register session for client
        self._register_session_for_client(client_id, session_id)

        # FIX: Automatically sync new session to cache for persistence across restarts
        # ISSUE: Previously, sessions were only cached during workflow transitions (updates),
        # not during initial creation. This meant sessions created but not progressed were
        # lost when the MCP server restarted (e.g., when Cursor was killed).
        # SOLUTION: Add immediate cache sync after session creation to ensure all sessions
        # survive server restarts, eliminating the race condition between creation and first update.
        try:
            self._sync_session_to_cache(session)
        except Exception as e:
            # Non-blocking: don't prevent session creation if cache sync fails
            print(
                f"Warning: Failed to sync new session {session_id[:8]} to cache during creation: {e}"
            )

        return session

    def update_session(self, session_id: str, **kwargs: Any) -> bool:
        """Update session with provided fields."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False

            # Update fields
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)

            return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if not session:
                return False

        # Unregister from client
        self._unregister_session_for_client(session.client_id, session_id)
        return True

    def get_sessions_by_client(self, client_id: str) -> list[DynamicWorkflowState]:
        """Get all sessions for a client."""
        with self._registry_lock:
            session_ids = self._client_session_registry.get(client_id, [])

        sessions = []
        with self._lock:
            for session_id in session_ids:
                if session := self._sessions.get(session_id):
                    sessions.append(session)

        return sessions

    def get_all_sessions(self) -> dict[str, DynamicWorkflowState]:
        """Get all sessions."""
        with self._lock:
            return self._sessions.copy()

    def get_session_stats(self) -> dict[str, int]:
        """Get session statistics."""
        with self._lock:
            sessions = list(self._sessions.values())

        stats = {
            "total_sessions": len(sessions),
            "running_sessions": len([s for s in sessions if s.status == "RUNNING"]),
            "completed_sessions": len([s for s in sessions if s.status == "COMPLETED"]),
            "failed_sessions": len([s for s in sessions if s.status == "FAILED"]),
        }

        # Count by client
        clients = set(s.client_id for s in sessions)
        stats["total_clients"] = len(clients)

        return stats

    def get_session_type(self, session_id: str) -> str | None:
        """Get session type."""
        session = self.get_session(session_id)
        if not session:
            return None

        # Determine type based on workflow name
        if hasattr(session, "workflow_name") and session.workflow_name:
            return "dynamic"
        return "legacy"

    def _prepare_dynamic_inputs(
        self, task_description: str, workflow_def: WorkflowDefinition
    ) -> dict[str, Any]:
        """Prepare dynamic inputs based on workflow definition."""
        inputs: dict[str, Any] = {}

        # Always ensure task_description is included
        inputs["task_description"] = task_description

        # Add other inputs from workflow definition with defaults
        for input_name, input_spec in workflow_def.inputs.items():
            if input_name == "task_description":
                continue  # Already handled

            # Set default values based on type
            input_type = input_spec.type
            if input_type == "boolean":
                inputs[input_name] = (
                    input_spec.default if input_spec.default is not None else False
                )
            elif input_type == "integer":
                inputs[input_name] = (
                    input_spec.default if input_spec.default is not None else 0
                )
            elif input_type == "array":
                inputs[input_name] = (
                    input_spec.default if input_spec.default is not None else []
                )
            else:  # string or others
                inputs[input_name] = (
                    input_spec.default if input_spec.default is not None else ""
                )

        return inputs

    def _register_session_for_client(self, client_id: str, session_id: str) -> None:
        """Register a session for a client."""
        with self._registry_lock:
            if client_id not in self._client_session_registry:
                self._client_session_registry[client_id] = []
            if session_id not in self._client_session_registry[client_id]:
                self._client_session_registry[client_id].append(session_id)

    def _unregister_session_for_client(self, client_id: str, session_id: str) -> None:
        """Unregister a session from a client."""
        with self._registry_lock:
            if client_id in self._client_session_registry:
                try:
                    self._client_session_registry[client_id].remove(session_id)
                    if not self._client_session_registry[client_id]:
                        del self._client_session_registry[client_id]
                except ValueError:
                    pass  # Session not in list

    def _sync_session_to_cache(self, session: DynamicWorkflowState) -> bool:
        """Sync session to cache when cache is available.

        Args:
            session: The session to sync to cache

        Returns:
            bool: True if sync succeeded or was skipped, False on error
        """
        try:
            # Import cache manager dynamically to avoid circular imports
            from ..services import get_cache_service

            # Check if cache service is available first
            try:
                cache_service = get_cache_service()
            except Exception as e:
                # Cache service not initialized or not available
                print(
                    f"Debug: Cache service not available during session creation: {e}"
                )
                return True  # Not an error - cache may be disabled

            if not cache_service or not cache_service.is_available():
                # Cache not available - this is normal if cache mode disabled
                print(
                    f"Debug: Cache service not available for session {session.session_id[:8]} - cache mode may be disabled"
                )
                return True

            try:
                cache_manager = cache_service.get_cache_manager()
            except Exception as e:
                print(
                    f"Debug: Failed to get cache manager for session {session.session_id[:8]}: {e}"
                )
                return True  # Not blocking

            if not cache_manager:
                print(
                    f"Debug: Cache manager is None for session {session.session_id[:8]}"
                )
                return True

            # Validate session before caching
            if not session.session_id:
                print("Warning: Cannot cache session with empty session_id")
                return False

            # Store session in cache
            result = cache_manager.store_workflow_state(session)

            # Log success/failure for debugging
            if result and result.success:
                print(
                    f"Debug: Session {session.session_id[:8]} successfully cached during creation"
                )
                return True
            else:
                error_msg = result.error_message if result else "Unknown error"
                print(
                    f"Debug: Failed to cache session {session.session_id[:8]} during creation: {error_msg}"
                )
                return False

        except ImportError as e:
            # Cache services not available - might be in test environment or cache disabled
            print(
                f"Debug: Cache services not importable for session {session.session_id[:8]}: {e}"
            )
            return True  # Not an error in this context
        except Exception as e:
            # Non-blocking: cache failures shouldn't prevent session creation
            print(
                f"Debug: Exception during cache sync for session {session.session_id[:8]}: {e}"
            )
            return False
