"""Session ID utilities for workflow session management."""

import uuid
from typing import Any


def generate_session_id() -> str:
    """Generate a unique session ID using UUID4.

    Returns:
        str: A unique session identifier
    """
    return str(uuid.uuid4())


def validate_session_id(session_id: str) -> bool:
    """Validate that a session ID is a valid UUID format.

    Args:
        session_id: The session ID to validate

    Returns:
        bool: True if valid UUID format, False otherwise
    """
    if not isinstance(session_id, str):
        return False

    try:
        uuid.UUID(session_id)
        return True
    except (ValueError, TypeError):
        return False


def add_session_id_to_response(
    response: Any, session_id: str | None = None
) -> dict[str, Any]:
    """Add session_id to any response, ensuring all MCP tool responses include session info.

    Args:
        response: The original response (dict, str, or other)
        session_id: Optional session ID to include

    Returns:
        Dict containing the response with session_id metadata
    """
    if session_id is None:
        # No session context
        if isinstance(response, dict):
            return response
        else:
            return {"content": response}

    if isinstance(response, dict):
        # Add session_id to existing dict response
        result = response.copy()
        result["session_id"] = session_id
        return result
    else:
        # Wrap non-dict responses
        return {"content": response, "session_id": session_id}


def extract_session_id_from_context(context: str | None) -> str | None:
    """Extract session_id from context string if present.

    Args:
        context: Context string that may contain session_id

    Returns:
        str | None: Extracted session_id or None if not found
    """
    if not context or not isinstance(context, str):
        return None

    # Look for session_id in various formats
    # Format: session_id:uuid
    if "session_id:" in context:
        try:
            parts = context.split("session_id:")
            if len(parts) > 1:
                candidate = parts[1].split()[0].strip()
                if validate_session_id(candidate):
                    return candidate
        except (IndexError, AttributeError):
            pass

    return None


def sync_session_after_modification(session_id: str) -> bool:
    """Convenience function to sync session after direct modifications.

    This function provides a way to sync sessions from modules that don't
    directly import session_manager to avoid circular imports.

    Args:
        session_id: The session identifier

    Returns:
        bool: True if sync succeeded or was skipped, False on error
    """
    try:
        # Import here to avoid circular imports
        from .session_manager import sync_session

        return sync_session(session_id)
    except ImportError:
        return False
