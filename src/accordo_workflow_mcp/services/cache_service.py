"""Cache service for workflow session caching and semantic search."""

from typing import Any, Protocol

from ..logging_config import get_logger
from ..models.cache_models import CacheMetadata, CacheOperationResult, CacheStats
from .cache_storage_service import CacheStorageService, CacheStorageServiceProtocol
from .dependency_injection import get_service, has_service, register_singleton
from .embedding_service import EmbeddingService, EmbeddingServiceProtocol
from .semantic_search_service import SemanticSearchService, SemanticSearchServiceProtocol

logger = get_logger(__name__)


class CacheServiceProtocol(Protocol):
    """Protocol for cache service implementations."""

    def is_available(self) -> bool:
        """Check if cache service is available and functional."""
        ...

    def semantic_search(
        self,
        query_text: str,
        max_results: int = 50,
        min_similarity: float = 0.0,
        client_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform semantic search of cached workflow states."""
        ...

    def store_workflow_state(
        self,
        session_id: str,
        context_text: str,
        metadata: dict[str, Any],
    ) -> CacheOperationResult:
        """Store workflow state with semantic embedding."""
        ...

    def retrieve_workflow_state(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve workflow state by session ID."""
        ...

    def delete_workflow_state(self, session_id: str) -> CacheOperationResult:
        """Delete workflow state by session ID."""
        ...

    def get_cache_stats(self) -> CacheStats | None:
        """Get cache statistics."""
        ...

    def get_all_sessions_for_client(self, client_id: str) -> list[CacheMetadata]:
        """Get all sessions for a specific client."""
        ...

    def cleanup_old_entries(self, max_age_days: int = 30) -> int:
        """Clean up old cache entries."""
        ...

    def get_cache_manager(self):
        """Get the underlying cache manager instance (legacy compatibility)."""
        ...


class CacheService(CacheServiceProtocol):
    """Service for managing workflow session cache and semantic search using decomposed services."""

    def __init__(self, config_service=None):
        """Initialize cache service with configuration.

        Args:
            config_service: Configuration service instance (injected)
        """
        self._config_service = config_service
        self._initialization_attempted = False
        self._initialization_error = None

        # Decomposed services
        self._embedding_service: EmbeddingServiceProtocol | None = None
        self._storage_service: CacheStorageServiceProtocol | None = None
        self._search_service: SemanticSearchServiceProtocol | None = None

        # Legacy compatibility
        self._legacy_cache_manager = None

    def is_available(self) -> bool:
        """Check if cache service is available and functional."""
        if not self._initialization_attempted:
            self._ensure_initialized()
        return (
            self._embedding_service is not None
            and self._storage_service is not None
            and self._search_service is not None
            and self._embedding_service.is_available()
            and self._storage_service.is_initialized()
        )

    def semantic_search(
        self,
        query_text: str,
        max_results: int = 50,
        min_similarity: float = 0.0,
        client_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform semantic search of cached workflow states.

        Args:
            query_text: Text to search for semantically
            max_results: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)
            client_id: Optional client ID filter

        Returns:
            List of workflow metadata with similarity scores
        """
        if not self.is_available():
            logger.warning("Cache service not available for semantic search")
            return []

        try:
            return self._search_service.find_similar_workflows(
                query_text=query_text,
                max_results=max_results,
                min_similarity=min_similarity,
                client_id=client_id,
            )
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def store_workflow_state(
        self,
        session_id: str,
        context_text: str,
        metadata: dict[str, Any],
    ) -> CacheOperationResult:
        """Store workflow state with semantic embedding.

        Args:
            session_id: Unique session identifier
            context_text: Text context for semantic embedding
            metadata: Workflow metadata to store

        Returns:
            CacheOperationResult indicating success/failure
        """
        if not self.is_available():
            return CacheOperationResult(
                success=False,
                error_message="Cache service not available",
                operation_type="store",
            )

        try:
            # Generate embedding
            embeddings = self._embedding_service.get_embeddings([context_text])
            if embeddings is None:
                return CacheOperationResult(
                    success=False,
                    error_message="Failed to generate embedding",
                    operation_type="store",
                )

            # Store with embedding
            return self._storage_service.store_with_embedding(
                session_id=session_id,
                embedding=embeddings[0].tolist(),
                document_text=context_text,
                metadata=metadata,
            )

        except Exception as e:
            return CacheOperationResult(
                success=False,
                error_message=str(e),
                operation_type="store",
            )

    def retrieve_workflow_state(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve workflow state by session ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Dictionary with metadata and document or None if not found
        """
        if not self.is_available():
            return None

        try:
            return self._storage_service.retrieve_by_id(session_id)
        except Exception as e:
            logger.warning(f"Failed to retrieve workflow state for {session_id}: {e}")
            return None

    def delete_workflow_state(self, session_id: str) -> CacheOperationResult:
        """Delete workflow state by session ID.

        Args:
            session_id: Session ID to delete

        Returns:
            CacheOperationResult indicating success/failure
        """
        if not self.is_available():
            return CacheOperationResult(
                success=False,
                error_message="Cache service not available",
                operation_type="delete",
            )

        try:
            return self._storage_service.delete_by_id(session_id)
        except Exception as e:
            return CacheOperationResult(
                success=False,
                error_message=str(e),
                operation_type="delete",
            )

    def get_cache_stats(self) -> CacheStats | None:
        """Get cache statistics.

        Returns:
            CacheStats object or None if unavailable
        """
        if not self.is_available():
            return None

        try:
            return self._storage_service.get_stats()
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return None

    def get_all_sessions_for_client(self, client_id: str) -> list[CacheMetadata]:
        """Get all sessions for a specific client.

        Args:
            client_id: Client ID to filter by

        Returns:
            List of CacheMetadata objects
        """
        if not self.is_available():
            return []

        try:
            return self._storage_service.get_all_sessions_for_client(client_id)
        except Exception as e:
            logger.warning(f"Failed to get sessions for client {client_id}: {e}")
            return []

    def cleanup_old_entries(self, max_age_days: int = 30) -> int:
        """Clean up old cache entries.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of entries cleaned up
        """
        if not self.is_available():
            return 0

        try:
            return self._storage_service.cleanup_old_entries(max_age_days)
        except Exception as e:
            logger.warning(f"Failed to cleanup old entries: {e}")
            return 0

    def get_cache_manager(self):
        """Get the underlying cache manager instance (legacy compatibility).

        Returns:
            Legacy cache manager or None
        """
        if not self._initialization_attempted:
            self._ensure_initialized()
        return self._legacy_cache_manager

    def _ensure_initialized(self):
        """Ensure all cache services are initialized."""
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

            # Ensure cache directory exists
            if not server_config.ensure_cache_dir():
                self._initialization_error = "Failed to create cache directory"
                return

            # Initialize decomposed services
            self._embedding_service = EmbeddingService(
                model_name=server_config.cache_embedding_model
            )

            self._storage_service = CacheStorageService(
                db_path=str(server_config.cache_dir),
                collection_name=server_config.cache_collection_name,
                max_results=server_config.cache_max_results,
            )

            self._search_service = SemanticSearchService(
                embedding_service=self._embedding_service,
                storage_service=self._storage_service,
            )

            # Create legacy cache manager for backward compatibility
            try:
                from ..utils.cache_manager import WorkflowCacheManager

                self._legacy_cache_manager = WorkflowCacheManager(
                    db_path=str(server_config.cache_dir),
                    collection_name=server_config.cache_collection_name,
                    embedding_model=server_config.cache_embedding_model,
                    max_results=server_config.cache_max_results,
                )
            except Exception as legacy_error:
                logger.warning(f"Failed to create legacy cache manager: {legacy_error}")
                # Continue without legacy manager - new services should work

            logger.info(
                "Cache service initialized with decomposed services",
                embedding_model=server_config.cache_embedding_model,
                cache_dir=str(server_config.cache_dir),
                collection_name=server_config.cache_collection_name,
            )

        except Exception as e:
            self._initialization_error = f"Cache initialization failed: {e}"
            logger.error(f"Cache service initialization failed: {e}")


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
