"""Response models for workflow operations."""

from pydantic import BaseModel


class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""

    success: bool
    message: str
    next_prompt: str | None = None
    next_params: dict | None = None


class StateUpdateResponse(BaseModel):
    """Response for state update operations."""

    success: bool
    message: str
    current_phase: str
    current_status: str
