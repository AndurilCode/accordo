"""Centralized logging configuration for Accordo Workflow MCP.

This module provides structured logging with JSON formatting, file rotation,
correlation IDs, and consistent message formatting across all components.
"""

import json
import logging
import logging.handlers
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Thread-local storage for correlation IDs
import threading
_local = threading.local()


class AccordoJSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON formatted log message
        """
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if available
        correlation_id = getattr(_local, 'correlation_id', None)
        if correlation_id:
            log_data["correlation_id"] = correlation_id
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        # Add extra fields from the log record
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                'filename', 'module', 'lineno', 'funcName', 'created', 
                'msecs', 'relativeCreated', 'thread', 'threadName', 
                'processName', 'process', 'getMessage', 'exc_info', 'exc_text',
                'stack_info', 'message'
            ]:
                log_data[key] = value
                
        return json.dumps(log_data, default=str)


class AccordoConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[41m',  # Red background
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log message with colors
        """
        # Get correlation ID if available
        correlation_id = getattr(_local, 'correlation_id', None)
        correlation_part = f" [{correlation_id[:8]}]" if correlation_id else ""
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # Get color for log level
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Build the message
        message = (
            f"{color}{timestamp} [{record.levelname:8}]{reset} "
            f"{record.name}:{record.funcName}:{record.lineno}{correlation_part} - "
            f"{record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
            
        return message


class CorrelationFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to the log record.
        
        Args:
            record: The log record to filter
            
        Returns:
            True to allow the record to be logged
        """
        correlation_id = getattr(_local, 'correlation_id', None)
        if correlation_id:
            record.correlation_id = correlation_id
        return True


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for the current thread.
    
    Args:
        correlation_id: The correlation ID to set
    """
    _local.correlation_id = correlation_id


def get_correlation_id() -> Optional[str]:
    """Get correlation ID for the current thread.
    
    Returns:
        The correlation ID or None if not set
    """
    return getattr(_local, 'correlation_id', None)


def clear_correlation_id() -> None:
    """Clear correlation ID for the current thread."""
    if hasattr(_local, 'correlation_id'):
        delattr(_local, 'correlation_id')


def generate_correlation_id() -> str:
    """Generate a new correlation ID.
    
    Returns:
        A new UUID-based correlation ID
    """
    return str(uuid.uuid4())


class AccordoLogger:
    """Enhanced logger with structured logging capabilities."""
    
    def __init__(self, name: str):
        """Initialize AccordoLogger.
        
        Args:
            name: Logger name
        """
        self.name = name  # Store name for compatibility
        self.logger = logging.getLogger(name)
        self._ensure_handlers_configured()
    
    def _ensure_handlers_configured(self) -> None:
        """Ensure logger has proper handlers configured."""
        if not self.logger.handlers:
            configure_logging()
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional structured data."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with optional structured data."""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional structured data."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with optional structured data."""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with optional structured data."""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback and optional structured data."""
        kwargs['exc_info'] = True
        self._log(logging.ERROR, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs) -> None:
        """Internal logging method with structured data support.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional structured data
        """
        # Create a record and add extra fields
        extra = {}
        for key, value in kwargs.items():
            if key != 'exc_info':
                extra[key] = value
        
        self.logger.log(level, message, extra=extra, **{k: v for k, v in kwargs.items() if k == 'exc_info'})
    
    def with_correlation_id(self, correlation_id: str) -> "AccordoLogger":
        """Create logger context with correlation ID.
        
        Args:
            correlation_id: Correlation ID to use
            
        Returns:
            Self for method chaining
        """
        set_correlation_id(correlation_id)
        return self
    
    def with_context(self, context: Dict[str, Any] = None, **kwargs) -> "AccordoLogger":
        """Add context to subsequent log messages.
        
        Args:
            context: Context dictionary to add
            **kwargs: Additional context to add
            
        Returns:
            Self for method chaining
        """
        # Store context in thread-local storage
        if not hasattr(_local, 'context'):
            _local.context = {}
        
        if context:
            _local.context.update(context)
        _local.context.update(kwargs)
        return self


def configure_logging(
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    json_logs: bool = True
) -> None:
    """Configure centralized logging system.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (defaults to .accordo/logs)
        enable_console: Whether to enable console output
        enable_file: Whether to enable file output
        max_file_size: Maximum size of each log file in bytes
        backup_count: Number of backup files to keep
        json_logs: Whether to use JSON formatting for file logs
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Get root logger and clear existing handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set up log directory
    if log_dir is None:
        log_dir = Path.home() / ".accordo" / "logs"
    else:
        log_dir = Path(log_dir)
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(AccordoConsoleFormatter())
        console_handler.addFilter(CorrelationFilter())
        root_logger.addHandler(console_handler)
    
    # Configure file handler with rotation
    if enable_file:
        log_file = log_dir / "accordo.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        
        if json_logs:
            file_handler.setFormatter(AccordoJSONFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            ))
        
        file_handler.addFilter(CorrelationFilter())
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers with appropriate levels
    _configure_module_loggers(numeric_level)


def _configure_module_loggers(base_level: int) -> None:
    """Configure specific loggers for different modules.
    
    Args:
        base_level: Base logging level
    """
    # Module-specific log levels
    module_levels = {
        'accordo_workflow_mcp.utils.cache_manager': logging.WARNING,
        'accordo_workflow_mcp.services.session_lifecycle_manager': logging.INFO,
        'accordo_workflow_mcp.utils.session_manager': logging.INFO,
        'accordo_workflow_mcp.prompts.phase_prompts': logging.INFO,
        'accordo_workflow_mcp.utils.workflow_engine': logging.DEBUG,
        'accordo_workflow_mcp.services.dependency_injection': logging.WARNING,
    }
    
    for module_name, level in module_levels.items():
        logger = logging.getLogger(module_name)
        logger.setLevel(max(level, base_level))


def get_logger(name: str) -> AccordoLogger:
    """Get an AccordoLogger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        AccordoLogger instance
    """
    return AccordoLogger(name)


def log_function_call(func_name: str, **kwargs) -> None:
    """Log a function call with parameters.
    
    Args:
        func_name: Name of the function being called
        **kwargs: Function parameters to log
    """
    logger = get_logger("accordo_workflow_mcp.function_calls")
    logger.debug(f"Function call: {func_name}", function=func_name, parameters=kwargs)


def log_performance(operation: str, duration_ms: float, **kwargs) -> None:
    """Log performance metrics.
    
    Args:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        **kwargs: Additional performance metrics
    """
    logger = get_logger("accordo_workflow_mcp.performance")
    logger.info(
        f"Performance: {operation} completed in {duration_ms:.2f}ms",
        operation=operation,
        duration_ms=duration_ms,
        **kwargs
    )


def log_security_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log security-related events.
    
    Args:
        event_type: Type of security event
        details: Event details
    """
    logger = get_logger("accordo_workflow_mcp.security")
    logger.warning(f"Security event: {event_type}", event_type=event_type, **details)


def log_error_with_context(
    error: Exception,
    context: Dict[str, Any],
    logger_name: str = "accordo_workflow_mcp.errors"
) -> None:
    """Log an error with additional context information.
    
    Args:
        error: The exception that occurred
        context: Additional context information
        logger_name: Name of the logger to use
    """
    logger = get_logger(logger_name)
    logger.exception(f"Error occurred: {str(error)}", error_type=type(error).__name__, **context)


# Context managers for structured logging
class LoggingContext:
    """Context manager for structured logging with automatic cleanup."""
    
    def __init__(self, correlation_id: Optional[str] = None, **context):
        """Initialize logging context.
        
        Args:
            correlation_id: Optional correlation ID
            **context: Additional context to set
        """
        self.correlation_id = correlation_id or generate_correlation_id()
        self.context = context
        self.previous_correlation_id = None
        self.previous_context = None
    
    def __enter__(self) -> "LoggingContext":
        """Enter logging context."""
        # Save previous state
        self.previous_correlation_id = get_correlation_id()
        self.previous_context = getattr(_local, 'context', {}).copy()
        
        # Set new state
        set_correlation_id(self.correlation_id)
        if not hasattr(_local, 'context'):
            _local.context = {}
        _local.context.update(self.context)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit logging context and restore previous state."""
        # Restore previous state
        if self.previous_correlation_id:
            set_correlation_id(self.previous_correlation_id)
        else:
            clear_correlation_id()
        
        if hasattr(_local, 'context'):
            _local.context = self.previous_context


# Initialize logging on module import
def _initialize_default_logging():
    """Initialize default logging configuration."""
    try:
        # Try to get log level from environment
        log_level = os.getenv('ACCORDO_LOG_LEVEL', 'INFO')
        
        # Configure logging with defaults
        configure_logging(
            log_level=log_level,
            enable_console=True,
            enable_file=True,
            json_logs=True
        )
    except Exception:
        # Fallback to basic configuration if anything fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


# Initialize on import
_initialize_default_logging() 