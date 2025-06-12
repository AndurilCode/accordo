"""MCP-specific error handling middleware for FastMCP tools."""

import functools
import json
from collections.abc import Callable
from typing import Any, TypeVar

from .error_responses import add_session_id_to_response, create_error_response
from .exceptions import AccordoError, ValidationError, wrap_exception
from .logging_config import get_logger

logger = get_logger(__name__)

# Type variable for function decoration
F = TypeVar('F', bound=Callable[..., Any])


def _log(level: str, message: str, **kwargs) -> None:
    """Internal logging function."""
    logger_method = getattr(logger, level.lower(), logger.info)
    logger_method(message, **kwargs)


class MCPErrorHandler:
    """Error handler specifically designed for MCP tools."""
    
    def __init__(
        self,
        include_traceback: bool = False,
        log_errors: bool = True,
        standardize_responses: bool = True,
        include_session_id: bool = True
    ):
        """Initialize MCP error handler.
        
        Args:
            include_traceback: Whether to include traceback in error responses
            log_errors: Whether to log errors using the logging system
            standardize_responses: Whether to standardize all responses
            include_session_id: Whether to include session_id in responses
        """
        self.include_traceback = include_traceback
        self.log_errors = log_errors
        self.standardize_responses = standardize_responses
        self.include_session_id = include_session_id
    
    def __call__(self, func: F) -> F:
        """Apply error handling to function."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> str | dict[str, Any]:
            # Extract context and session information
            ctx = kwargs.get('ctx')
            session_id = kwargs.get('session_id', '')
            
            # Extract correlation ID from context if available
            correlation_id = None
            if ctx and hasattr(ctx, 'client_id'):
                correlation_id = getattr(ctx, 'correlation_id', ctx.client_id)
            
            try:
                # Execute the original function
                result = func(*args, **kwargs)
                
                # Handle different result types
                if isinstance(result, str):
                    # String result - typical for MCP tools
                    if self.standardize_responses:
                        from .error_responses import create_success_response
                        response = create_success_response(
                            data={"content": result},
                            message="Operation completed successfully",
                            correlation_id=correlation_id,
                            context={"tool": func.__name__}
                        )
                    else:
                        response = result
                
                elif isinstance(result, dict):
                    # Dict result - check if already standardized
                    if "success" in result:
                        response = result  # Already standardized
                    else:
                        if self.standardize_responses:
                            from .error_responses import create_success_response
                            response = create_success_response(
                                data=result,
                                correlation_id=correlation_id,
                                context={"tool": func.__name__}
                            )
                        else:
                            response = result
                else:
                    # Other result types
                    if self.standardize_responses:
                        from .error_responses import create_success_response
                        response = create_success_response(
                            data=result,
                            correlation_id=correlation_id,
                            context={"tool": func.__name__}
                        )
                    else:
                        response = str(result)
                
                # Add session_id if requested and available
                if self.include_session_id and session_id:
                    if isinstance(response, dict):
                        response = add_session_id_to_response(response, session_id)
                    else:
                        # For string responses, we need to decide how to include session_id
                        # Return as dict with content and session_id
                        response = add_session_id_to_response(response, session_id)
                
                return response
                
            except ValidationError as e:
                # Handle validation errors specifically
                if self.log_errors:
                    error_dict = e.to_dict()
                    logger.warning(
                        f"Validation error in {func.__name__}",
                        error_type=error_dict.get('type'),
                        error_code=error_dict.get('code'),
                        error_details=error_dict.get('details')
                    )
                
                error_response = create_error_response(
                    e,
                    correlation_id=correlation_id,
                    include_traceback=self.include_traceback,
                    context={"tool": func.__name__, "error_category": "validation"}
                )
                
                if self.include_session_id and session_id:
                    error_response = add_session_id_to_response(error_response, session_id)
                
                # MCP tools typically return strings, so convert to string for consistency
                return json.dumps(error_response, indent=2) if isinstance(error_response, dict) else str(error_response)
                
            except AccordoError as e:
                # Handle AccordoError instances with structured information
                if self.log_errors:
                    error_dict = e.to_dict()
                    logger.error(
                        f"AccordoError in {func.__name__}",
                        error_type=error_dict.get('type'),
                        error_code=error_dict.get('code'),
                        error_details=error_dict.get('details')
                    )
                
                error_response = create_error_response(
                    e,
                    correlation_id=correlation_id,
                    include_traceback=self.include_traceback,
                    context={"tool": func.__name__, "error_category": "accordo"}
                )
                
                if self.include_session_id and session_id:
                    error_response = add_session_id_to_response(error_response, session_id)
                
                return json.dumps(error_response, indent=2) if isinstance(error_response, dict) else str(error_response)
                
            except Exception as e:
                # Handle unexpected exceptions
                if self.log_errors:
                    logger.exception(
                        f"Unexpected error in MCP tool {func.__name__}",
                        tool=func.__name__,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        session_id=session_id,
                        correlation_id=correlation_id
                    )
                
                # Convert to AccordoError for consistent handling
                accordo_error = wrap_exception(
                    e,
                    AccordoError,
                    message=f"Unexpected error in {func.__name__}",
                    correlation_id=correlation_id
                ).with_details(
                    tool=func.__name__,
                    original_error_type=type(e).__name__
                )
                
                error_response = create_error_response(
                    accordo_error,
                    correlation_id=correlation_id,
                    include_traceback=self.include_traceback,
                    context={"tool": func.__name__, "error_category": "unexpected"}
                )
                
                if self.include_session_id and session_id:
                    error_response = add_session_id_to_response(error_response, session_id)
                
                return json.dumps(error_response, indent=2) if isinstance(error_response, dict) else str(error_response)
        
        return wrapper


def mcp_error_handler(
    include_traceback: bool = False,
    log_errors: bool = True,
    standardize_responses: bool = False,  # Default False for MCP compatibility
    include_session_id: bool = True
) -> Callable[[F], F]:
    """Decorator for MCP tool error handling.
    
    Args:
        include_traceback: Whether to include traceback in error responses
        log_errors: Whether to log errors using the logging system
        standardize_responses: Whether to standardize all responses (may break MCP compatibility)
        include_session_id: Whether to include session_id in responses
        
    Returns:
        Decorator function
    """
    handler = MCPErrorHandler(
        include_traceback=include_traceback,
        log_errors=log_errors,
        standardize_responses=standardize_responses,
        include_session_id=include_session_id
    )
    return handler


def validate_mcp_parameters(**validation_rules) -> Callable[[F], F]:
    """Decorator for MCP parameter validation.
    
    Args:
        **validation_rules: Dictionary of parameter name to validation function
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            validation_errors = []
            
            # Validate each parameter
            for param_name, validation_func in validation_rules.items():
                if param_name in kwargs:
                    param_value = kwargs[param_name]
                    try:
                        if callable(validation_func):
                            validation_result = validation_func(param_value)
                            if validation_result is not None and validation_result is not True:
                                validation_errors.append(f"{param_name}: {validation_result}")
                    except Exception as e:
                        validation_errors.append(f"{param_name}: Validation failed - {str(e)}")
            
            # If validation errors, raise ValidationError
            if validation_errors:
                raise ValidationError(
                    f"Parameter validation failed for {func.__name__}",
                ).with_details(validation_errors=validation_errors)
            
            # Proceed with original function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_session_id(func: F) -> F:
    """Decorator to ensure session_id is provided and valid."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        session_id = kwargs.get('session_id', '')
        
        # Handle Field defaults that may be FieldInfo objects
        if hasattr(session_id, 'default'):
            session_id = session_id.default if session_id.default else ''
        
        # Ensure it's a string
        session_id = str(session_id) if session_id is not None else ''
        
        if not session_id or not session_id.strip():
            raise ValidationError(
                "Session ID is required for this operation"
            ).with_details(
                function=func.__name__,
                required_parameter="session_id"
            )
        
        # Update kwargs with clean session_id
        kwargs['session_id'] = session_id.strip()
        
        return func(*args, **kwargs)
    
    return wrapper


def require_task_description_format(func: F) -> F:
    """Decorator to validate task_description follows required format."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        task_description = kwargs.get('task_description')
        
        if not task_description:
            raise ValidationError(
                "Task description is required"
            ).with_details(
                function=func.__name__,
                required_parameter="task_description",
                required_format="Action: Brief description"
            )
        
        # Validate format
        if isinstance(task_description, str):
            description = task_description.strip()
            if ":" not in description:
                raise ValidationError(
                    "Task description must follow format 'Action: Brief description'"
                ).with_details(
                    function=func.__name__,
                    provided_description=description,
                    required_format="Action: Brief description"
                )
        
        return func(*args, **kwargs)
    
    return wrapper


def log_mcp_tool_usage(func: F) -> F:
    """Decorator to log MCP tool usage."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Extract relevant information
        session_id = kwargs.get('session_id', 'unknown')
        task_description = kwargs.get('task_description', 'No description')
        
        # Log tool invocation
        _log('info', f"MCP tool invoked: {func.__name__}", 
             tool=func.__name__, 
             session_id=session_id,
             task_description=task_description)
        
        try:
            result = func(*args, **kwargs)
            _log('info', f"MCP tool completed: {func.__name__}",
                 tool=func.__name__,
                 session_id=session_id,
                 success=True)
            return result
        except Exception as e:
            _log('error', f"MCP tool failed: {func.__name__}",
                 tool=func.__name__,
                 session_id=session_id,
                 error=str(e),
                 success=False)
            raise
    
    return wrapper


def format_mcp_response(
    content: Any,
    session_id: str | None = None,
    success: bool = True,
    error_info: dict[str, Any] | None = None
) -> str:
    """Format a response for MCP tools.
    
    Args:
        content: Response content
        session_id: Optional session ID
        success: Whether the operation was successful
        error_info: Optional error information
        
    Returns:
        Formatted response string
    """
    response = {
        "success": success,
        "content": content,
        "timestamp": _get_timestamp()
    }
    
    if session_id:
        response["session_id"] = session_id
    
    if error_info:
        response["error"] = error_info
    
    return json.dumps(response, indent=2)


def _get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"


def extract_mcp_parameters(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Extract and validate MCP-specific parameters.
    
    Args:
        kwargs: Function keyword arguments
        
    Returns:
        Dictionary of extracted MCP parameters
    """
    mcp_params = {}
    
    # Extract session_id
    session_id = kwargs.get('session_id')
    if session_id:
        mcp_params['session_id'] = str(session_id).strip()
    
    # Extract task_description
    task_description = kwargs.get('task_description')
    if task_description:
        mcp_params['task_description'] = str(task_description).strip()
    
    # Extract context
    context = kwargs.get('context')
    if context:
        mcp_params['context'] = context
    
    return mcp_params


def validate_json_parameter(param_value: str, param_name: str) -> dict[str, Any]:
    """Validate and parse a JSON parameter.
    
    Args:
        param_value: The parameter value to validate
        param_name: Name of the parameter for error messages
        
    Returns:
        Parsed JSON object
        
    Raises:
        ValidationError: If JSON is invalid
    """
    if not param_value or not param_value.strip():
        return {}
    
    try:
        parsed = json.loads(param_value)
        if not isinstance(parsed, dict):
            raise ValidationError(
                f"Parameter '{param_name}' must be a JSON object"
            ).with_details(
                parameter=param_name,
                provided_type=type(parsed).__name__,
                expected_type="dict"
            )
        return parsed
    except json.JSONDecodeError as e:
        raise ValidationError(
            f"Parameter '{param_name}' contains invalid JSON"
        ).with_details(
            parameter=param_name,
            json_error=str(e),
            provided_value=param_value[:100] + "..." if len(param_value) > 100 else param_value
        )


def mcp_tool_protection(
    include_traceback: bool = False,
    require_session: bool = False,
    require_task_format: bool = False,
    log_usage: bool = True,
    custom_validation: dict[str, Callable] | None = None
) -> Callable[[F], F]:
    """Comprehensive MCP tool protection decorator.
    
    Args:
        include_traceback: Include traceback in error responses
        require_session: Require session_id parameter
        require_task_format: Require task_description format validation
        log_usage: Log tool usage
        custom_validation: Custom parameter validation rules
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        # Apply decorators in reverse order (innermost first)
        protected_func = func
        
        # Apply custom validation if provided
        if custom_validation:
            protected_func = validate_mcp_parameters(**custom_validation)(protected_func)
        
        # Apply task format validation if required
        if require_task_format:
            protected_func = require_task_description_format(protected_func)
        
        # Apply session requirement if needed
        if require_session:
            protected_func = require_session_id(protected_func)
        
        # Apply usage logging if enabled
        if log_usage:
            protected_func = log_mcp_tool_usage(protected_func)
        
        # Apply error handling (outermost)
        protected_func = mcp_error_handler(
            include_traceback=include_traceback,
            log_errors=True,
            standardize_responses=False,  # Keep MCP compatibility
            include_session_id=True
        )(protected_func)
        
        return protected_func
    
    return decorator 