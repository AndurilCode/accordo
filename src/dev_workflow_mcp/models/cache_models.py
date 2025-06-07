"""Cache-specific models for ChromaDB integration."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class CacheMetadata(BaseModel):
    """Metadata for cached workflow states."""

    session_id: str = Field(description="Unique session identifier")
    client_id: str = Field(description="Client session identifier")
    workflow_name: str = Field(description="Name of the workflow")
    workflow_file: str | None = Field(
        default=None, description="Path to workflow YAML file"
    )
    current_node: str = Field(description="Current node in the workflow")
    current_item: str | None = Field(
        default=None, description="Current task or item description"
    )
    status: str = Field(description="Current workflow status")
    node_outputs: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Outputs from completed nodes including acceptance criteria evidence",
    )
    created_at: datetime = Field(description="Session creation time")
    last_updated: datetime = Field(description="Last update time")
    cache_created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this cache entry was created",
    )
    cache_version: str = Field(default="1.0", description="Cache schema version")


class CachedWorkflowState(BaseModel):
    """Complete cached workflow state with metadata."""

    metadata: CacheMetadata = Field(description="Cache metadata")
    state_data: dict[str, Any] = Field(description="Serialized workflow state data")
    embedding_text: str = Field(
        description="Text used for semantic embedding generation"
    )


class SemanticSearchResult(BaseModel):
    """Result from semantic search of cached workflow states."""

    session_id: str = Field(description="Session ID of the matching state")
    similarity_score: float = Field(
        description="Similarity score (0-1, higher is more similar)"
    )
    metadata: CacheMetadata = Field(description="Metadata of the matching state")
    matching_text: str = Field(description="Text that was matched in the search")


class CacheSearchQuery(BaseModel):
    """Query parameters for cache search operations."""

    search_text: str = Field(description="Text to search for semantically")
    client_id: str | None = Field(default=None, description="Filter by client ID")
    workflow_name: str | None = Field(
        default=None, description="Filter by workflow name"
    )
    status_filter: list[str] | None = Field(
        default=None, description="Filter by status values"
    )
    min_similarity: float = Field(default=0.1, description="Minimum similarity score")
    max_results: int = Field(default=50, description="Maximum number of results")
    include_inactive: bool = Field(
        default=True, description="Include inactive/completed sessions"
    )


class CacheOperationResult(BaseModel):
    """Result of cache operations."""

    success: bool = Field(description="Whether the operation succeeded")
    session_id: str | None = Field(default=None, description="Session ID if applicable")
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )
    operation_type: str = Field(description="Type of operation performed")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the operation was performed",
    )


class CacheStats(BaseModel):
    """Statistics about the cache state."""

    total_entries: int = Field(description="Total number of cached entries")
    active_sessions: int = Field(description="Number of active sessions in cache")
    completed_sessions: int = Field(description="Number of completed sessions in cache")
    oldest_entry: datetime | None = Field(
        default=None, description="Timestamp of oldest entry"
    )
    newest_entry: datetime | None = Field(
        default=None, description="Timestamp of newest entry"
    )
    cache_size_mb: float = Field(description="Approximate cache size in MB")
    collection_name: str = Field(description="ChromaDB collection name")
