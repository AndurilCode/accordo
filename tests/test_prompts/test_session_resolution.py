"""Tests for session_resolution.py functions."""

import pytest
from unittest.mock import Mock, patch

from src.dev_workflow_mcp.prompts.session_resolution import resolve_session_context
from fastmcp import Context


class TestResolveSessionContext:
    """Test resolve_session_context function."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context object."""
        context = Mock(spec=Context)
        context.client_id = "test-client-123"
        return context

    def test_resolve_session_context_with_explicit_session_id(self, mock_context):
        """Test resolution with explicit session_id parameter."""
        session_id, client_id = resolve_session_context(
            "session-123", "", mock_context
        )
        
        assert session_id == "session-123"
        assert client_id == "test-client-123"

    def test_resolve_session_context_with_session_id_whitespace(self, mock_context):
        """Test resolution with session_id that has whitespace."""
        session_id, client_id = resolve_session_context(
            "  session-456  ", "", mock_context
        )
        
        assert session_id == "session-456"
        assert client_id == "test-client-123"

    def test_resolve_session_context_with_empty_session_id_and_context_extraction(self, mock_context):
        """Test resolution when session_id is empty but context contains session_id."""
        with patch('src.dev_workflow_mcp.prompts.session_resolution.extract_session_id_from_context') as mock_extract:
            mock_extract.return_value = "extracted-session-789"
            
            session_id, client_id = resolve_session_context(
                "", "some context with session info", mock_context
            )
            
            assert session_id == "extracted-session-789"
            assert client_id == "test-client-123"
            mock_extract.assert_called_once_with("some context with session info")

    def test_resolve_session_context_with_none_session_id_and_context_extraction(self, mock_context):
        """Test resolution when session_id is None but context contains session_id."""
        with patch('src.dev_workflow_mcp.prompts.session_resolution.extract_session_id_from_context') as mock_extract:
            mock_extract.return_value = "extracted-session-abc"
            
            session_id, client_id = resolve_session_context(
                None, "context with session", mock_context
            )
            
            assert session_id == "extracted-session-abc"
            assert client_id == "test-client-123"
            mock_extract.assert_called_once_with("context with session")

    def test_resolve_session_context_no_session_found(self, mock_context):
        """Test resolution when no session is found anywhere."""
        with patch('src.dev_workflow_mcp.prompts.session_resolution.extract_session_id_from_context') as mock_extract:
            mock_extract.return_value = None
            
            session_id, client_id = resolve_session_context(
                "", "", mock_context
            )
            
            assert session_id is None
            assert client_id == "test-client-123"

    def test_resolve_session_context_with_none_context_object(self):
        """Test resolution when context object is None."""
        session_id, client_id = resolve_session_context(
            "session-999", "", None
        )
        
        assert session_id == "session-999"
        assert client_id == "default"

    def test_resolve_session_context_with_context_missing_client_id(self):
        """Test resolution when context object exists but has no client_id."""
        # Create a mock that doesn't have client_id attribute
        mock_context = Mock()
        # Make hasattr return False for client_id
        mock_context.__dict__.clear()  # Remove all attributes
        
        session_id, client_id = resolve_session_context(
            "session-777", "", mock_context
        )
        
        assert session_id == "session-777"
        assert client_id == "default"

    def test_resolve_session_context_with_context_empty_client_id(self):
        """Test resolution when context object has empty client_id."""
        mock_context = Mock(spec=Context)
        mock_context.client_id = ""
        
        session_id, client_id = resolve_session_context(
            "session-555", "", mock_context
        )
        
        assert session_id == "session-555"
        assert client_id == "default"

    def test_resolve_session_context_with_context_none_client_id(self):
        """Test resolution when context object has None client_id."""
        mock_context = Mock(spec=Context)
        mock_context.client_id = None
        
        session_id, client_id = resolve_session_context(
            "session-333", "", mock_context
        )
        
        assert session_id == "session-333"
        assert client_id == "default"

    def test_resolve_session_context_with_attribute_error_scenario(self):
        """Test resolution when context object has issues accessing client_id."""
        # Since the actual implementation uses hasattr first, we test the fallback behavior
        # by creating a context that will fall back to default
        mock_context = Mock()
        mock_context.__dict__.clear()  # No attributes, so hasattr returns False
        
        session_id, client_id = resolve_session_context(
            "session-111", "", mock_context
        )
        
        assert session_id == "session-111"
        assert client_id == "default"

    def test_resolve_session_context_with_field_info_objects(self, mock_context):
        """Test resolution when session_id and context are FieldInfo objects."""
        # Mock FieldInfo-like objects
        mock_session_id = Mock()
        mock_session_id.default = "field-session-123"
        
        mock_context_param = Mock()
        mock_context_param.default = "field context"
        
        with patch('src.dev_workflow_mcp.prompts.session_resolution.extract_session_id_from_context') as mock_extract:
            mock_extract.return_value = None
            
            session_id, client_id = resolve_session_context(
                mock_session_id, mock_context_param, mock_context
            )
            
            assert session_id == "field-session-123"
            assert client_id == "test-client-123"

    def test_resolve_session_context_with_field_info_empty_defaults(self, mock_context):
        """Test resolution when FieldInfo objects have empty defaults."""
        # Mock FieldInfo-like objects with empty defaults
        mock_session_id = Mock()
        mock_session_id.default = ""
        
        mock_context_param = Mock()
        mock_context_param.default = None
        
        with patch('src.dev_workflow_mcp.prompts.session_resolution.extract_session_id_from_context') as mock_extract:
            mock_extract.return_value = "extracted-from-empty"
            
            session_id, client_id = resolve_session_context(
                mock_session_id, mock_context_param, mock_context
            )
            
            assert session_id == "extracted-from-empty"
            assert client_id == "test-client-123"
            mock_extract.assert_called_once_with("")

    def test_resolve_session_context_priority_explicit_over_context(self, mock_context):
        """Test that explicit session_id takes priority over context extraction."""
        with patch('src.dev_workflow_mcp.prompts.session_resolution.extract_session_id_from_context') as mock_extract:
            # Even if context would extract a session, explicit session_id wins
            mock_extract.return_value = "context-session"
            
            session_id, client_id = resolve_session_context(
                "explicit-session", "context with session", mock_context
            )
            
            assert session_id == "explicit-session"
            assert client_id == "test-client-123"
            # extract function should not be called when explicit session_id is provided
            mock_extract.assert_not_called()

    def test_resolve_session_context_string_conversion(self, mock_context):
        """Test that non-string inputs are converted to strings."""
        # Test with integer inputs
        session_id, client_id = resolve_session_context(
            123, 456, mock_context
        )
        
        assert session_id == "123"
        assert client_id == "test-client-123"

    def test_resolve_session_context_none_inputs_converted_to_empty_string(self, mock_context):
        """Test that None inputs are converted to empty strings."""
        with patch('src.dev_workflow_mcp.prompts.session_resolution.extract_session_id_from_context') as mock_extract:
            mock_extract.return_value = None
            
            session_id, client_id = resolve_session_context(
                None, None, mock_context
            )
            
            assert session_id is None
            assert client_id == "test-client-123"
            mock_extract.assert_called_once_with("")

    def test_resolve_session_context_complex_integration_scenario(self):
        """Test a complex integration scenario with multiple edge cases."""
        # Context without client_id, FieldInfo objects, and context extraction
        mock_context = Mock()
        mock_context.__dict__.clear()  # No client_id attribute
        
        mock_session_id = Mock()
        mock_session_id.default = ""  # Empty default
        
        mock_context_param = Mock()
        mock_context_param.default = "complex context string"
        
        with patch('src.dev_workflow_mcp.prompts.session_resolution.extract_session_id_from_context') as mock_extract:
            mock_extract.return_value = "complex-extracted-session"
            
            session_id, client_id = resolve_session_context(
                mock_session_id, mock_context_param, mock_context
            )
            
            assert session_id == "complex-extracted-session"
            assert client_id == "default"  # Falls back due to missing client_id
            mock_extract.assert_called_once_with("complex context string")

    def test_resolve_session_context_all_edge_cases_combined(self):
        """Test combining multiple edge cases in one scenario."""
        # No context, FieldInfo with None defaults, no extraction
        mock_session_id = Mock()
        mock_session_id.default = None
        
        mock_context_param = Mock()
        mock_context_param.default = ""
        
        with patch('src.dev_workflow_mcp.prompts.session_resolution.extract_session_id_from_context') as mock_extract:
            mock_extract.return_value = None
            
            session_id, client_id = resolve_session_context(
                mock_session_id, mock_context_param, None
            )
            
            assert session_id is None
            assert client_id == "default"
            mock_extract.assert_called_once_with("") 