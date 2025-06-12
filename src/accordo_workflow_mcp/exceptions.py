"""Standardized exception hierarchy for Accordo Workflow MCP.

This module provides a unified exception system with structured error information,
error codes, and consistent handling patterns across the entire codebase.
"""

import json
import uuid
from datetime import datetime
from typing import Any


class AccordoError(Exception):
    """Base exception class for all Accordo-specific errors.
    
    Provides structured error information including error codes, context data,
    correlation IDs, and serialization capabilities for consistent error handling.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        source_module: str | None = None,
        cause: Exception | None = None
    ):
        """Initialize AccordoError.
        
        Args:
            message: Human-readable error message
            error_code: Unique error code for programmatic handling
            details: Additional structured context information
            correlation_id: Optional correlation ID for request tracing
            source_module: Module where the error originated
            cause: Optional underlying exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._generate_default_error_code()
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.source_module = source_module
        self.cause = cause
        self.timestamp = datetime.utcnow().isoformat()
        
    def _generate_default_error_code(self) -> str:
        """Generate a default error code based on the exception class name."""
        class_name = self.__class__.__name__
        # Convert CamelCase to UPPER_SNAKE_CASE
        import re
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', class_name).upper()
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for JSON responses.
        
        Returns:
            Dictionary containing all error information
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "correlation_id": self.correlation_id,
            "source_module": self.source_module,
            "timestamp": self.timestamp,
            "cause": str(self.cause) if self.cause else None
        }
    
    def to_json(self) -> str:
        """Serialize error to JSON string.
        
        Returns:
            JSON representation of the error
        """
        return json.dumps(self.to_dict(), indent=2)
    
    def with_details(self, **kwargs) -> "AccordoError":
        """Add additional details to the error.
        
        Args:
            **kwargs: Additional details to add
            
        Returns:
            Self for method chaining
        """
        self.details.update(kwargs)
        return self
    
    def with_correlation_id(self, correlation_id: str) -> "AccordoError":
        """Set correlation ID for request tracing.
        
        Args:
            correlation_id: Correlation ID to set
            
        Returns:
            Self for method chaining
        """
        self.correlation_id = correlation_id
        return self
    
    def with_source_module(self, module_name: str) -> "AccordoError":
        """Set the source module where error originated.
        
        Args:
            module_name: Name of the source module
            
        Returns:
            Self for method chaining
        """
        self.source_module = module_name
        return self


# Workflow-related exceptions
class WorkflowError(AccordoError):
    """Exception raised for workflow-related errors."""
    pass


class WorkflowLoadError(WorkflowError):
    """Exception raised when workflow loading fails."""
    
    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if file_path:
            self.with_details(file_path=file_path)


class WorkflowEngineError(WorkflowError):
    """Exception raised when workflow engine encounters an error."""
    pass


class WorkflowValidationError(WorkflowError):
    """Exception raised when workflow validation fails."""
    pass


class WorkflowNodeError(WorkflowError):
    """Exception raised for workflow node-related errors."""
    
    def __init__(
        self,
        message: str,
        node_name: str | None = None,
        workflow_name: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if node_name:
            self.with_details(node_name=node_name)
        if workflow_name:
            self.with_details(workflow_name=workflow_name)


class WorkflowTransitionError(WorkflowError):
    """Exception raised for invalid workflow transitions."""
    
    def __init__(
        self,
        message: str,
        current_node: str | None = None,
        target_node: str | None = None,
        allowed_nodes: list | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        details = {}
        if current_node:
            details["current_node"] = current_node
        if target_node:
            details["target_node"] = target_node
        if allowed_nodes:
            details["allowed_nodes"] = allowed_nodes
        if details:
            self.with_details(**details)


# Session-related exceptions
class SessionError(AccordoError):
    """Exception raised for session-related errors."""
    
    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if session_id:
            self.with_details(session_id=session_id)


class SessionNotFoundError(SessionError):
    """Exception raised when a session is not found."""
    pass


class SessionInitializationError(SessionError):
    """Exception raised when session initialization fails."""
    pass


class SessionSyncError(SessionError):
    """Exception raised when session synchronization fails."""
    pass


class SessionLifecycleError(SessionError):
    """Exception raised for session lifecycle management errors."""
    pass


# Cache-related exceptions
class CacheError(AccordoError):
    """Exception raised for cache-related errors."""
    pass


class CacheInitializationError(CacheError):
    """Exception raised when cache initialization fails."""
    pass


class CacheOperationError(CacheError):
    """Exception raised when cache operations fail."""
    
    def __init__(
        self,
        message: str,
        operation: str | None = None,
        cache_key: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        details = {}
        if operation:
            details["operation"] = operation
        if cache_key:
            details["cache_key"] = cache_key
        if details:
            self.with_details(**details)


class EmbeddingError(CacheError):
    """Exception raised for embedding-related errors."""
    pass


# Configuration-related exceptions
class ConfigurationError(AccordoError):
    """Exception raised for configuration-related errors."""
    pass


class ConfigurationValidationError(ConfigurationError):
    """Exception raised when configuration validation fails."""
    pass


class ConfigurationLoadError(ConfigurationError):
    """Exception raised when configuration loading fails."""
    
    def __init__(
        self,
        message: str,
        config_path: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if config_path:
            self.with_details(config_path=config_path)


# Service and dependency injection exceptions
class ServiceError(AccordoError):
    """Exception raised for service-related errors."""
    pass


class DependencyInjectionError(ServiceError):
    """Exception raised when dependency injection fails."""
    
    def __init__(
        self,
        message: str,
        service_type: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if service_type:
            self.with_details(service_type=service_type)


class ServiceRegistrationError(ServiceError):
    """Exception raised when service registration fails validation."""
    
    def __init__(
        self,
        message: str,
        service_type: str | None = None,
        registration_type: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        details = {}
        if service_type:
            details["service_type"] = service_type
        if registration_type:
            details["registration_type"] = registration_type
        if details:
            self.with_details(**details)


class ServiceNotFoundError(ServiceError):
    """Exception raised when a requested service is not found."""
    
    def __init__(
        self,
        message: str,
        service_type: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if service_type:
            self.with_details(service_type=service_type)


# Validation-related exceptions
class ValidationError(AccordoError):
    """Exception raised for data validation errors."""
    
    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        invalid_value: Any | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        details = {}
        if field_name:
            details["field_name"] = field_name
        if invalid_value is not None:
            details["invalid_value"] = str(invalid_value)
        if details:
            self.with_details(**details)


# Network and external service exceptions
class NetworkError(AccordoError):
    """Exception raised for network-related errors."""
    
    def __init__(
        self,
        message: str,
        endpoint: str | None = None,
        status_code: int | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        details = {}
        if endpoint:
            details["endpoint"] = endpoint
        if status_code:
            details["status_code"] = status_code
        if details:
            self.with_details(**details)


class ExternalServiceError(NetworkError):
    """Exception raised when external service calls fail."""
    pass


# File and path-related exceptions
class PathError(AccordoError):
    """Exception raised for path-related errors."""
    
    def __init__(
        self,
        message: str,
        path: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if path:
            self.with_details(path=path)


class FileOperationError(PathError):
    """Exception raised when file operations fail."""
    
    def __init__(
        self,
        message: str,
        operation: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if operation:
            self.with_details(operation=operation)


# Template and generation exceptions
class TemplateError(AccordoError):
    """Exception raised for template-related errors."""
    pass


class TemplateGenerationError(TemplateError):
    """Exception raised when template generation fails."""
    
    def __init__(
        self,
        message: str,
        template_name: str | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if template_name:
            self.with_details(template_name=template_name)


# Utility functions for error handling
def create_error_response(
    error: AccordoError,
    include_traceback: bool = False
) -> dict[str, Any]:
    """Create a standardized error response dictionary.
    
    Args:
        error: The AccordoError instance
        include_traceback: Whether to include traceback information
        
    Returns:
        Standardized error response dictionary
    """
    response = {
        "success": False,
        "error": error.to_dict()
    }
    
    if include_traceback and error.cause:
        import traceback
        response["error"]["traceback"] = traceback.format_exception(
            type(error.cause), error.cause, error.cause.__traceback__
        )
    
    return response


def wrap_exception(
    exception: Exception,
    error_class: type[AccordoError] = AccordoError,
    message: str | None = None,
    **kwargs
) -> AccordoError:
    """Wrap a generic exception in an AccordoError.
    
    Args:
        exception: The original exception
        error_class: AccordoError subclass to use
        message: Optional custom message
        **kwargs: Additional error details
        
    Returns:
        Wrapped AccordoError instance
    """
    wrapped_message = message or f"Wrapped exception: {str(exception)}"
    return error_class(
        message=wrapped_message,
        cause=exception,
        **kwargs
    ) 