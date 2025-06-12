"""Structured error response patterns for Accordo Workflow MCP.

This module provides standardized error response formats, middleware patterns,
and utilities for consistent error handling across API endpoints and service interfaces.
"""

import functools
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from .exceptions import AccordoError
from .logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)

# Type variables for generic functions
F = TypeVar('F', bound=Callable[..., Any])


class ErrorSeverity(Enum):
    """Enumeration of error severity levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HTTPStatusCode(Enum):
    """Common HTTP status codes for error responses."""
    
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


class ErrorResponseFormat:
    """Standardized error response format for API endpoints."""
    
    def __init__(
        self,
        success: bool = False,
        error_type: str = "UnknownError",
        message: str = "An error occurred",
        error_code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        http_status: HTTPStatusCode = HTTPStatusCode.INTERNAL_SERVER_ERROR,
        traceback: Optional[list[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Initialize error response format.
        
        Args:
            success: Always False for error responses
            error_type: Type of error (exception class name)
            message: Human-readable error message
            error_code: Standardized error code for programmatic handling
            details: Additional structured error details
            correlation_id: Request correlation ID for tracing
            timestamp: ISO formatted timestamp of error occurrence
            severity: Error severity level
            http_status: HTTP status code for the response
            traceback: Optional traceback information (for debugging)
            context: Additional context information
        """
        self.success = success
        self.error_type = error_type
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.correlation_id = correlation_id
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.severity = severity
        self.http_status = http_status
        self.traceback = traceback
        self.context = context or {}
    
    def to_dict(self, include_traceback: bool = False) -> Dict[str, Any]:
        """Convert error response to dictionary.
        
        Args:
            include_traceback: Whether to include traceback in response
            
        Returns:
            Dictionary representation of error response
        """
        response = {
            "success": self.success,
            "error": {
                "type": self.error_type,
                "message": self.message,
                "code": self.error_code,
                "details": self.details,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp,
                "severity": self.severity.value,
            },
            "http_status": self.http_status.value,
            "context": self.context
        }
        
        if include_traceback and self.traceback:
            response["error"]["traceback"] = self.traceback
            
        return response
    
    def to_json(self, include_traceback: bool = False) -> str:
        """Convert error response to JSON string.
        
        Args:
            include_traceback: Whether to include traceback in response
            
        Returns:
            JSON representation of error response
        """
        import json
        return json.dumps(self.to_dict(include_traceback), indent=2)
    
    @classmethod
    def from_accordo_error(
        cls,
        error: AccordoError,
        severity: Optional[ErrorSeverity] = None,
        http_status: Optional[HTTPStatusCode] = None,
        include_traceback: bool = False
    ) -> "ErrorResponseFormat":
        """Create error response from AccordoError instance.
        
        Args:
            error: AccordoError instance
            severity: Override error severity
            http_status: Override HTTP status code
            include_traceback: Whether to include traceback
            
        Returns:
            ErrorResponseFormat instance
        """
        # Determine appropriate HTTP status code based on error type
        if http_status is None:
            http_status = cls._map_error_to_http_status(error)
            
        # Determine severity if not provided
        if severity is None:
            severity = cls._map_error_to_severity(error)
            
        # Extract traceback if available and requested
        traceback_info = None
        if include_traceback and error.cause:
            traceback_info = traceback.format_exception(
                type(error.cause), error.cause, error.cause.__traceback__
            )
        
        return cls(
            error_type=error.__class__.__name__,
            message=error.message,
            error_code=error.error_code,
            details=error.details,
            correlation_id=error.correlation_id,
            timestamp=error.timestamp,
            severity=severity,
            http_status=http_status,
            traceback=traceback_info,
            context={"source_module": error.source_module} if error.source_module else {}
        )
    
    @staticmethod
    def _map_error_to_http_status(error: AccordoError) -> HTTPStatusCode:
        """Map AccordoError types to appropriate HTTP status codes."""
        # Import here to avoid circular imports
        from .exceptions import (
            ValidationError, ConfigurationError, SessionNotFoundError,
            NetworkError, CacheError, ServiceError
        )
        
        error_type = type(error)
        
        if issubclass(error_type, ValidationError):
            return HTTPStatusCode.BAD_REQUEST
        elif issubclass(error_type, (SessionNotFoundError,)):
            return HTTPStatusCode.NOT_FOUND
        elif issubclass(error_type, ConfigurationError):
            return HTTPStatusCode.UNPROCESSABLE_ENTITY
        elif issubclass(error_type, NetworkError):
            return HTTPStatusCode.SERVICE_UNAVAILABLE
        elif issubclass(error_type, (CacheError, ServiceError)):
            return HTTPStatusCode.INTERNAL_SERVER_ERROR
        else:
            return HTTPStatusCode.INTERNAL_SERVER_ERROR
    
    @staticmethod
    def _map_error_to_severity(error: AccordoError) -> ErrorSeverity:
        """Map AccordoError types to appropriate severity levels."""
        # Import here to avoid circular imports
        from .exceptions import (
            ValidationError, ConfigurationError, SessionNotFoundError,
            NetworkError, CacheError, ServiceError
        )
        
        error_type = type(error)
        
        if issubclass(error_type, ValidationError):
            return ErrorSeverity.LOW
        elif issubclass(error_type, (SessionNotFoundError, ConfigurationError)):
            return ErrorSeverity.MEDIUM
        elif issubclass(error_type, (NetworkError, CacheError)):
            return ErrorSeverity.HIGH
        elif issubclass(error_type, ServiceError):
            return ErrorSeverity.CRITICAL
        else:
            return ErrorSeverity.MEDIUM


def create_error_response(
    error: Union[AccordoError, Exception, str],
    correlation_id: Optional[str] = None,
    include_traceback: bool = False,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized error response from various error types.
    
    Args:
        error: Error instance, exception, or error message
        correlation_id: Optional correlation ID for request tracing
        include_traceback: Whether to include traceback information
        context: Additional context information
        
    Returns:
        Standardized error response dictionary
    """
    if isinstance(error, AccordoError):
        # Create response from AccordoError
        response_format = ErrorResponseFormat.from_accordo_error(
            error, include_traceback=include_traceback
        )
        if context:
            response_format.context.update(context)
        return response_format.to_dict(include_traceback)
    
    elif isinstance(error, Exception):
        # Convert generic exception to AccordoError
        from .exceptions import wrap_exception
        accordo_error = wrap_exception(
            error,
            AccordoError,
            correlation_id=correlation_id
        )
        response_format = ErrorResponseFormat.from_accordo_error(
            accordo_error, include_traceback=include_traceback
        )
        if context:
            response_format.context.update(context)
        return response_format.to_dict(include_traceback)
    
    elif isinstance(error, str):
        # Create response from error message
        response_format = ErrorResponseFormat(
            message=error,
            correlation_id=correlation_id,
            context=context or {}
        )
        return response_format.to_dict(include_traceback)
    
    else:
        # Fallback for unexpected error types
        response_format = ErrorResponseFormat(
            message=f"Unexpected error type: {type(error).__name__}",
            correlation_id=correlation_id,
            context=context or {}
        )
        return response_format.to_dict(include_traceback)


def create_success_response(
    data: Any = None,
    message: str = "Operation completed successfully",
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized success response.
    
    Args:
        data: Response data payload
        message: Success message
        correlation_id: Optional correlation ID for request tracing
        context: Additional context information
        
    Returns:
        Standardized success response dictionary
    """
    response = {
        "success": True,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = data
        
    if correlation_id:
        response["correlation_id"] = correlation_id
        
    if context:
        response["context"] = context
        
    return response


def error_handler_middleware(
    include_traceback: bool = False,
    log_errors: bool = True
) -> Callable[[F], F]:
    """Decorator for standardized error handling in API endpoints and service methods.
    
    Args:
        include_traceback: Whether to include traceback in error responses
        log_errors: Whether to log errors using the logging system
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                result = func(*args, **kwargs)
                
                # If result is already a standardized response, return as-is
                if isinstance(result, dict) and "success" in result:
                    return result
                    
                # Wrap successful results in standardized response
                return create_success_response(
                    data=result,
                    context={"function": func.__name__}
                )
                
            except AccordoError as e:
                # Log AccordoError with structured information
                if log_errors:
                    logger.error(
                        f"AccordoError in {func.__name__}",
                        **e.to_dict()
                    )
                
                return create_error_response(
                    e,
                    include_traceback=include_traceback,
                    context={"function": func.__name__}
                )
                
            except Exception as e:
                # Log generic exceptions
                if log_errors:
                    logger.exception(
                        f"Unexpected error in {func.__name__}",
                        function=func.__name__,
                        error_type=type(e).__name__,
                        error_message=str(e)
                    )
                
                return create_error_response(
                    e,
                    include_traceback=include_traceback,
                    context={"function": func.__name__}
                )
                
        return wrapper
    return decorator


def validate_and_handle_errors(
    validation_func: Callable[[Any], Optional[str]],
    include_traceback: bool = False
) -> Callable[[F], F]:
    """Decorator for input validation with standardized error responses.
    
    Args:
        validation_func: Function that validates input and returns error message or None
        include_traceback: Whether to include traceback in error responses
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Validate inputs
            validation_error = validation_func(kwargs)
            if validation_error:
                from .exceptions import ValidationError
                error = ValidationError(validation_error)
                return create_error_response(
                    error,
                    include_traceback=include_traceback,
                    context={"function": func.__name__, "validation_failed": True}
                )
            
            # Proceed with original function
            return func(*args, **kwargs)
            
        return wrapper
    return decorator


# Utility functions for common error scenarios
def create_not_found_response(
    resource_type: str,
    resource_id: str,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standardized 'not found' error response."""
    from .exceptions import SessionNotFoundError
    
    error = SessionNotFoundError(
        f"{resource_type} not found: {resource_id}",
        correlation_id=correlation_id
    ).with_details(resource_type=resource_type, resource_id=resource_id)
    
    return create_error_response(error)


def create_validation_error_response(
    validation_errors: list[str],
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standardized validation error response."""
    from .exceptions import ValidationError
    
    error = ValidationError(
        "Validation failed",
        correlation_id=correlation_id
    ).with_details(validation_errors=validation_errors)
    
    return create_error_response(error)


def create_service_unavailable_response(
    service_name: str,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standardized service unavailable error response."""
    from .exceptions import ServiceError
    
    error = ServiceError(
        f"Service unavailable: {service_name}",
        correlation_id=correlation_id
    ).with_details(service_name=service_name, availability=False)
    
    return create_error_response(error)


# Response format validation
def validate_response_format(response: Dict[str, Any]) -> list[str]:
    """Validate that a response follows the standardized format.
    
    Args:
        response: Response dictionary to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check required fields
    if "success" not in response:
        errors.append("Missing required field: success")
    elif not isinstance(response["success"], bool):
        errors.append("Field 'success' must be a boolean")
    
    # For error responses
    if response.get("success") is False:
        if "error" not in response:
            errors.append("Error responses must contain 'error' field")
        else:
            error = response["error"]
            required_error_fields = ["type", "message", "code"]
            for field in required_error_fields:
                if field not in error:
                    errors.append(f"Missing required error field: {field}")
    
    # For success responses
    if response.get("success") is True:
        if "message" not in response:
            errors.append("Success responses should contain 'message' field")
    
    return errors 


def add_session_id_to_response(
    response: Union[str, Dict[str, Any]], 
    session_id: str
) -> Union[str, Dict[str, Any]]:
    """Add session_id to a response, handling both string and dict responses.
    
    Args:
        response: The response to add session_id to
        session_id: The session ID to add
        
    Returns:
        Response with session_id added
    """
    if isinstance(response, dict):
        # Add session_id to dictionary response
        response_copy = response.copy()
        response_copy["session_id"] = session_id
        return response_copy
    else:
        # For string responses, convert to dict with content and session_id
        return {
            "content": str(response),
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }