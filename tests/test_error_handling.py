"""Test suite for standardized error handling system.

This module provides comprehensive tests for the AccordoError hierarchy,
logging configuration, error response patterns, and MCP middleware.
"""

import json
import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import modules to test
from accordo_workflow_mcp.error_responses import (
    ErrorResponseFormat,
    ErrorSeverity,
    HTTPStatusCode,
    create_error_response,
    create_success_response,
    validate_response_format,
)
from accordo_workflow_mcp.exceptions import (
    AccordoError,
    CacheError,
    ConfigurationError,
    NetworkError,
    ServiceError,
    SessionNotFoundError,
    ValidationError,
    WorkflowError,
    wrap_exception,
)
from accordo_workflow_mcp.logging_config import (
    AccordoLogger,
    configure_logging,
    get_logger,
    set_correlation_id,
)
from accordo_workflow_mcp.mcp_error_middleware import (
    MCPErrorHandler,
    mcp_error_handler,
    mcp_tool_protection,
    require_session_id,
    validate_json_parameter,
)


class TestAccordoErrorHierarchy:
    """Test the AccordoError exception hierarchy."""
    
    def test_base_accordo_error(self):
        """Test basic AccordoError functionality."""
        error = AccordoError("Test error message")
        
        assert error.message == "Test error message"
        assert error.error_code == "ACCORDO_ERROR"
        assert error.correlation_id is not None
        assert error.timestamp is not None
        assert error.details == {}
        
    def test_accordo_error_with_details(self):
        """Test AccordoError with additional details."""
        details = {"param1": "value1", "param2": "value2"}
        error = AccordoError("Test error", details=details)
        
        assert error.details == details
        assert error.to_dict()["details"] == details
        
    def test_accordo_error_method_chaining(self):
        """Test method chaining functionality."""
        correlation_id = str(uuid.uuid4())
        error = (AccordoError("Test error")
                .with_details(key1="value1")
                .with_correlation_id(correlation_id))
        
        assert error.details["key1"] == "value1"
        assert error.correlation_id == correlation_id
        
    def test_accordo_error_serialization(self):
        """Test error serialization methods."""
        error = AccordoError("Test error").with_details(test_key="test_value")
        
        # Test to_dict
        error_dict = error.to_dict()
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "ACCORDO_ERROR"
        assert error_dict["details"]["test_key"] == "test_value"
        
        # Test to_json
        error_json = error.to_json()
        parsed = json.loads(error_json)
        assert parsed["message"] == "Test error"
        
    def test_specific_error_types(self):
        """Test specific error type instantiation and codes."""
        validation_error = ValidationError("Invalid input")
        assert validation_error.error_code == "VALIDATION_ERROR"
        
        session_error = SessionNotFoundError("Session not found")
        assert session_error.error_code == "SESSION_NOT_FOUND_ERROR"
        
        config_error = ConfigurationError("Invalid config")
        assert config_error.error_code == "CONFIGURATION_ERROR"
        
        workflow_error = WorkflowError("Workflow failed")
        assert workflow_error.error_code == "WORKFLOW_ERROR"
        
        cache_error = CacheError("Cache operation failed")
        assert cache_error.error_code == "CACHE_ERROR"
        
        service_error = ServiceError("Service unavailable")
        assert service_error.error_code == "SERVICE_ERROR"
        
        network_error = NetworkError("Connection failed")
        assert network_error.error_code == "NETWORK_ERROR"
        
    def test_wrap_exception_utility(self):
        """Test the wrap_exception utility function."""
        original_error = ValueError("Original error message")
        
        wrapped = wrap_exception(
            original_error,
            ValidationError,
            message="Custom message",
            correlation_id="test-123"
        )
        
        assert isinstance(wrapped, ValidationError)
        assert wrapped.message == "Custom message"
        assert wrapped.correlation_id == "test-123"
        assert wrapped.cause == original_error
        

class TestLoggingConfiguration:
    """Test the centralized logging configuration."""
    
    def test_get_logger(self):
        """Test logger retrieval."""
        logger = get_logger("test_module")
        
        assert isinstance(logger, AccordoLogger)
        assert logger.name == "test_module"
        
    def test_logger_with_correlation_id(self):
        """Test logger with correlation ID."""
        logger = get_logger("test_module")
        correlation_id = str(uuid.uuid4())
        
        logger_with_id = logger.with_correlation_id(correlation_id)
        assert isinstance(logger_with_id, AccordoLogger)
        
    def test_logger_with_context(self):
        """Test logger with context."""
        logger = get_logger("test_module")
        context = {"operation": "test", "user_id": "123"}
        
        logger_with_context = logger.with_context(context)
        assert isinstance(logger_with_context, AccordoLogger)
        
    def test_set_correlation_id_global(self):
        """Test global correlation ID setting."""
        correlation_id = str(uuid.uuid4())
        set_correlation_id(correlation_id)
        
        # Create new logger and verify it uses the correlation ID
        logger = get_logger("test_correlation")
        # Note: Actual verification would require inspecting log output
        
    def test_configure_logging_with_file(self):
        """Test logging configuration with file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            configure_logging(
                log_level="DEBUG",
                log_dir=str(log_dir),
                enable_console=False
            )
            
            logger = get_logger("test_file_logging")
            logger.info("Test message")
            
            # Verify log file was created
            log_file = log_dir / "accordo.log"
            assert log_file.exists()


class TestErrorResponsePatterns:
    """Test error response formatting and patterns."""
    
    def test_error_response_format_creation(self):
        """Test ErrorResponseFormat instantiation."""
        response = ErrorResponseFormat(
            error_type="TestError",
            message="Test message",
            error_code="TEST_ERROR",
            severity=ErrorSeverity.HIGH,
            http_status=HTTPStatusCode.BAD_REQUEST
        )
        
        assert response.error_type == "TestError"
        assert response.message == "Test message" 
        assert response.error_code == "TEST_ERROR"
        assert response.severity == ErrorSeverity.HIGH
        assert response.http_status == HTTPStatusCode.BAD_REQUEST
        
    def test_error_response_from_accordo_error(self):
        """Test creating error response from AccordoError."""
        error = ValidationError("Invalid input").with_details(field="email")
        response = ErrorResponseFormat.from_accordo_error(error)
        
        assert response.error_type == "ValidationError"
        assert response.message == "Invalid input"
        assert response.error_code == "VALIDATION_ERROR"
        assert response.severity == ErrorSeverity.LOW
        assert response.http_status == HTTPStatusCode.BAD_REQUEST
        assert response.details["field"] == "email"
        
    def test_error_response_serialization(self):
        """Test error response serialization."""
        response = ErrorResponseFormat(
            error_type="TestError",
            message="Test message"
        )
        
        response_dict = response.to_dict()
        assert response_dict["success"] is False
        assert response_dict["error"]["type"] == "TestError"
        assert response_dict["error"]["message"] == "Test message"
        
        response_json = response.to_json()
        parsed = json.loads(response_json)
        assert parsed["success"] is False
        
    def test_create_error_response_from_accordo_error(self):
        """Test create_error_response with AccordoError."""
        error = ValidationError("Test validation error")
        response = create_error_response(error)
        
        assert response["success"] is False
        assert response["error"]["type"] == "ValidationError"
        assert response["error"]["message"] == "Test validation error"
        
    def test_create_error_response_from_exception(self):
        """Test create_error_response with generic Exception."""
        error = ValueError("Generic error")
        response = create_error_response(error)
        
        assert response["success"] is False
        assert "ValueError" in response["error"]["message"] or "AccordoError" in response["error"]["type"]
        
    def test_create_error_response_from_string(self):
        """Test create_error_response with string message."""
        response = create_error_response("Simple error message")
        
        assert response["success"] is False
        assert response["error"]["message"] == "Simple error message"
        
    def test_create_success_response(self):
        """Test create_success_response."""
        data = {"result": "success", "count": 5}
        response = create_success_response(
            data=data,
            message="Operation completed",
            correlation_id="test-123"
        )
        
        assert response["success"] is True
        assert response["message"] == "Operation completed"
        assert response["data"] == data
        assert response["correlation_id"] == "test-123"
        
    def test_validate_response_format_valid(self):
        """Test response format validation with valid response."""
        valid_response = {
            "success": True,
            "message": "Success",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        errors = validate_response_format(valid_response)
        assert errors == []
        
    def test_validate_response_format_invalid(self):
        """Test response format validation with invalid response."""
        invalid_response = {
            "success": False,
            # Missing required error field
        }
        
        errors = validate_response_format(invalid_response)
        assert len(errors) > 0
        assert any("error" in error for error in errors)


class TestMCPErrorMiddleware:
    """Test MCP-specific error handling middleware."""
    
    def test_mcp_error_handler_success(self):
        """Test MCP error handler with successful function."""
        @mcp_error_handler()
        def test_function():
            return "success result"
        
        result = test_function()
        assert result == "success result"
        
    def test_mcp_error_handler_accordo_error(self):
        """Test MCP error handler with AccordoError."""
        @mcp_error_handler()
        def test_function():
            raise ValidationError("Test validation error")
        
        result = test_function()
        # Should return JSON string for MCP compatibility
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert parsed["error"]["type"] == "ValidationError"
        
    def test_mcp_error_handler_generic_exception(self):
        """Test MCP error handler with generic exception."""
        @mcp_error_handler()
        def test_function():
            raise ValueError("Generic error")
        
        result = test_function()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["success"] is False
        
    def test_require_session_id_decorator_valid(self):
        """Test require_session_id decorator with valid session ID."""
        @require_session_id
        def test_function(session_id=None):
            return f"Session: {session_id}"
        
        result = test_function(session_id="test-session-123")
        assert "test-session-123" in result
        
    def test_require_session_id_decorator_invalid(self):
        """Test require_session_id decorator with invalid session ID."""
        @require_session_id
        def test_function(session_id=None):
            return f"Session: {session_id}"
        
        with pytest.raises(ValidationError) as exc_info:
            test_function(session_id="")
        
        assert "Session ID is required" in str(exc_info.value)
        
    def test_validate_json_parameter_valid(self):
        """Test JSON parameter validation with valid JSON."""
        json_data = '{"key": "value", "number": 123}'
        result = validate_json_parameter(json_data, "test_param")
        
        assert result == {"key": "value", "number": 123}
        
    def test_validate_json_parameter_invalid(self):
        """Test JSON parameter validation with invalid JSON."""
        invalid_json = '{"key": "value", invalid}'
        
        with pytest.raises(ValidationError) as exc_info:
            validate_json_parameter(invalid_json, "test_param")
        
        assert "invalid JSON" in str(exc_info.value)
        
    def test_validate_json_parameter_empty(self):
        """Test JSON parameter validation with empty string."""
        result = validate_json_parameter("", "test_param")
        assert result == {}
        
    def test_mcp_tool_protection_comprehensive(self):
        """Test comprehensive MCP tool protection."""
        @mcp_tool_protection(
            require_task_format=True,
            log_usage=True,
            custom_validation={
                "context": lambda x: validate_json_parameter(x, "context") and None
            }
        )
        def test_function(task_description=None, context="", session_id="test-123"):
            return "Protected function result"
        
        # Test successful call
        result = test_function(
            task_description="Test: description",
            context='{"key": "value"}',
            session_id="test-123"
        )
        assert "Protected function result" in str(result)
        
    def test_mcp_error_handler_class(self):
        """Test MCPErrorHandler class directly."""
        handler = MCPErrorHandler(
            include_traceback=True,
            log_errors=False,
            standardize_responses=True
        )
        
        @handler
        def test_function():
            return {"data": "test"}
        
        result = test_function()
        # Should be wrapped in standard response format
        assert isinstance(result, dict)
        assert result.get("success") is True


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components."""
    
    def test_full_error_flow(self):
        """Test complete error flow from exception to response."""
        # Create an error with full context
        correlation_id = str(uuid.uuid4())
        error = (ValidationError("Test validation failed")
                .with_details(field="email", value="invalid-email")
                .with_correlation_id(correlation_id))
        
        # Create error response
        response = create_error_response(error, include_traceback=True)
        
        # Validate response structure
        assert response["success"] is False
        assert response["error"]["correlation_id"] == correlation_id
        assert response["error"]["details"]["field"] == "email"
        
        # Validate format
        format_errors = validate_response_format(response)
        assert format_errors == []
        
    def test_mcp_tool_with_logging_and_error_handling(self):
        """Test MCP tool with full logging and error handling."""
        with patch('accordo_workflow_mcp.mcp_error_middleware.logger') as mock_logger:
            
            @mcp_tool_protection(log_usage=True)
            def test_mcp_tool(session_id="test-session"):
                # Simulate some work
                logger = get_logger("test_tool")
                logger.info("Processing request")
                return "Tool completed successfully"
            
            result = test_mcp_tool(session_id="test-session")
            
            # Verify logging was called
            assert mock_logger.info.called
            
            # Verify result format
            assert "Tool completed successfully" in str(result)
            
    def test_error_hierarchy_inheritance(self):
        """Test that error hierarchy properly inherits AccordoError behavior."""
        errors_to_test = [
            ValidationError("Validation failed"),
            SessionNotFoundError("Session not found"),
            ConfigurationError("Config invalid"),
            WorkflowError("Workflow failed"),
            CacheError("Cache failed"),
            ServiceError("Service failed"),
            NetworkError("Network failed")
        ]
        
        for error in errors_to_test:
            assert isinstance(error, AccordoError)
            assert error.message is not None
            assert error.error_code is not None
            assert error.correlation_id is not None
            
            # Test serialization
            error_dict = error.to_dict()
            assert "message" in error_dict
            assert "error_code" in error_dict
            
            # Test method chaining
            enhanced_error = error.with_details(test="value")
            assert enhanced_error.details["test"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 