"""Configuration models for workflow MCP server."""

import os
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class S3Config(BaseModel):
    """S3 configuration for workflow state synchronization."""

    enabled: bool = Field(
        default_factory=lambda: bool(os.getenv("S3_BUCKET_NAME")),
        description="Enable S3 synchronization (auto-enabled if S3_BUCKET_NAME is set)",
    )
    bucket_name: str | None = Field(
        default_factory=lambda: os.getenv("S3_BUCKET_NAME"),
        description="S3 bucket name (from S3_BUCKET_NAME env var)",
    )
    prefix: str = Field(
        default_factory=lambda: os.getenv("S3_PREFIX", "workflow-states/"),
        description="S3 key prefix for workflow states (from S3_PREFIX env var)",
    )
    region: str = Field(
        default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"),
        description="AWS region (from AWS_REGION env var)",
    )
    sync_on_finalize: bool = Field(
        default_factory=lambda: os.getenv("S3_SYNC_ON_FINALIZE", "true").lower()
        == "true",
        description="Sync state when workflow is finalized (from S3_SYNC_ON_FINALIZE env var)",
    )
    archive_completed: bool = Field(
        default_factory=lambda: os.getenv("S3_ARCHIVE_COMPLETED", "true").lower()
        == "true",
        description="Archive completed workflows with timestamp (from S3_ARCHIVE_COMPLETED env var)",
    )

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        """Ensure prefix ends with slash."""
        if v and not v.endswith("/"):
            return v + "/"
        return v

    @model_validator(mode="after")
    def validate_s3_config(self) -> Self:
        """Validate S3 configuration consistency."""
        if self.enabled and not self.bucket_name:
            raise ValueError(
                "S3 sync is enabled but bucket_name is not set. Set S3_BUCKET_NAME environment variable."
            )

        # Auto-disable if bucket name is missing
        if not self.bucket_name:
            object.__setattr__(self, "enabled", False)

        return self


class WorkflowConfig(BaseModel):
    """Workflow behavior configuration.

    This configuration controls core workflow behavior including:
    - Local state file enforcement for dual storage mode
    - Local state file format selection (MD or JSON)

    Configuration is now CLI-driven rather than environment variable based.
    """

    local_state_file: bool = Field(
        default=False,
        description="Enforce local storage of workflow state files through automatic synchronization. When enabled, maintains both MCP server memory state AND local file state in .accordo/sessions/ directory.",
    )
    local_state_file_format: str = Field(
        default="MD",
        description="Format for local state file when local_state_file is enabled. Supports 'MD' for markdown or 'JSON' for structured JSON format.",
    )

    @classmethod
    def from_server_config(cls, server_config) -> "WorkflowConfig":
        """Create WorkflowConfig from ServerConfig instance.

        Args:
            server_config: ServerConfig instance with CLI-provided values

        Returns:
            WorkflowConfig instance
        """
        return cls(
            local_state_file=server_config.enable_local_state_file,
            local_state_file_format=server_config.local_state_file_format,
        )

    @field_validator("local_state_file_format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate format is MD or JSON."""
        v_upper = v.upper()
        if v_upper not in ("MD", "JSON"):
            raise ValueError(
                f"local_state_file_format must be 'MD' or 'JSON', got '{v}'"
            )
        return v_upper
