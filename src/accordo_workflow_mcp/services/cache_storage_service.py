"""Cache storage service for ChromaDB persistence operations."""

import contextlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import chromadb
from chromadb.config import Settings
# Collection type is part of chromadb

from ..logging_config import get_logger
from ..models.cache_models import CacheMetadata, CacheOperationResult, CacheStats
from ..models.workflow_state import DynamicWorkflowState

logger = get_logger(__name__)


class CacheStorageServiceProtocol(Protocol):
    """Protocol for cache storage service implementations."""

    def is_initialized(self) -> bool:
        """Check if storage service is initialized."""
        ...

    def ensure_initialized(self) -> bool:
        """Ensure storage service is initialized."""
        ...

    def store_with_embedding(
        self, 
        session_id: str, 
        embedding: list[float], 
        document_text: str, 
        metadata: dict[str, Any]
    ) -> CacheOperationResult:
        """Store data with pre-computed embedding."""
        ...

    def retrieve_by_id(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve stored data by session ID."""
        ...

    def query_by_embedding(
        self,
        query_embedding: list[float],
        n_results: int = 50,
        where_filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Query storage using embedding vector."""
        ...

    def delete_by_id(self, session_id: str) -> CacheOperationResult:
        """Delete data by session ID."""
        ...

    def get_stats(self) -> CacheStats | None:
        """Get storage statistics."""
        ...

    def get_all_sessions_for_client(self, client_id: str) -> list[CacheMetadata]:
        """Get all sessions for a specific client."""
        ...

    def cleanup_old_entries(self, max_age_days: int = 30) -> int:
        """Clean up old entries.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of entries cleaned up
        """
        if not self.ensure_initialized():
            return 0

        try:
            with self._lock:
                if self._collection is None:
                    return 0
                # Calculate cutoff date
                from datetime import timedelta
                cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)

                # Get all entries with timestamps
                results = self._collection.get(include=["metadatas"])

                old_ids = []
                if results["metadatas"] is not None:
                    for i, metadata_dict in enumerate(results["metadatas"]):
                        last_updated_str = metadata_dict.get("last_updated")
                        if last_updated_str and isinstance(last_updated_str, str):
                            try:
                                last_updated = datetime.fromisoformat(last_updated_str)
                                if last_updated.tzinfo is None:
                                    last_updated = last_updated.replace(tzinfo=UTC)
                                
                                if last_updated < cutoff_date:
                                    old_ids.append(results["ids"][i])
                            except (ValueError, TypeError):
                                # Skip entries with invalid timestamps
                                continue

                # Delete old entries
                if old_ids:
                    self._collection.delete(ids=old_ids)

                return len(old_ids)

        except Exception as e:
            logger.warning(f"Failed to cleanup old entries: {e}")
            return 0

    def get_all_session_ids(self) -> list[str]:
        """Get all stored session IDs."""
        ...

    def get_distance_metric(self) -> str:
        """Get the distance metric used by the collection."""
        ...

    def update_embeddings(self, updates: list[dict[str, Any]]) -> int:
        """Update multiple embeddings in batch."""
        ...


class CacheStorageService(CacheStorageServiceProtocol):
    """Service for ChromaDB persistence operations."""

    def __init__(
        self,
        db_path: str,
        collection_name: str = "workflow_states",
        max_results: int = 50,
    ):
        """Initialize the cache storage service.

        Args:
            db_path: Path to ChromaDB database directory
            collection_name: Name of the ChromaDB collection
            max_results: Maximum results for queries
        """
        self.db_path = Path(db_path)
        self.collection_name = collection_name
        self.max_results = max_results

        # Thread safety
        self._lock = threading.Lock()

        # Lazy initialization for expensive operations
        self._client: chromadb.api.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None
        self._initialized = False

    def is_initialized(self) -> bool:
        """Check if storage service is initialized."""
        return self._initialized

    def ensure_initialized(self) -> bool:
        """Ensure storage service is initialized.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        with self._lock:
            if self._initialized:
                return True

            try:
                # Ensure database directory exists
                self.db_path.mkdir(parents=True, exist_ok=True)

                # Initialize ChromaDB client
                self._client = chromadb.PersistentClient(
                    path=str(self.db_path),
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )

                # Get or create collection with optimized distance metric for text embeddings
                try:
                    # Try to get existing collection first (preserves existing metric)
                    self._collection = self._client.get_collection(
                        name=self.collection_name
                    )
                except Exception:
                    # Create new collection with cosine distance (better for text embeddings)
                    try:
                        self._collection = self._client.create_collection(
                            name=self.collection_name,
                            metadata={
                                "hnsw:space": "cosine",  # Use cosine distance for semantic similarity
                                "description": "Workflow states with semantic embeddings",
                            },
                        )
                    except Exception as create_error:
                        # Fallback: create with default settings if cosine fails
                        logger.warning(
                            "Failed to create collection with cosine distance, falling back to default metric",
                            collection_name=self.collection_name,
                            error=str(create_error)
                        )
                        self._collection = self._client.create_collection(
                            name=self.collection_name,
                            metadata={
                                "description": "Workflow states with semantic embeddings"
                            },
                        )

                self._initialized = True
                return True

            except Exception as e:
                # Log error but don't raise to avoid breaking workflow execution
                logger.warning(
                    "Failed to initialize cache storage",
                    db_path=str(self.db_path),
                    collection_name=self.collection_name,
                    error=str(e)
                )
                return False

    def store_with_embedding(
        self, 
        session_id: str, 
        embedding: list[float], 
        document_text: str, 
        metadata: dict[str, Any]
    ) -> CacheOperationResult:
        """Store data with pre-computed embedding.
        
        Args:
            session_id: Unique session identifier
            embedding: Pre-computed embedding vector
            document_text: Text used for embedding generation
            metadata: Metadata to store
            
        Returns:
            CacheOperationResult indicating success/failure
        """
        if not self.ensure_initialized():
            return CacheOperationResult(
                success=False,
                error_message="Storage not initialized",
                operation_type="store",
            )

        try:
            with self._lock:
                # Serialize metadata for ChromaDB (convert datetime to string and serialize complex objects)
                serialized_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, datetime):
                        serialized_metadata[key] = value.isoformat()
                    elif isinstance(value, dict):
                        # Serialize complex dictionaries like node_outputs to JSON string
                        serialized_metadata[key] = json.dumps(value) if value else "{}"
                    else:
                        serialized_metadata[key] = value

                # Store in ChromaDB
                if self._collection is not None:
                    self._collection.upsert(  # type: ignore
                        ids=[session_id],
                        embeddings=[embedding],
                        documents=[document_text],
                        metadatas=[serialized_metadata],
                    )

                return CacheOperationResult(
                    success=True, session_id=session_id, operation_type="store"
                )

        except Exception as e:
            return CacheOperationResult(
                success=False, error_message=str(e), operation_type="store"
            )

    def retrieve_by_id(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve stored data by session ID.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Dictionary with metadata and document or None if not found
        """
        if not self.ensure_initialized():
            return None

        try:
            with self._lock:
                # Query ChromaDB for the specific session
                if self._collection is None:
                    return None
                results = self._collection.get(
                    ids=[session_id], include=["metadatas", "documents"]
                )

                if not results["ids"] or len(results["ids"]) == 0:
                    return None

                # Get metadata and deserialize datetime strings
                metadata_dict = dict(results["metadatas"][0])  # type: ignore

                # Convert ISO datetime strings back to datetime objects and deserialize JSON
                for key, value in metadata_dict.items():
                    if isinstance(value, str) and (
                        key.endswith("_at")
                        or key.endswith("_time")
                        or key.endswith("_updated")
                    ):
                        with contextlib.suppress(ValueError, TypeError):
                            dt = datetime.fromisoformat(value)
                            # Ensure timezone awareness - if naive, assume UTC
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=UTC)
                            metadata_dict[key] = dt
                    elif isinstance(value, str) and key == "node_outputs":
                        # Deserialize node_outputs JSON string back to dict
                        try:
                            metadata_dict[key] = json.loads(value) if value else {}
                        except (ValueError, TypeError, json.JSONDecodeError):
                            # If JSON parsing fails, use empty dict as fallback
                            metadata_dict[key] = {}

                return {
                    "metadata": metadata_dict,
                    "document": results["documents"][0] if results["documents"] else "",
                }

        except Exception as e:
            logger.warning(f"Failed to retrieve data for session {session_id}: {e}")
            return None

    def query_by_embedding(
        self,
        query_embedding: list[float],
        n_results: int = 50,
        where_filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Query storage using embedding vector.
        
        Args:
            query_embedding: Embedding vector for similarity search
            n_results: Maximum number of results
            where_filters: Optional metadata filters
            
        Returns:
            Dictionary with query results from ChromaDB
        """
        if not self.ensure_initialized():
            return {"ids": [], "metadatas": [], "documents": [], "distances": []}

        try:
            with self._lock:
                # Perform vector search
                if self._collection is None:
                    return {"ids": [], "metadatas": [], "documents": [], "distances": []}
                search_results = self._collection.query(  # type: ignore
                    query_embeddings=[query_embedding],
                    n_results=min(n_results, self.max_results),
                    where=where_filters if where_filters else None,
                    include=["metadatas", "documents", "distances"],
                )

                return dict(search_results)

        except Exception as e:
            logger.warning(f"Query by embedding failed: {e}")
            return {"ids": [], "metadatas": [], "documents": [], "distances": []}

    def delete_by_id(self, session_id: str) -> CacheOperationResult:
        """Delete data by session ID.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            CacheOperationResult indicating success/failure
        """
        if not self.ensure_initialized():
            return CacheOperationResult(
                success=False,
                error_message="Storage not initialized",
                operation_type="delete",
            )

        try:
            with self._lock:
                # Check if session exists
                if self._collection is None:
                    return CacheOperationResult(
                        success=False,
                        error_message="Storage not initialized",
                        operation_type="delete",
                    )
                existing = self._collection.get(ids=[session_id])
                if not existing["ids"]:
                    return CacheOperationResult(
                        success=False,
                        error_message=f"Session {session_id} not found",
                        operation_type="delete",
                    )

                # Delete from ChromaDB
                self._collection.delete(ids=[session_id])

                return CacheOperationResult(
                    success=True, session_id=session_id, operation_type="delete"
                )

        except Exception as e:
            return CacheOperationResult(
                success=False, error_message=str(e), operation_type="delete"
            )

    def get_stats(self) -> CacheStats | None:
        """Get storage statistics.
        
        Returns:
            CacheStats object or None if unavailable
        """
        if not self.ensure_initialized():
            return None

        try:
            with self._lock:
                if self._collection is None:
                    return None
                total_entries = self._collection.count()

                # Get a sample to check for presence of data
                sample = self._collection.get(limit=1, include=["metadatas"])
                has_data = len(sample["ids"]) > 0

                return CacheStats(
                    total_entries=total_entries,
                    active_sessions=0,  # Would need to query for active status
                    completed_sessions=0,  # Would need to query for completed status
                    cache_size_mb=0.0,  # Would need to calculate from data
                    collection_name=self.collection_name,
                )

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
        if not self.ensure_initialized():
            return []

        try:
            with self._lock:
                # Query for specific client
                if self._collection is None:
                    return []
                results = self._collection.get(
                    where={"client_id": client_id},
                    include=["metadatas"],
                )

                metadata_list = []
                if results["metadatas"] is not None:
                    for metadata_dict in results["metadatas"]:
                        # Convert to mutable dict and deserialize datetime strings
                        metadata_dict = dict(metadata_dict)
                        for key, value in metadata_dict.items():
                            if isinstance(value, str) and key.endswith("_at"):
                                with contextlib.suppress(ValueError, TypeError):
                                    dt = datetime.fromisoformat(value)
                                    if dt.tzinfo is None:
                                        dt = dt.replace(tzinfo=UTC)
                                    metadata_dict[key] = dt
                            elif isinstance(value, str) and key == "node_outputs":
                                try:
                                    metadata_dict[key] = json.loads(value) if value else {}
                                except (ValueError, TypeError, json.JSONDecodeError):
                                    metadata_dict[key] = {}

                        metadata_list.append(CacheMetadata(**metadata_dict))  # type: ignore

                return metadata_list

        except Exception as e:
            logger.warning(f"Failed to get sessions for client {client_id}: {e}")
            return []

    def get_all_session_ids(self) -> list[str]:
        """Get all stored session IDs.
        
        Returns:
            List of session IDs
        """
        if not self.ensure_initialized():
            return []

        try:
            with self._lock:
                if self._collection is None:
                    return []
                results = self._collection.get(include=[])
                return list(results["ids"])

        except Exception as e:
            logger.warning(f"Failed to get session IDs: {e}")
            return []

    def get_distance_metric(self) -> str:
        """Get the distance metric used by the collection.

        Returns:
            str: Distance metric ('l2', 'cosine', 'ip') or 'l2' as default
        """
        if not self.ensure_initialized():
            return "l2"

        try:
            # Get collection metadata to check distance metric
            if self._collection is None:
                return "l2"
            collection_metadata = self._collection.metadata
            if collection_metadata and "hnsw:space" in collection_metadata:
                return str(collection_metadata["hnsw:space"])
            # Default to L2 if not specified (ChromaDB default)
            return "l2"
        except Exception:
            # Fallback to L2 if we can't determine the metric
            return "l2"

    def update_embeddings(self, updates: list[dict[str, Any]]) -> int:
        """Update multiple embeddings in batch.
        
        Args:
            updates: List of update dictionaries with 'id', 'embedding', 'document', 'metadata'
            
        Returns:
            Number of successful updates
        """
        if not self.ensure_initialized():
            return 0

        try:
            with self._lock:
                if self._collection is None:
                    return 0
                successful_updates = 0

                for update in updates:
                    try:
                        session_id = update["id"]
                        embedding = update["embedding"]
                        document = update["document"]
                        metadata = update["metadata"]

                        # Serialize metadata
                        serialized_metadata = {}
                        for key, value in metadata.items():
                            if isinstance(value, datetime):
                                serialized_metadata[key] = value.isoformat()
                            elif isinstance(value, dict):
                                serialized_metadata[key] = json.dumps(value) if value else "{}"
                            else:
                                serialized_metadata[key] = value

                        # Update in ChromaDB
                        self._collection.upsert(
                            ids=[session_id],
                            embeddings=[embedding],
                            documents=[document],
                            metadatas=[serialized_metadata],
                        )

                        successful_updates += 1

                    except Exception as e:
                        logger.warning(f"Failed to update embedding for {update.get('id', 'unknown')}: {e}")
                        continue

                return successful_updates

        except Exception as e:
            logger.warning(f"Batch embedding update failed: {e}")
            return 0 