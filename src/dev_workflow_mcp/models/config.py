"""Configuration models for workflow MCP server."""

import os
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class S3Config(BaseModel):
    """S3 configuration for workflow state synchronization."""

    enabled: bool = Field(
        default_factory=lambda: bool(os.getenv("S3_BUCKET_NAME")),
        description="Enable S3 synchronization (auto-enabled if S3_BUCKET_NAME is set)"
    )
    bucket_name: str | None = Field(
        default_factory=lambda: os.getenv("S3_BUCKET_NAME"),
        description="S3 bucket name (from S3_BUCKET_NAME env var)"
    )
    prefix: str = Field(
        default_factory=lambda: os.getenv("S3_PREFIX", "workflow-states/"),
        description="S3 key prefix for workflow states (from S3_PREFIX env var)"
    )
    region: str = Field(
        default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"),
        description="AWS region (from AWS_REGION env var)"
    )
    sync_on_finalize: bool = Field(
        default_factory=lambda: os.getenv("S3_SYNC_ON_FINALIZE", "true").lower() == "true",
        description="Sync state when workflow is finalized (from S3_SYNC_ON_FINALIZE env var)"
    )
    archive_completed: bool = Field(
        default_factory=lambda: os.getenv("S3_ARCHIVE_COMPLETED", "true").lower() == "true",
        description="Archive completed workflows with timestamp (from S3_ARCHIVE_COMPLETED env var)"
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
            raise ValueError("S3 sync is enabled but bucket_name is not set. Set S3_BUCKET_NAME environment variable.")
        
        # Auto-disable if bucket name is missing
        if not self.bucket_name:
            object.__setattr__(self, 'enabled', False)
        
        return self


class WorkflowConfig(BaseModel):
    """Workflow behavior configuration.
    
    This configuration controls core workflow behavior including:
    - Automatic plan approval to bypass user confirmation
    - Local state file enforcement for dual storage mode
    """

    auto_approve_plans: bool = Field(
        default_factory=lambda: os.getenv("WORKFLOW_AUTO_APPROVE_PLANS", "false").lower() == "true",
        description="Automatically approve blueprint plans without user interaction (from WORKFLOW_AUTO_APPROVE_PLANS env var)"
    )
    local_state_file: bool = Field(
        default_factory=lambda: os.getenv("WORKFLOW_LOCAL_STATE_FILE", "false").lower() == "true",
        description="Enforce local storage of workflow_state.md file through mandatory agent prompts. When enabled, maintains both MCP server memory state AND local file state for dual storage mode. (from WORKFLOW_LOCAL_STATE_FILE env var)"
    )