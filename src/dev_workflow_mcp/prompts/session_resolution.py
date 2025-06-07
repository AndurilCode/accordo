"""Session resolution and context management functions.

This module handles session ID resolution and client context management for
workflow operations.
"""

from fastmcp import Context

from ..utils.session_id_utils import extract_session_id_from_context


def resolve_session_context(
    session_id: str, context: str, ctx: Context
) -> tuple[str | None, str]:
    """Resolve session from session_id with improved session-first approach.

    This function prioritizes explicit session_id over client-based lookup to support
    the new session-independent architecture where each chat operates independently.

    Args:
        session_id: Optional session ID parameter (preferred method)
        context: Context string that may contain session_id
        ctx: MCP Context object

    Returns:
        tuple: (resolved_session_id, client_id)

    Note:
        - client_id is still returned for cache operations and semantic search filtering
        - session_id takes absolute priority for workflow operations
        - No automatic client-based session conflicts are detected
    """
    client_id = "default"  # consistent fallback for cache operations

    # Extract client_id from MCP Context with defensive handling
    if ctx is not None:
        try:
            if hasattr(ctx, "client_id") and ctx.client_id:
                client_id = ctx.client_id
        except AttributeError:
            pass  # Context object exists but doesn't have expected attributes

    # Handle direct function calls where Field defaults may be FieldInfo objects
    if hasattr(session_id, "default"):  # FieldInfo object
        session_id = session_id.default if session_id.default else ""
    if hasattr(context, "default"):  # FieldInfo object
        context = context.default if context.default else ""

    # Ensure session_id and context are strings
    session_id = str(session_id) if session_id is not None else ""
    context = str(context) if context is not None else ""

    # Priority 1: Explicit session_id parameter (PREFERRED for session-independent operation)
    if session_id and session_id.strip():
        return session_id.strip(), client_id

    # Priority 2: session_id in context string (alternative method)
    extracted_session_id = extract_session_id_from_context(context)
    if extracted_session_id:
        return extracted_session_id, client_id

    # Priority 3: No explicit session - return None for new session creation
    # NOTE: This no longer triggers client-based conflict detection
    return None, client_id
