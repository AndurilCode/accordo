"""Evidence extraction functions for workflow operations.

This module provides automatic evidence extraction from session activity to support
workflow completion tracking and criteria validation.
"""


def extract_automatic_evidence_from_session(
    session,
    node_name: str,
    acceptance_criteria: dict[str, str],
) -> dict[str, str]:
    """Automatically extract evidence of completed work from session activity.

    This function analyzes recent session logs, execution context, and other
    session data to intelligently extract evidence of actual agent work
    rather than falling back to generic YAML descriptions.

    Args:
        session: Current workflow session state
        node_name: Name of the node being completed
        acceptance_criteria: Dict of criterion -> description from YAML

    Returns:
        Dict of criterion -> evidence extracted from session activity

    Note:
        This provides automatic evidence capture for backward compatibility
        when agents use simple "choose: node" format instead of JSON context.
    """
    evidence = {}

    # Get recent log entries (last 10-15 entries to capture current phase work)
    recent_logs = session.log[-15:] if hasattr(session, "log") and session.log else []

    # Extract evidence based on common patterns in session logs and context
    for criterion, description in acceptance_criteria.items():
        extracted_evidence = _extract_criterion_evidence(
            criterion, description, recent_logs, session, node_name
        )
        if extracted_evidence:
            evidence[criterion] = extracted_evidence

    return evidence


def _extract_criterion_evidence(
    criterion: str,
    description: str,
    recent_logs: list[str],
    session,
    node_name: str,
) -> str | None:
    """Extract evidence for a specific criterion from session activity.

    Args:
        criterion: Name of the acceptance criterion
        description: YAML description of the criterion
        recent_logs: Recent log entries from the session
        session: Current session state
        node_name: Current node name

    Returns:
        Extracted evidence string or None if no meaningful evidence found
    """
    # Pattern 1: Look for specific criterion mentions in logs
    for log_entry in reversed(recent_logs):  # Start with most recent
        log_lower = log_entry.lower()
        criterion_lower = criterion.lower()

        # Direct criterion mentions
        if criterion_lower in log_lower or any(
            keyword in log_lower
            for keyword in _get_criterion_keywords(criterion, description)
        ):
            # Extract meaningful context around the criterion mention
            evidence = _extract_evidence_from_log_entry(
                log_entry, criterion, description
            )
            if evidence:
                return evidence

    # Pattern 2: Extract from execution context if available
    if hasattr(session, "execution_context") and session.execution_context:
        context_evidence = _extract_evidence_from_execution_context(
            session.execution_context, criterion, description
        )
        if context_evidence:
            return context_evidence

    # Pattern 3: Look for activity patterns that suggest criterion completion
    activity_evidence = _extract_evidence_from_activity_patterns(
        recent_logs, criterion, description, node_name
    )
    if activity_evidence:
        return activity_evidence

    # Pattern 4: Check for tool usage patterns that indicate work completion
    tool_evidence = _extract_evidence_from_tool_patterns(
        recent_logs, criterion, description
    )
    if tool_evidence:
        return tool_evidence

    return None


def _get_criterion_keywords(criterion: str, description: str) -> list[str]:
    """Get relevant keywords for a criterion to help with evidence extraction.

    Args:
        criterion: Criterion name
        description: Criterion description

    Returns:
        List of keywords to look for in logs
    """
    # Extract keywords from criterion name and description
    keywords = []

    # Add criterion name variations
    keywords.extend(
        [
            criterion.lower(),
            criterion.replace("_", " ").lower(),
            criterion.replace("_", "").lower(),
        ]
    )

    # Extract key terms from description
    description_words = description.lower().split()
    important_words = [
        word
        for word in description_words
        if len(word) > 3
        and word
        not in {
            "must",
            "the",
            "and",
            "or",
            "with",
            "for",
            "this",
            "that",
            "from",
            "into",
            "have",
            "been",
        }
    ]
    keywords.extend(important_words[:5])  # Top 5 important words

    return keywords


def _extract_evidence_from_log_entry(
    log_entry: str, criterion: str, description: str
) -> str | None:
    """Extract evidence from a specific log entry.

    Args:
        log_entry: Log entry text
        criterion: Criterion name
        description: Criterion description

    Returns:
        Extracted evidence or None
    """
    # Clean up timestamp and formatting from log entry
    clean_entry = log_entry
    if "] " in clean_entry:
        clean_entry = clean_entry.split("] ", 1)[-1]

    # Filter out non-meaningful log entries
    if any(
        filter_term in clean_entry.lower()
        for filter_term in [
            "transitioned from",
            "transitioned to",
            "workflow initialized",
            "completed node:",
            "criterion satisfied:",
        ]
    ):
        return None

    # Extract meaningful activity descriptions
    if len(clean_entry.strip()) > 20:  # Ensure substantial content
        return f"Session activity: {clean_entry.strip()}"

    return None


def _extract_evidence_from_execution_context(
    execution_context: dict, criterion: str, description: str
) -> str | None:
    """Extract evidence from session execution context.

    Args:
        execution_context: Session execution context dict
        criterion: Criterion name
        description: Criterion description

    Returns:
        Extracted evidence or None
    """
    if not execution_context:
        return None

    # Look for relevant context entries
    context_evidence = []
    for key, value in execution_context.items():
        key_lower = key.lower()
        criterion_lower = criterion.lower()

        if criterion_lower in key_lower or any(
            keyword in key_lower
            for keyword in _get_criterion_keywords(criterion, description)
        ):
            context_evidence.append(f"{key}: {value}")

    if context_evidence:
        return f"Execution context: {'; '.join(context_evidence)}"

    return None


def _extract_evidence_from_activity_patterns(
    recent_logs: list[str], criterion: str, description: str, node_name: str
) -> str | None:
    """Extract evidence based on activity patterns in logs.

    Args:
        recent_logs: Recent log entries
        criterion: Criterion name
        description: Criterion description
        node_name: Current node name

    Returns:
        Extracted evidence or None
    """
    # Count meaningful activities (non-system logs)
    meaningful_activities = []
    for log_entry in recent_logs:
        clean_entry = log_entry
        if "] " in clean_entry:
            clean_entry = clean_entry.split("] ", 1)[-1]

        # Skip system/transition logs
        if (
            not any(
                system_term in clean_entry.lower()
                for system_term in [
                    "transitioned",
                    "initialized",
                    "completed node",
                    "criterion satisfied",
                ]
            )
            and len(clean_entry.strip()) > 15
        ):
            meaningful_activities.append(clean_entry.strip())

    if meaningful_activities:
        activity_count = len(meaningful_activities)
        recent_activity = (
            meaningful_activities[-1] if meaningful_activities else "various activities"
        )
        return f"Completed {activity_count} activities in {node_name} phase, including: {recent_activity}"

    return None


def _extract_evidence_from_tool_patterns(
    recent_logs: list[str], criterion: str, description: str
) -> str | None:
    """Extract evidence based on tool usage patterns.

    Args:
        recent_logs: Recent log entries
        criterion: Criterion name
        description: Criterion description

    Returns:
        Extracted evidence or None
    """
    # Look for patterns indicating specific types of work
    tool_patterns = {
        "analysis": ["analyzed", "examined", "reviewed", "investigated"],
        "implementation": ["implemented", "created", "built", "developed"],
        "testing": ["tested", "verified", "validated", "checked"],
        "documentation": ["documented", "recorded", "noted", "captured"],
    }

    detected_activities = []
    for log_entry in recent_logs:
        log_lower = log_entry.lower()
        for activity_type, patterns in tool_patterns.items():
            if any(pattern in log_lower for pattern in patterns):
                detected_activities.append(activity_type)
                break

    if detected_activities:
        unique_activities = list(
            dict.fromkeys(detected_activities)
        )  # Remove duplicates while preserving order
        return f"Performed {', '.join(unique_activities)} work as evidenced by session activity"

    return None 