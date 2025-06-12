"""Semantic search service for managing search operations and similarity calculations."""

from typing import Any, Protocol

from ..logging_config import get_logger
from .cache_storage_service import CacheStorageServiceProtocol
from .embedding_service import EmbeddingServiceProtocol

logger = get_logger(__name__)


class SemanticSearchServiceProtocol(Protocol):
    """Protocol for semantic search service implementations."""

    def find_similar_workflows(
        self,
        query_text: str,
        max_results: int = 50,
        min_similarity: float = 0.0,
        client_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find workflows similar to the query text."""
        ...

    def search_with_filters(
        self,
        query_text: str,
        where_filters: dict[str, Any] | None = None,
        max_results: int = 50,
        min_similarity: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search with custom filters and query text."""
        ...

    def is_available(self) -> bool:
        """Check if search service is available."""
        ...


class SemanticSearchService(SemanticSearchServiceProtocol):
    """Service for managing search operations and similarity calculations."""

    def __init__(
        self,
        embedding_service: EmbeddingServiceProtocol,
        storage_service: CacheStorageServiceProtocol,
    ):
        """Initialize the semantic search service.

        Args:
            embedding_service: Service for generating embeddings
            storage_service: Service for storage operations
        """
        self.embedding_service = embedding_service
        self.storage_service = storage_service

    def find_similar_workflows(
        self,
        query_text: str,
        max_results: int = 50,
        min_similarity: float = 0.0,
        client_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find workflows similar to the query text.

        Args:
            query_text: Text to search for similar workflows
            max_results: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)
            client_id: Optional client ID filter

        Returns:
            List of workflow metadata with similarity scores
        """
        try:
            # Check if services are available
            if not self.is_available():
                logger.warning("Search service unavailable: embedding or storage service not ready")
                return []

            # Generate embedding for query
            query_embedding = self.embedding_service.get_embeddings([query_text])
            if query_embedding is None:
                logger.warning("Failed to generate embedding for query text")
                return []

            # Prepare filters
            where_filters = {"client_id": client_id} if client_id else None

            # Perform vector search
            search_results = self.storage_service.query_by_embedding(
                query_embedding=query_embedding[0].tolist(),
                n_results=max_results,
                where_filters=where_filters,
            )

            # Process results and apply similarity filtering
            workflows = []
            distance_metric = self.storage_service.get_distance_metric()

            if (
                search_results
                and search_results.get("ids")
                and len(search_results["ids"]) > 0
                and search_results["ids"][0]  # Check first list is not empty
            ):
                for i, session_id in enumerate(search_results["ids"][0]):
                    try:
                        distance = search_results["distances"][0][i]
                        metadata = search_results["metadatas"][0][i]
                        document = search_results["documents"][0][i]

                        # Convert distance to similarity based on metric
                        similarity = self._convert_distance_to_similarity(distance, distance_metric)

                        # Apply similarity threshold
                        if similarity < min_similarity:
                            continue

                        workflow_data = {
                            "session_id": session_id,
                            "similarity": similarity,
                            "distance": distance,
                            "metadata": metadata,
                            "document": document,
                        }

                        workflows.append(workflow_data)

                    except (IndexError, KeyError, TypeError) as e:
                        logger.warning(f"Error processing search result at index {i}: {e}")
                        continue

            # Sort by similarity descending
            workflows.sort(key=lambda x: x["similarity"], reverse=True)

            logger.info(
                "Semantic search completed",
                query_length=len(query_text),
                results_found=len(workflows),
                max_results=max_results,
                min_similarity=min_similarity,
                distance_metric=distance_metric,
            )

            return workflows

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def search_with_filters(
        self,
        query_text: str,
        where_filters: dict[str, Any] | None = None,
        max_results: int = 50,
        min_similarity: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search with custom filters and query text.

        Args:
            query_text: Text to search for
            where_filters: Custom metadata filters for ChromaDB
            max_results: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of workflow metadata with similarity scores
        """
        try:
            # Check if services are available
            if not self.is_available():
                logger.warning("Search service unavailable: embedding or storage service not ready")
                return []

            # Generate embedding for query
            query_embedding = self.embedding_service.get_embeddings([query_text])
            if query_embedding is None:
                logger.warning("Failed to generate embedding for query text")
                return []

            # Perform vector search with custom filters
            search_results = self.storage_service.query_by_embedding(
                query_embedding=query_embedding[0].tolist(),
                n_results=max_results,
                where_filters=where_filters,
            )

            # Process results and apply similarity filtering
            workflows = []
            distance_metric = self.storage_service.get_distance_metric()

            if (
                search_results
                and search_results.get("ids")
                and len(search_results["ids"]) > 0
                and search_results["ids"][0]  # Check first list is not empty
            ):
                for i, session_id in enumerate(search_results["ids"][0]):
                    try:
                        distance = search_results["distances"][0][i]
                        metadata = search_results["metadatas"][0][i]
                        document = search_results["documents"][0][i]

                        # Convert distance to similarity based on metric
                        similarity = self._convert_distance_to_similarity(distance, distance_metric)

                        # Apply similarity threshold
                        if similarity < min_similarity:
                            continue

                        workflow_data = {
                            "session_id": session_id,
                            "similarity": similarity,
                            "distance": distance,
                            "metadata": metadata,
                            "document": document,
                        }

                        workflows.append(workflow_data)

                    except (IndexError, KeyError, TypeError) as e:
                        logger.warning(f"Error processing search result at index {i}: {e}")
                        continue

            # Sort by similarity descending
            workflows.sort(key=lambda x: x["similarity"], reverse=True)

            logger.info(
                "Filtered semantic search completed",
                query_length=len(query_text),
                results_found=len(workflows),
                max_results=max_results,
                min_similarity=min_similarity,
                filters=where_filters,
                distance_metric=distance_metric,
            )

            return workflows

        except Exception as e:
            logger.error(f"Filtered semantic search failed: {e}")
            return []

    def is_available(self) -> bool:
        """Check if search service is available.

        Returns:
            bool: True if both embedding and storage services are available
        """
        return (
            self.embedding_service.is_available()
            and self.storage_service.is_initialized()
        )

    def _convert_distance_to_similarity(self, distance: float, metric: str) -> float:
        """Convert distance to similarity score based on distance metric.

        Args:
            distance: Distance value from ChromaDB
            metric: Distance metric used ('l2', 'cosine', 'ip')

        Returns:
            float: Similarity score between 0.0 and 1.0
        """
        try:
            if metric == "cosine":
                # Cosine distance: distance = 1 - cosine_similarity
                # So similarity = 1 - distance
                # Clamp to [0, 1] range
                return max(0.0, min(1.0, 1.0 - distance))
            elif metric == "ip":  # Inner product
                # Inner product: higher values = more similar
                # For normalized vectors, IP ranges from -1 to 1
                # Convert to 0-1 similarity: (ip + 1) / 2
                return max(0.0, min(1.0, (distance + 1.0) / 2.0))
            else:  # l2 (Euclidean) or unknown
                # L2 distance: lower values = more similar
                # Convert using exponential decay: e^(-distance)
                # This gives similarity in (0, 1] range
                import math
                return max(0.0, min(1.0, math.exp(-distance)))
        except (ValueError, OverflowError, TypeError):
            # Fallback for any numerical issues
            return 0.0 