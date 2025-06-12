"""Response models for workflow operations."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class BaseResponse(BaseModel):
    """Base response model with standardized fields."""
    
    success: bool = Field(..., description="Indicates if the operation was successful")
    message: str = Field(..., description="Human-readable message about the operation")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    correlation_id: str | None = Field(None, description="Request correlation ID for tracing")
    context: dict[str, Any] | None = Field(default_factory=dict, description="Additional context information")


class ErrorResponse(BaseResponse):
    """Standardized error response model."""
    
    success: Literal[False] = Field(False, description="Always False for error responses")
    error: dict[str, Any] = Field(..., description="Detailed error information")
    http_status: int = Field(500, description="HTTP status code")
    
    @field_validator('error')
    @classmethod
    def validate_error_structure(cls, v):
        """Validate error field has required structure."""
        required_fields = ['type', 'message', 'code']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Error field missing required key: {field}")
        return v


class SuccessResponse(BaseResponse):
    """Standardized success response model."""
    
    success: Literal[True] = Field(True, description="Always True for success responses")
    data: Any | None = Field(None, description="Response data payload")


class WorkflowResponse(BaseResponse):
    """Response model for workflow operations."""

    next_prompt: str | None = Field(None, description="Next prompt for workflow continuation")
    next_params: dict[str, Any] | None = Field(None, description="Parameters for next workflow step")
    session_id: str | None = Field(None, description="Workflow session identifier")
    current_node: str | None = Field(None, description="Current workflow node")
    phase: str | None = Field(None, description="Current workflow phase")


class StateUpdateResponse(BaseResponse):
    """Response for state update operations."""

    current_phase: str = Field(..., description="Current workflow phase")
    current_status: str = Field(..., description="Current workflow status")
    session_id: str | None = Field(None, description="Session identifier")
    updated_fields: list[str] | None = Field(None, description="List of fields that were updated")


class ValidationErrorResponse(ErrorResponse):
    """Response for validation errors with detailed field errors."""
    
    validation_errors: list[str] = Field(..., description="List of validation error messages")
    
    @field_validator('error', mode='before')
    @classmethod
    def set_error_from_validation(cls, v, info):
        """Automatically populate error field from validation errors."""
        if hasattr(info, 'data') and 'validation_errors' in info.data:
            return {
                'type': 'ValidationError',
                'message': 'Input validation failed',
                'code': 'VALIDATION_ERROR',
                'details': {
                    'validation_errors': info.data['validation_errors']
                }
            }
        return v


class ServiceUnavailableResponse(ErrorResponse):
    """Response for service unavailable errors."""
    
    service_name: str = Field(..., description="Name of the unavailable service")
    retry_after: int | None = Field(None, description="Suggested retry time in seconds")
    
    @field_validator('error', mode='before')
    @classmethod
    def set_error_from_service(cls, v, info):
        """Automatically populate error field from service info."""
        if hasattr(info, 'data') and 'service_name' in info.data:
            return {
                'type': 'ServiceError',
                'message': f"Service unavailable: {info.data['service_name']}",
                'code': 'SERVICE_UNAVAILABLE',
                'details': {
                    'service_name': info.data['service_name'],
                    'availability': False
                }
            }
        return v


class NotFoundResponse(ErrorResponse):
    """Response for resource not found errors."""
    
    resource_type: str = Field(..., description="Type of resource that was not found")
    resource_id: str = Field(..., description="Identifier of resource that was not found")
    
    @field_validator('error', mode='before')
    @classmethod
    def set_error_from_resource(cls, v, info):
        """Automatically populate error field from resource info."""
        if hasattr(info, 'data') and 'resource_type' in info.data and 'resource_id' in info.data:
            return {
                'type': 'SessionNotFoundError',
                'message': f"{info.data['resource_type']} not found: {info.data['resource_id']}",
                'code': 'RESOURCE_NOT_FOUND',
                'details': {
                    'resource_type': info.data['resource_type'],
                    'resource_id': info.data['resource_id']
                }
            }
        return v
