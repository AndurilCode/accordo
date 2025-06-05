"""Workflow cache manager using ChromaDB for persistent storage and semantic search."""

import contextlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from ..models.cache_models import (
    CacheMetadata,
    CacheOperationResult,
    CacheSearchQuery,
    CacheStats,
    SemanticSearchResult,
)
from ..models.workflow_state import DynamicWorkflowState


class WorkflowCacheManager:
    """Manages workflow state caching using ChromaDB with semantic search capabilities."""

    def __init__(
        self,
        db_path: str,
        collection_name: str = "workflow_states",
        embedding_model: str = "all-mpnet-base-v2",
        max_results: int = 50,
    ):
        """Initialize the cache manager.

        Args:
            db_path: Path to ChromaDB database directory
            collection_name: Name of the ChromaDB collection
            embedding_model: Sentence transformer model for embeddings
            max_results: Maximum results for search queries
        """
        self.db_path = Path(db_path)
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.max_results = max_results
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Lazy initialization for expensive operations
        self._client: chromadb.Client | None = None
        self._collection: chromadb.Collection | None = None
        self._embedding_model: SentenceTransformer | None = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Ensure the cache manager is initialized.
        
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
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                
                # Get or create collection
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "Workflow states with semantic embeddings"}
                )
                
                # Initialize embedding model (lazy loading for performance)
                # Model will be loaded on first use
                
                self._initialized = True
                return True
                
            except Exception as e:
                # Log error but don't raise to avoid breaking workflow execution
                print(f"Warning: Failed to initialize cache manager: {e}")
                return False

    def _get_embedding_model(self) -> SentenceTransformer | None:
        """Get the embedding model, loading it if necessary.
        
        Returns:
            SentenceTransformer model or None if loading fails
        """
        if self._embedding_model is not None:
            return self._embedding_model
            
        try:
            self._embedding_model = SentenceTransformer(self.embedding_model_name)
            return self._embedding_model
        except Exception as e:
            print(f"Warning: Failed to load embedding model {self.embedding_model_name}: {e}")
            return None

    def _generate_embedding_text(self, state: DynamicWorkflowState) -> str:
        """Generate text for embedding from workflow state.
        
        Args:
            state: Workflow state to generate text from
            
        Returns:
            str: Text suitable for embedding generation
        """
        # Combine key state information for semantic search
        text_parts = [
            f"Workflow: {state.workflow_name}",
            f"Current node: {state.current_node}",
            f"Status: {state.status}",
        ]
        
        # Add current item if available
        if state.current_item:
            text_parts.append(f"Current task: {state.current_item}")
            
        # Add recent log entries (last 3)
        if state.log:
            recent_logs = state.log[-3:]
            text_parts.append(f"Recent activity: {' '.join(recent_logs)}")
            
        # Add execution context if available
        if state.execution_context:
            context_summary = ', '.join(f"{k}: {v}" for k, v in state.execution_context.items())
            text_parts.append(f"Context: {context_summary}")
            
        return " | ".join(text_parts)

    def store_workflow_state(self, state: DynamicWorkflowState) -> CacheOperationResult:
        """Store a workflow state in the cache.
        
        Args:
            state: Workflow state to store
            
        Returns:
            CacheOperationResult: Result of the store operation
        """
        if not self._ensure_initialized():
            return CacheOperationResult(
                success=False,
                error_message="Cache manager not initialized",
                operation_type="store"
            )
            
        try:
            with self._lock:
                # Generate embedding text
                embedding_text = self._generate_embedding_text(state)
                
                # Create metadata
                metadata = CacheMetadata(
                    session_id=state.session_id,
                    client_id=state.client_id,
                    workflow_name=state.workflow_name,
                    workflow_file=state.workflow_file,
                    current_node=state.current_node,
                    status=state.status,
                    created_at=state.created_at,
                    last_updated=state.last_updated,
                )
                
                # Create cached state (metadata for storage)
                
                # Generate embedding
                model = self._get_embedding_model()
                if model is None:
                    return CacheOperationResult(
                        success=False,
                        error_message="Embedding model not available",
                        operation_type="store"
                    )
                    
                embedding = model.encode([embedding_text])[0].tolist()
                
                # Serialize metadata for ChromaDB (convert datetime to string)
                metadata_dict = metadata.model_dump()
                for key, value in metadata_dict.items():
                    if isinstance(value, datetime):
                        metadata_dict[key] = value.isoformat()
                
                # Store in ChromaDB
                self._collection.upsert(
                    ids=[state.session_id],
                    embeddings=[embedding],
                    documents=[embedding_text],
                    metadatas=[metadata_dict]
                )
                
                return CacheOperationResult(
                    success=True,
                    session_id=state.session_id,
                    operation_type="store"
                )
                
        except Exception as e:
            return CacheOperationResult(
                success=False,
                error_message=str(e),
                operation_type="store"
            )

    def retrieve_workflow_state(self, session_id: str) -> DynamicWorkflowState | None:
        """Retrieve a workflow state from the cache.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            DynamicWorkflowState or None if not found
        """
        if not self._ensure_initialized():
            return None
            
        try:
            with self._lock:
                # Query ChromaDB for the specific session
                results = self._collection.get(
                    ids=[session_id],
                    include=["metadatas", "documents"]
                )
                
                if not results["ids"] or len(results["ids"]) == 0:
                    return None
                    
                # Get metadata and deserialize datetime strings
                metadata_dict = results["metadatas"][0]
                
                # Convert ISO datetime strings back to datetime objects
                for key, value in metadata_dict.items():
                    if isinstance(value, str) and (key.endswith('_at') or key.endswith('_time')):
                        with contextlib.suppress(ValueError, TypeError):
                            metadata_dict[key] = datetime.fromisoformat(value)
                
                metadata = CacheMetadata(**metadata_dict)
                
                # Note: We don't store the full state data in ChromaDB for this initial version
                # Instead, we create a minimal state from metadata for persistence restoration
                # Full state reconstruction would require storing state_data in ChromaDB
                
                # Create a minimal workflow state from metadata
                state = DynamicWorkflowState(
                    session_id=metadata.session_id,
                    client_id=metadata.client_id,
                    workflow_name=metadata.workflow_name,
                    workflow_file=metadata.workflow_file,
                    current_node=metadata.current_node,
                    current_item=metadata.current_item,
                    status=metadata.status,
                    created_at=metadata.created_at,
                    last_updated=metadata.last_updated,
                )
                
                return state
                
        except Exception as e:
            print(f"Warning: Failed to retrieve workflow state {session_id}: {e}")
            return None

    def delete_workflow_state(self, session_id: str) -> CacheOperationResult:
        """Delete a workflow state from the cache.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            CacheOperationResult: Result of the delete operation
        """
        if not self._ensure_initialized():
            return CacheOperationResult(
                success=False,
                error_message="Cache manager not initialized",
                operation_type="delete"
            )
            
        try:
            with self._lock:
                self._collection.delete(ids=[session_id])
                
                return CacheOperationResult(
                    success=True,
                    session_id=session_id,
                    operation_type="delete"
                )
                
        except Exception as e:
            return CacheOperationResult(
                success=False,
                error_message=str(e),
                operation_type="delete"
            )

    def get_cache_stats(self) -> CacheStats | None:
        """Get statistics about the cache.
        
        Returns:
            CacheStats or None if unavailable
        """
        if not self._ensure_initialized():
            return None
            
        try:
            with self._lock:
                # Get all entries
                results = self._collection.get(include=["metadatas"])
                
                if not results["metadatas"]:
                    return CacheStats(
                        total_entries=0,
                        active_sessions=0,
                        completed_sessions=0,
                        cache_size_mb=0.0,
                        collection_name=self.collection_name
                    )
                
                # Convert ISO datetime strings back to datetime objects for each metadata
                metadatas = []
                for m in results["metadatas"]:
                    metadata_dict = dict(m)
                    for key, value in metadata_dict.items():
                        if isinstance(value, str) and (key.endswith('_at') or key.endswith('_time')):
                            with contextlib.suppress(ValueError, TypeError):
                                metadata_dict[key] = datetime.fromisoformat(value)
                    metadatas.append(CacheMetadata(**metadata_dict))
                
                # Calculate statistics
                total_entries = len(metadatas)
                active_sessions = sum(1 for m in metadatas if m.status not in ["COMPLETED", "ERROR", "FINISHED"])
                completed_sessions = total_entries - active_sessions
                
                # Calculate timestamps
                timestamps = [m.cache_created_at for m in metadatas]
                oldest_entry = min(timestamps) if timestamps else None
                newest_entry = max(timestamps) if timestamps else None
                
                # Estimate cache size (rough approximation)
                cache_size_mb = len(json.dumps(results["metadatas"])) / (1024 * 1024)
                
                return CacheStats(
                    total_entries=total_entries,
                    active_sessions=active_sessions,
                    completed_sessions=completed_sessions,
                    oldest_entry=oldest_entry,
                    newest_entry=newest_entry,
                    cache_size_mb=round(cache_size_mb, 2),
                    collection_name=self.collection_name
                )
                
        except Exception as e:
            print(f"Warning: Failed to get cache stats: {e}")
            return None

    def is_available(self) -> bool:
        """Check if the cache is available for use.
        
        Returns:
            bool: True if cache is available
        """
        return self._ensure_initialized()

    def semantic_search(
        self, 
        search_text: str = None,
        query: CacheSearchQuery = None,
        client_id: str = None,
        workflow_name: str = None,
        status_filter: list[str] = None,
        min_similarity: float = 0.1,
        max_results: int = 50,
        include_inactive: bool = True
    ) -> list[SemanticSearchResult]:
        """Perform semantic search on cached workflow states.
        
        Args:
            search_text: Text to search for (alternative to query object)
            query: Search query object (alternative to individual parameters)
            client_id: Filter by client ID
            workflow_name: Filter by workflow name
            status_filter: Filter by status values
            min_similarity: Minimum similarity score
            max_results: Maximum number of results
            include_inactive: Include inactive/completed sessions
            
        Returns:
            List of semantic search results ordered by similarity
        """
        if not self._ensure_initialized():
            return []
        
        # Handle both calling styles
        if query is not None:
            # Use query object
            search_text = query.search_text
            client_id = query.client_id
            workflow_name = query.workflow_name
            status_filter = query.status_filter
            min_similarity = query.min_similarity
            max_results = query.max_results
            # include_inactive = query.include_inactive  # Future use
        elif search_text is None:
            # No search text provided
            return []
            
        try:
            with self._lock:
                # Generate embedding for search query
                model = self._get_embedding_model()
                if model is None:
                    return []
                    
                query_embedding = model.encode([search_text])[0].tolist()
                
                # Prepare metadata filters
                where_filters = {}
                if client_id:
                    where_filters["client_id"] = client_id
                if workflow_name:
                    where_filters["workflow_name"] = workflow_name
                if status_filter:
                    where_filters["status"] = {"$in": status_filter}
                
                # Perform vector search
                search_results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(max_results, self.max_results),
                    where=where_filters if where_filters else None,
                    include=["metadatas", "documents", "distances"]
                )
                
                # Convert results to SemanticSearchResult objects
                results = []
                if search_results["ids"] and len(search_results["ids"]) > 0:
                    for i, session_id in enumerate(search_results["ids"][0]):
                        # Calculate similarity score (ChromaDB returns distances)
                        distance = search_results["distances"][0][i]
                        similarity_score = max(0.0, 1.0 - distance)  # Convert distance to similarity
                        
                        # Skip results below minimum similarity
                        if similarity_score < min_similarity:
                            continue
                            
                        # Create metadata object (deserialize datetime strings)
                        metadata_dict = dict(search_results["metadatas"][0][i])
                        for key, value in metadata_dict.items():
                            if isinstance(value, str) and (key.endswith('_at') or key.endswith('_time')):
                                with contextlib.suppress(ValueError, TypeError):
                                    metadata_dict[key] = datetime.fromisoformat(value)
                        metadata = CacheMetadata(**metadata_dict)
                        
                        # Get matching text
                        matching_text = search_results["documents"][0][i]
                        
                        result = SemanticSearchResult(
                            session_id=session_id,
                            similarity_score=round(similarity_score, 4),
                            metadata=metadata,
                            matching_text=matching_text
                        )
                        results.append(result)
                
                # Sort by similarity score (highest first)
                results.sort(key=lambda x: x.similarity_score, reverse=True)
                return results
                
        except Exception as e:
            print(f"Warning: Semantic search failed: {e}")
            return []

    def find_similar_workflows(
        self, 
        workflow_state: DynamicWorkflowState, 
        max_results: int = 10,
        min_similarity: float = 0.3
    ) -> list[SemanticSearchResult]:
        """Find workflows similar to the given workflow state.
        
        Args:
            workflow_state: Workflow state to find similar ones for
            max_results: Maximum number of results to return
            min_similarity: Minimum similarity score
            
        Returns:
            List of similar workflow states
        """
        # Generate search text from the workflow state
        search_text = self._generate_embedding_text(workflow_state)
        
        # Perform search using direct parameters instead of query object
        results = self.semantic_search(
            search_text=search_text,
            client_id=workflow_state.client_id,  # Find similar workflows for same client
            max_results=max_results,
            min_similarity=min_similarity,
            include_inactive=True
        )
        
        # Filter out the current session
        return [r for r in results if r.session_id != workflow_state.session_id]

    def get_all_sessions_for_client(self, client_id: str) -> list[CacheMetadata]:
        """Get all cached sessions for a specific client.
        
        Args:
            client_id: Client ID to search for
            
        Returns:
            List of cache metadata for the client's sessions
        """
        if not self._ensure_initialized():
            return []
            
        try:
            with self._lock:
                # Query for all sessions of this client
                results = self._collection.get(
                    where={"client_id": client_id},
                    include=["metadatas"]
                )
                
                if not results["metadatas"]:
                    return []
                    
                # Convert to metadata objects (deserialize datetime strings) and sort by last_updated
                metadatas = []
                for m in results["metadatas"]:
                    metadata_dict = dict(m)
                    for key, value in metadata_dict.items():
                        if isinstance(value, str) and (key.endswith('_at') or key.endswith('_time')):
                            with contextlib.suppress(ValueError, TypeError):
                                metadata_dict[key] = datetime.fromisoformat(value)
                    metadatas.append(CacheMetadata(**metadata_dict))
                
                metadatas.sort(key=lambda x: x.last_updated, reverse=True)
                
                return metadatas
                
        except Exception as e:
            print(f"Warning: Failed to get sessions for client {client_id}: {e}")
            return []

    def cleanup_old_entries(self, max_age_days: int = 30) -> int:
        """Remove cached entries older than specified days.
        
        Args:
            max_age_days: Maximum age in days for cached entries
            
        Returns:
            Number of entries removed
        """
        if not self._ensure_initialized():
            return 0
            
        try:
            with self._lock:
                # Calculate cutoff date
                from datetime import timedelta
                cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
                
                # Get all entries with timestamps
                results = self._collection.get(include=["metadatas"])
                
                if not results["metadatas"]:
                    return 0
                    
                # Find entries to delete
                ids_to_delete = []
                for i, metadata_dict in enumerate(results["metadatas"]):
                    metadata = CacheMetadata(**metadata_dict)
                    if metadata.cache_created_at < cutoff_date:
                        ids_to_delete.append(results["ids"][i])
                
                # Delete old entries
                if ids_to_delete:
                    self._collection.delete(ids=ids_to_delete)
                    
                return len(ids_to_delete)
                
        except Exception as e:
            print(f"Warning: Failed to cleanup old entries: {e}")
            return 0

    def cleanup(self) -> None:
        """Cleanup cache resources."""
        with self._lock:
            if self._client:
                # ChromaDB client doesn't need explicit cleanup
                pass
            self._initialized = False
            self._client = None
            self._collection = None
            # Keep embedding model loaded for reuse 