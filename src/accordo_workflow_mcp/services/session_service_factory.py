"""Session service factory for creating and configuring session services."""

import contextlib
from typing import Any

from .dependency_injection import ServiceRegistry, get_service
from .session_lifecycle_manager import (
    SessionLifecycleManager,
    SessionLifecycleManagerProtocol,
)
from .session_repository import SessionRepository, SessionRepositoryProtocol
from .session_sync_service import SessionSyncService, SessionSyncServiceProtocol
from .workflow_definition_cache import (
    WorkflowDefinitionCache,
    WorkflowDefinitionCacheProtocol,
)


class SessionServiceFactory:
    """Factory for creating and configuring session services."""

    def __init__(self, service_registry: ServiceRegistry) -> None:
        self._service_registry = service_registry
        self._initialized = False

    def initialize_session_services(self) -> None:
        """Initialize and register all session services."""
        if self._initialized:
            print("🚨 DEBUG: SessionServiceFactory already initialized, skipping")
            return

        print("🚨 DEBUG: SessionServiceFactory.initialize_session_services() called")

        # Initialize cache service first to ensure it's available
        try:
            from .cache_service import initialize_cache_service

            initialize_cache_service()
            print("🚨 DEBUG: Cache service initialized successfully")
        except Exception as e:
            print(f"🚨 DEBUG: Cache service initialization failed: {e}")

        # Create core services
        print("🚨 DEBUG: Creating SessionRepository...")
        session_repository = SessionRepository()

        print("🚨 DEBUG: Creating WorkflowDefinitionCache...")
        workflow_definition_cache = WorkflowDefinitionCache()

        # Get cache manager if available
        print("🚨 DEBUG: Getting cache manager for SessionSyncService...")
        cache_manager = self._get_cache_manager()
        print(f"🚨 DEBUG: Cache manager for SessionSyncService: {cache_manager}")

        # Create dependent services
        print("🚨 DEBUG: Creating SessionSyncService...")
        session_sync_service = SessionSyncService(
            session_repository=session_repository, cache_manager=cache_manager
        )

        print("🚨 DEBUG: Creating SessionLifecycleManager...")
        session_lifecycle_manager = SessionLifecycleManager(
            session_repository=session_repository,
            session_sync_service=session_sync_service,
            cache_manager=cache_manager,
        )

        print("🚨 DEBUG: Registering services with dependency injection...")

        # Register services with dependency injection
        self._service_registry.register_service(
            SessionRepositoryProtocol, session_repository
        )
        self._service_registry.register_service(
            SessionSyncServiceProtocol, session_sync_service
        )
        self._service_registry.register_service(
            SessionLifecycleManagerProtocol, session_lifecycle_manager
        )
        self._service_registry.register_service(
            WorkflowDefinitionCacheProtocol, workflow_definition_cache
        )

        # Register concrete classes as well for direct access
        self._service_registry.register_service(SessionRepository, session_repository)
        self._service_registry.register_service(
            SessionSyncService, session_sync_service
        )
        self._service_registry.register_service(
            SessionLifecycleManager, session_lifecycle_manager
        )
        self._service_registry.register_service(
            WorkflowDefinitionCache, workflow_definition_cache
        )

        print("🚨 DEBUG: SessionServiceFactory initialization complete")
        self._initialized = True

    def get_session_repository(self) -> SessionRepository:
        """Get the session repository service."""
        self.initialize_session_services()
        return get_service(SessionRepository)

    def get_session_sync_service(self) -> SessionSyncService:
        """Get the session sync service."""
        self.initialize_session_services()
        return get_service(SessionSyncService)

    def get_session_lifecycle_manager(self) -> SessionLifecycleManager:
        """Get the session lifecycle manager."""
        self.initialize_session_services()
        return get_service(SessionLifecycleManager)

    def get_workflow_definition_cache(self) -> WorkflowDefinitionCache:
        """Get the workflow definition cache."""
        self.initialize_session_services()
        return get_service(WorkflowDefinitionCache)

    def _get_cache_manager(self) -> Any:
        """Get cache manager for SessionSyncService."""
        print("🚨 DEBUG: SessionServiceFactory._get_cache_manager() called")

        # Try to get cache manager from the new cache service first
        print("🚨 DEBUG: Trying to get cache manager from new cache service...")
        with contextlib.suppress(Exception):
            from .cache_service import get_cache_service

            cache_service = get_cache_service()
            if cache_service and hasattr(cache_service, "get_cache_manager"):
                cache_manager = cache_service.get_cache_manager()
                if cache_manager:
                    print(
                        f"🚨 DEBUG: Got cache manager from cache service: {type(cache_manager)}"
                    )
                    return cache_manager

        print("🚨 DEBUG: New cache service not available")

        # Fallback to legacy session manager cache
        print("🚨 DEBUG: Falling back to legacy session manager cache...")
        from ..utils import session_manager

        cache_manager = session_manager.get_cache_manager()
        print(
            f"🚨 DEBUG: Got cache manager from legacy session manager: {type(cache_manager)}"
        )

        return cache_manager

    def is_initialized(self) -> bool:
        """Check if services are initialized."""
        return self._initialized

    def reset_services(self) -> None:
        """Reset all services (for testing)."""
        self._initialized = False
        # Clear all registrations
        with contextlib.suppress(Exception):
            self._service_registry.clear_registry()


# Global factory instance
_session_service_factory: SessionServiceFactory | None = None


def get_session_service_factory() -> SessionServiceFactory:
    """Get the global session service factory."""
    global _session_service_factory

    if _session_service_factory is None:
        from .dependency_injection import get_service_registry

        service_registry = get_service_registry()
        _session_service_factory = SessionServiceFactory(service_registry)
    else:
        # Check if the factory's service registry is still valid
        # If the registry was cleared (e.g., during tests), reset the factory
        from .dependency_injection import get_service_registry

        current_registry = get_service_registry()
        if _session_service_factory._service_registry is not current_registry:
            _session_service_factory = SessionServiceFactory(current_registry)

    return _session_service_factory


def initialize_session_services() -> None:
    """Initialize all session services."""
    factory = get_session_service_factory()
    factory.initialize_session_services()


def reset_session_services() -> None:
    """Reset all session services (for testing)."""
    global _session_service_factory

    if _session_service_factory is not None:
        _session_service_factory.reset_services()
        _session_service_factory = None

    # Also clear the global registry
    from .dependency_injection import clear_registry

    clear_registry()


# Convenience functions for getting services
def get_session_repository() -> SessionRepository:
    """Get the session repository service."""
    return get_session_service_factory().get_session_repository()


def get_session_sync_service() -> SessionSyncService:
    """Get the session sync service."""
    return get_session_service_factory().get_session_sync_service()


def get_session_lifecycle_manager() -> SessionLifecycleManager:
    """Get the session lifecycle manager."""
    return get_session_service_factory().get_session_lifecycle_manager()


def get_workflow_definition_cache() -> WorkflowDefinitionCache:
    """Get the workflow definition cache."""
    return get_session_service_factory().get_workflow_definition_cache()
