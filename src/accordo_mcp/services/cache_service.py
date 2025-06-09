"""Cache service for workflow session caching and semantic search."""

from typing import Protocol

from .dependency_injection import get_service, has_service, register_singleton


class CacheServiceProtocol(Protocol):
    """Protocol for cache service implementations."""

    def is_available(self) -> bool:
        """Check if cache service is available and functional."""
        ...

    def get_cache_manager(self):
        """Get the underlying cache manager instance."""
        ...


class CacheService(CacheServiceProtocol):
    """Service for managing workflow session cache and semantic search."""

    def __init__(self, config_service=None):
        """Initialize cache service with configuration.

        Args:
            config_service: Configuration service instance (injected)
        """
        self._cache_manager = None
        self._config_service = config_service
        self._initialization_attempted = False
        self._initialization_error = None

    def is_available(self) -> bool:
        """Check if cache service is available and functional."""
        if not self._initialization_attempted:
            self._ensure_initialized()
        return self._cache_manager is not None

    def get_cache_manager(self):
        """Get the underlying cache manager instance."""
        if not self._initialization_attempted:
            self._ensure_initialized()
        return self._cache_manager

    def _ensure_initialized(self):
        """Ensure cache manager is initialized."""
        if self._initialization_attempted:
            return

        self._initialization_attempted = True

        try:
            # Get configuration from service
            if not self._config_service:
                from .config_service import get_configuration_service

                self._config_service = get_configuration_service()

            # Check if cache mode is enabled
            server_config = self._config_service.to_legacy_server_config()
            if not server_config.enable_cache_mode:
                self._initialization_error = "Cache mode not enabled in configuration"
                return

            # Import and create cache manager
            from ..utils.cache_manager import WorkflowCacheManager

            # Ensure cache directory exists
            if not server_config.ensure_cache_dir():
                self._initialization_error = "Failed to create cache directory"
                return

            # Create cache manager
            self._cache_manager = WorkflowCacheManager(
                db_path=str(server_config.cache_dir),
                collection_name=server_config.cache_collection_name,
                embedding_model=server_config.cache_embedding_model,
                max_results=server_config.cache_max_results,
            )

        except Exception as e:
            self._initialization_error = f"Cache initialization failed: {e}"
            self._cache_manager = None


def _create_cache_service() -> CacheService:
    """Factory function to create cache service instance."""
    return CacheService()


def get_cache_service() -> CacheService:
    """Get the cache service instance.

    Returns:
        CacheService instance
    """
    return get_service(CacheService)


def initialize_cache_service() -> None:
    """Initialize the cache service singleton."""
    if not has_service(CacheService):
        register_singleton(CacheService, _create_cache_service)


def reset_cache_service() -> None:
    """Reset cache service (primarily for testing)."""
    # Note: This clears entire registry, so it's mainly for tests
    pass  # Individual service reset would need registry enhancement
