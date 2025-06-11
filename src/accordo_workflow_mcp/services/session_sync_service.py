"""Session sync service for file and cache persistence operations."""

import json
import threading
from pathlib import Path
from typing import Any, Protocol

from ..models.workflow_state import DynamicWorkflowState
from ..utils.yaml_loader import WorkflowLoader


class SessionSyncServiceProtocol(Protocol):
    """Protocol for session sync operations."""

    def sync_session_to_file(
        self, session_id: str, session: DynamicWorkflowState | None = None
    ) -> bool:
        """Sync session to file storage."""
        ...

    def sync_session_to_cache(
        self, session_id: str, session: DynamicWorkflowState | None = None
    ) -> bool:
        """Sync session to cache storage."""
        ...

    def sync_session(self, session_id: str) -> bool:
        """Sync session to both file and cache."""
        ...

    def force_cache_sync_session(self, session_id: str) -> dict[str, Any]:
        """Force sync session to cache with detailed results."""
        ...

    def restore_sessions_from_cache(self, client_id: str | None = None) -> int:
        """Restore sessions from cache storage."""
        ...

    def auto_restore_sessions_on_startup(self) -> int:
        """Auto-restore sessions on startup."""
        ...

    def list_cached_sessions(
        self, client_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List cached sessions."""
        ...


class SessionSyncService:
    """Session sync service implementation for file and cache persistence."""

    def __init__(self, session_repository: Any, cache_manager: Any = None) -> None:
        self._session_repository = session_repository
        self._cache_manager = cache_manager
        self._lock = threading.Lock()

    def sync_session_to_file(
        self, session_id: str, session: DynamicWorkflowState | None = None
    ) -> bool:
        """Sync session to file storage."""
        if session is None:
            session = self._session_repository.get_session(session_id)

        if not session:
            return False

        try:
            # Get server config to determine file settings
            server_config = self._get_effective_server_config()
            if not server_config or not server_config.enable_local_state_file:
                return True  # Not enabled, consider success

            # Ensure sessions directory exists
            sessions_dir = Path(server_config.get_sessions_dir())
            sessions_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename
            filename = self._generate_unique_session_filename(
                session_id, server_config.local_state_file_format, sessions_dir
            )

            file_path = sessions_dir / filename

            # Prepare session data
            session_data = session.model_dump()

            # Write to file based on format
            if server_config.local_state_file_format.upper() == "JSON":
                with open(file_path, "w") as f:
                    json.dump(session_data, f, indent=2, default=str)
            else:  # Markdown
                markdown_content = self._session_to_markdown(session)
                with open(file_path, "w") as f:
                    f.write(markdown_content)

            return True

        except Exception as e:
            print(f"Warning: Failed to sync session {session_id} to file: {e}")
            return False

    def sync_session_to_cache(
        self, session_id: str, session: DynamicWorkflowState | None = None
    ) -> bool:
        """Sync session to cache storage."""
        if not self._cache_manager:
            return True  # No cache manager, consider success

        if session is None:
            session = self._session_repository.get_session(session_id)

        if not session:
            return False

        try:
            # Store session in cache using the correct method name
            result = self._cache_manager.store_workflow_state(session)

            if result.success:
                return True
            else:
                print(
                    f"Warning: Failed to sync session {session_id} to cache: {result.error_message}"
                )
                return False

        except Exception as e:
            print(f"Warning: Failed to sync session {session_id} to cache: {e}")
            return False

    def sync_session(self, session_id: str) -> bool:
        """Sync session to both file and cache."""
        session = self._session_repository.get_session(session_id)
        if not session:
            return False

        file_success = self.sync_session_to_file(session_id, session)
        cache_success = self.sync_session_to_cache(session_id, session)

        return file_success and cache_success

    def force_cache_sync_session(self, session_id: str) -> dict[str, Any]:
        """Force sync session to cache with detailed results."""
        result: dict[str, Any] = {
            "session_id": session_id,
            "success": False,
            "message": "",
            "cache_enabled": False,
        }

        if not self._cache_manager:
            result["message"] = "Cache manager not available"
            return result

        result["cache_enabled"] = True

        session = self._session_repository.get_session(session_id)
        if not session:
            result["message"] = f"Session {session_id} not found"
            return result

        try:
            success = self.sync_session_to_cache(session_id, session)
            result["success"] = success
            result["message"] = (
                "Successfully synced to cache" if success else "Failed to sync to cache"
            )

        except Exception as e:
            result["message"] = f"Error syncing to cache: {e}"

        return result

    def restore_sessions_from_cache(self, client_id: str | None = None) -> int:
        """Restore sessions from cache storage."""
        if not self._cache_manager:
            return 0

        try:
            # Default to "default" client if None or empty string is passed - this is the standard client_id
            # used by the MCP server when no specific client is specified
            effective_client_id = (
                client_id if client_id and client_id.strip() else "default"
            )

            # Debug logging to track restoration process
            print(
                f"DEBUG: Restoring sessions for client_id='{effective_client_id}' (original: {repr(client_id)})"
            )

            # WORKAROUND: Instead of using problematic get_all_sessions_for_client() with ChromaDB metadata filtering,
            # get all sessions from cache and filter them ourselves using working session_id based retrieval

            # Get cache stats to access all session metadata
            cache_stats = self._cache_manager.get_cache_stats()
            if not cache_stats or cache_stats.total_entries == 0:
                print("DEBUG: No sessions found in cache")
                return 0

            # Use the working approach: get all session IDs using proper cache manager method
            try:
                # Get all session IDs from cache using the proper method
                all_session_ids = self._cache_manager.get_all_session_ids()

                if not all_session_ids:
                    print("DEBUG: No session IDs found in cache")
                    return 0

                print(f"DEBUG: Found {len(all_session_ids)} total sessions in cache")

                restored_count = 0
                for session_id in all_session_ids:
                    try:
                        # Use the working retrieve_workflow_state method for individual session lookup
                        session = self._cache_manager.retrieve_workflow_state(
                            session_id
                        )
                        if not session:
                            print(
                                f"DEBUG: Could not retrieve session {session_id[:8]}..."
                            )
                            continue

                        # Filter by client_id after retrieval (since direct filtering doesn't work)
                        if session.client_id != effective_client_id:
                            continue  # Skip sessions that don't match our target client

                        print(
                            f"DEBUG: Restoring session {session_id[:8]}... for client {session.client_id}"
                        )

                        # Restore workflow definition
                        self._restore_workflow_definition(session)

                        # Store in repository using proper repository storage
                        with self._session_repository._lock:
                            self._session_repository._sessions[session.session_id] = (
                                session
                            )

                        # Register for client using repository method
                        self._session_repository._register_session_for_client(
                            session.client_id, session.session_id
                        )

                        print(
                            f"DEBUG: Successfully restored session {session_id[:8]}... to repository"
                        )
                        restored_count += 1

                    except Exception as e:
                        print(f"Warning: Failed to restore session {session_id}: {e}")
                        continue

                print(
                    f"DEBUG: Session restoration completed. Restored {restored_count} sessions for client '{effective_client_id}'"
                )
                return restored_count

            except Exception as e:
                print(
                    f"WARNING: Direct cache access failed, falling back to empty result: {e}"
                )
                return 0

        except Exception as e:
            print(f"Warning: Failed to restore sessions from cache: {e}")
            import traceback

            traceback.print_exc()
            return 0

    def auto_restore_sessions_on_startup(self) -> int:
        """Auto-restore sessions on startup."""
        # TEMPORARY DEBUG: Create visible evidence that this method is called
        print("=" * 80)
        print("🚨 DEBUG: auto_restore_sessions_on_startup() CALLED!")
        print("=" * 80)

        server_config = self._get_effective_server_config()
        if not server_config or not server_config.enable_cache_mode:
            print("🚨 DEBUG: Cache mode not enabled or no server config")
            return 0

        print("🚨 DEBUG: Cache mode enabled, calling restore_sessions_from_cache()")
        result = self.restore_sessions_from_cache()
        print(f"🚨 DEBUG: auto_restore_sessions_on_startup() returning {result}")
        return result

    def list_cached_sessions(
        self, client_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List cached sessions."""
        if not self._cache_manager:
            return []

        try:
            if client_id:
                session_metadata_list = self._cache_manager.get_all_sessions_for_client(
                    client_id
                )
                sessions_info = []

                for metadata in session_metadata_list:
                    sessions_info.append(
                        {
                            "session_id": metadata.session_id,
                            "workflow_name": metadata.workflow_name,
                            "status": metadata.status,
                            "current_node": metadata.current_node,
                            "created_at": metadata.created_at.isoformat(),
                            "last_updated": metadata.last_updated.isoformat(),
                            "task_description": metadata.current_item
                            if metadata.current_item
                            else "No description",
                        }
                    )

                return sessions_info
            else:
                # Get cache stats to show available sessions
                cache_stats = self._cache_manager.get_cache_stats()
                if cache_stats:
                    return [
                        {
                            "total_cached_sessions": cache_stats.total_entries,
                            "active_sessions": cache_stats.active_sessions,
                            "completed_sessions": cache_stats.completed_sessions,
                            "oldest_entry": cache_stats.oldest_entry.isoformat()
                            if cache_stats.oldest_entry
                            else None,
                            "newest_entry": cache_stats.newest_entry.isoformat()
                            if cache_stats.newest_entry
                            else None,
                        }
                    ]

                return []
        except Exception as e:
            print(f"Warning: Failed to list cached sessions: {e}")
            return []

    def _generate_unique_session_filename(
        self, session_id: str, format_ext: str, sessions_dir: Path
    ) -> str:
        """Generate unique session filename."""
        import re
        from datetime import datetime

        # Clean session_id for filename
        clean_session_id = re.sub(r'[<>:"/\\|?*]', "_", session_id)[:50]

        # Get current timestamp
        from datetime import UTC

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        # Determine extension
        ext = "json" if format_ext.upper() == "JSON" else "md"

        # Find next available counter
        counter = 1
        while True:
            filename = f"{clean_session_id}_{timestamp}_{counter:03d}.{ext}"
            if not (sessions_dir / filename).exists():
                return filename
            counter += 1

    def _session_to_markdown(self, session: DynamicWorkflowState) -> str:
        """Convert session to markdown format."""
        import contextlib

        export_session_to_markdown = None
        with contextlib.suppress(ImportError):
            from ..prompts.formatting import export_session_to_markdown  # type: ignore

        # Try to get workflow definition for proper formatting
        workflow_def = None
        try:
            from .workflow_definition_cache import WorkflowDefinitionCache

            cache_service = WorkflowDefinitionCache()
            workflow_def = cache_service.get_workflow_definition_from_cache(
                session.session_id
            )
        except Exception:
            pass

        if workflow_def and export_session_to_markdown is not None:
            result = export_session_to_markdown(session.session_id, workflow_def)
            return result if result is not None else self._fallback_markdown(session)
        else:
            return self._fallback_markdown(session)

    def _fallback_markdown(self, session: DynamicWorkflowState) -> str:
        """Generate fallback markdown format."""
        lines = [
            f"# Session: {session.session_id}",
            "",
            f"**Client ID**: {session.client_id}",
            f"**Workflow**: {session.workflow_name or 'Unknown'}",
            f"**Status**: {session.status}",
            f"**Created**: {session.created_at}",
            f"**Current Node**: {session.current_node}",
            "",
            "## Inputs",
            "```json",
            json.dumps(session.inputs, indent=2),
            "```",
            "",
            "## Log",
        ]

        for entry in session.log:
            lines.append(f"- {entry}")

        return "\n".join(lines)

    def _generate_session_context_text(self, session: DynamicWorkflowState) -> str:
        """Generate context text for cache storage."""
        context_parts = [
            f"Session: {session.session_id}",
            f"Client: {session.client_id}",
            f"Workflow: {session.workflow_name or 'Unknown'}",
            f"Status: {session.status}",
            f"Current Node: {session.current_node}",
        ]

        # Add inputs
        if session.inputs:
            context_parts.append("Inputs:")
            for key, value in session.inputs.items():
                context_parts.append(f"  {key}: {value}")

        # Add log entries
        if session.log:
            context_parts.append("Log:")
            for entry in session.log[-5:]:  # Last 5 entries
                context_parts.append(f"  {entry}")

        return "\n".join(context_parts)

    def _restore_workflow_definition(
        self,
        session: DynamicWorkflowState,
        workflows_dir: str = ".accordo/workflows",
    ) -> None:
        """Restore workflow definition for a session."""
        if not session.workflow_file:
            return

        try:
            workflow_path = Path(workflows_dir) / session.workflow_file
            if workflow_path.exists():
                loader = WorkflowLoader()
                workflow_def = loader.load_workflow(str(workflow_path))

                # Store in cache for future use
                if workflow_def is not None:
                    try:
                        from .workflow_definition_cache import WorkflowDefinitionCache

                        cache_service = WorkflowDefinitionCache()
                        cache_service.store_workflow_definition_in_cache(
                            session.session_id, workflow_def
                        )
                    except Exception:
                        pass

        except Exception as e:
            print(
                f"Warning: Failed to restore workflow definition for session {session.session_id}: {e}"
            )

    def _get_effective_server_config(self) -> Any:
        """Get effective server configuration."""
        print("🚨 DEBUG: _get_effective_server_config() called")

        try:
            from ..services.config_service import ConfigurationService
            from ..services.dependency_injection import get_service

            print(
                "🚨 DEBUG: Trying to get ConfigurationService via dependency injection..."
            )
            config_service = get_service(ConfigurationService)
            if config_service:
                legacy_config = config_service.to_legacy_server_config()
                print(
                    f"🚨 DEBUG: Got config via DI - enable_cache_mode: {getattr(legacy_config, 'enable_cache_mode', None)}"
                )
                return legacy_config
            else:
                print(
                    "🚨 DEBUG: ConfigurationService not found via dependency injection"
                )
        except Exception as e:
            print(f"🚨 DEBUG: Exception getting config via DI: {e}")

        try:
            from ..services.config_service import get_configuration_service

            print("🚨 DEBUG: Trying get_configuration_service()...")
            config_service = get_configuration_service()
            legacy_config = config_service.to_legacy_server_config()
            print(
                f"🚨 DEBUG: Got config via get_configuration_service() - enable_cache_mode: {getattr(legacy_config, 'enable_cache_mode', None)}"
            )
            return legacy_config
        except Exception as e:
            print(
                f"🚨 DEBUG: Exception getting config via get_configuration_service(): {e}"
            )

        # FALLBACK: Try to detect cache mode from environment or server state
        print("🚨 DEBUG: Trying fallback config detection...")
        try:
            # Check if cache manager exists (indicates cache mode is enabled)
            if self._cache_manager is not None:
                print("🚨 DEBUG: Cache manager exists, assuming cache mode enabled")

                # Create a minimal config object with cache mode enabled
                class FallbackConfig:
                    def __init__(self):
                        self.enable_cache_mode = True

                return FallbackConfig()
            else:
                print("🚨 DEBUG: No cache manager, cache mode disabled")
        except Exception as e:
            print(f"🚨 DEBUG: Exception in fallback detection: {e}")

        print("🚨 DEBUG: No config found, returning None")
        return None
