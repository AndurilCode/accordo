"""Pure schema-driven workflow prompts.

This module provides workflow guidance based purely on YAML workflow schemas.
No hardcoded logic - all behavior determined by workflow definitions.
"""

import json
from datetime import UTC, datetime
from typing import Any

import yaml
from fastmcp import Context, FastMCP
from pydantic import Field

from ..models.yaml_workflow import WorkflowDefinition, WorkflowNode
from ..utils.placeholder_processor import replace_placeholders
from ..utils.schema_analyzer import (
    analyze_node_from_schema,
    extract_choice_from_context,
    get_available_transitions,
    get_workflow_summary,
    validate_transition,
)
from ..utils.session_id_utils import (
    add_session_id_to_response,
    extract_session_id_from_context,
)
from ..utils.session_manager import (
    add_log_to_session,
    create_dynamic_session,
    export_session_to_markdown,
    get_dynamic_session_workflow_def,
    get_or_create_dynamic_session,
    get_session,
    get_session_type,
    store_workflow_definition_in_cache,
    update_dynamic_session_node,
    update_dynamic_session_status,
)
from ..utils.workflow_engine import WorkflowEngine
from ..utils.yaml_loader import WorkflowLoader
from .discovery_prompts import get_cached_workflow

# =============================================================================
# SESSION RESOLUTION FUNCTIONS
# =============================================================================


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


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_task_description(description: str | None) -> str:
    """Validate task description format.

    Args:
        description: Task description to validate

    Returns:
        str: Trimmed and validated description

    Raises:
        ValueError: If description doesn't follow required format
    """
    if description is None:
        raise ValueError(
            "Task description must be a non-empty string. Task descriptions must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    if not isinstance(description, str):
        raise ValueError(
            "Task description must be a string. Task descriptions must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Trim whitespace
    description = description.strip()

    if not description:
        raise ValueError(
            "Task description must be a non-empty string. Task descriptions must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Check for colon
    if ":" not in description:
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Split on first colon
    parts = description.split(":", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    action_verb = parts[0].strip()
    task_details = parts[1]

    # Check if action verb is empty
    if not action_verb:
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Check if action verb starts with uppercase letter
    if not action_verb[0].isupper():
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Check if action verb is all alphabetic (no numbers or special chars)
    if not action_verb.isalpha():
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Check if there's a space after colon
    if not task_details.startswith(" "):
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Check if description part is not empty after trimming
    task_details_trimmed = task_details.strip()
    if not task_details_trimmed:
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    return description


# =============================================================================
# YAML PARSING FUNCTIONS
# =============================================================================


def parse_and_validate_yaml_context(
    context: str,
) -> tuple[str | None, str | None, str | None]:
    """Parse and validate YAML context from agent input.

    Args:
        context: Context string containing workflow name and YAML content

    Returns:
        tuple: (workflow_name, yaml_content, error_message)

    Expected formats:
    1. Standard format: "workflow: Name\\nyaml: <yaml_content>"
    2. Multiline format with proper YAML indentation
    3. Raw YAML with workflow name extracted from content
    """
    if not context or not isinstance(context, str):
        return None, None, "Context must be a non-empty string"

    context = context.strip()
    workflow_name = None
    yaml_content = None

    try:
        # Method 1: Parse standard format with "workflow:" and "yaml:" markers
        if "workflow:" in context and "yaml:" in context:
            result = _parse_standard_format(context)
            if result and len(result) == 2:
                workflow_name, yaml_content = result
                if workflow_name and yaml_content:
                    # Validate and reformat YAML
                    formatted_yaml = _validate_and_reformat_yaml(yaml_content)
                    if formatted_yaml:
                        return workflow_name, formatted_yaml, None
                    else:
                        return None, None, "Invalid YAML content - failed validation"

            # Handle case where YAML content is empty after "yaml:"
            if "yaml:" in context:
                workflow_name = _extract_workflow_name_only(context)
                yaml_part = context.split("yaml:", 1)[1].strip()
                if not yaml_part:  # Empty YAML content
                    return (
                        workflow_name,
                        None,
                        "Workflow name provided but YAML content is missing",
                    )

        # Method 2: Try parsing as pure YAML (extract name from content)
        elif _looks_like_yaml(context):
            result = _parse_pure_yaml(context)
            if result and len(result) == 2:
                workflow_name, yaml_content = result
                if workflow_name and yaml_content:
                    return workflow_name, yaml_content, None
            return None, None, "Could not extract workflow name from YAML content"

        # Method 3: Check if it's just a workflow name (no YAML content)
        elif "workflow:" in context and "yaml:" not in context:
            workflow_name = _extract_workflow_name_only(context)
            return (
                workflow_name,
                None,
                "Workflow name provided but YAML content is missing",
            )

        else:
            return (
                None,
                None,
                "Unrecognized context format - expected 'workflow: Name\\nyaml: <content>' or pure YAML",
            )

    except Exception as e:
        return None, None, f"Error parsing context: {str(e)}"


def _parse_standard_format(context: str) -> tuple[str | None, str | None]:
    """Parse standard format: workflow: Name\\nyaml: <content>"""
    lines = context.split("\n")
    workflow_name = None
    yaml_content = []
    yaml_started = False

    for line in lines:
        line_stripped = line.strip()

        # Extract workflow name
        if line_stripped.startswith("workflow:") and not workflow_name:
            workflow_name = line_stripped.split("workflow:", 1)[1].strip()

        # Start collecting YAML content
        elif line_stripped.startswith("yaml:"):
            yaml_started = True
            # Check if there's content on the same line after "yaml:"
            yaml_part = line_stripped.split("yaml:", 1)[1].strip()
            if yaml_part:
                yaml_content.append(yaml_part)

        # Continue collecting YAML lines
        elif yaml_started:
            yaml_content.append(line)  # Keep original indentation for YAML

    if workflow_name and yaml_content:
        return workflow_name, "\n".join(yaml_content)

    return None, None


def _parse_pure_yaml(context: str) -> tuple[str | None, str | None]:
    """Parse pure YAML content and extract workflow name."""
    try:
        # Try to parse as YAML to validate structure
        yaml_data = yaml.safe_load(context)

        if isinstance(yaml_data, dict) and "name" in yaml_data:
            workflow_name = yaml_data["name"]
            return workflow_name, context
        else:
            return None, None

    except yaml.YAMLError:
        return None, None


def _extract_workflow_name_only(context: str) -> str | None:
    """Extract workflow name when only name is provided (no YAML)."""
    for line in context.split("\n"):
        if line.strip().startswith("workflow:"):
            return line.split("workflow:", 1)[1].strip()
    return None


def _looks_like_yaml(content: str) -> bool:
    """Check if content looks like YAML format."""
    # Look for common YAML indicators
    yaml_indicators = [
        "name:",
        "description:",
        "workflow:",
        "inputs:",
        "tree:",
        "goal:",
        "acceptance_criteria:",
    ]

    return any(indicator in content for indicator in yaml_indicators)


def _validate_and_reformat_yaml(yaml_content: str) -> str | None:
    """Validate and reformat YAML content.

    Args:
        yaml_content: Raw YAML content string

    Returns:
        Formatted YAML string or None if invalid
    """
    try:
        # Parse YAML to validate structure
        yaml_data = yaml.safe_load(yaml_content)

        if not isinstance(yaml_data, dict):
            return None

        # Check for required top-level fields
        required_fields = ["name", "workflow"]
        missing_fields = [field for field in required_fields if field not in yaml_data]

        if missing_fields:
            return None

        # Validate workflow structure
        if not isinstance(yaml_data.get("workflow"), dict):
            return None

        workflow_section = yaml_data["workflow"]
        if "tree" not in workflow_section:
            return None

        # Reformat with proper indentation and structure
        reformatted = yaml.dump(
            yaml_data,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=120,
            allow_unicode=True,
        )

        return reformatted

    except yaml.YAMLError:
        return None
    except Exception:
        return None


# =============================================================================
# CONTEXT PARSING FUNCTIONS
# =============================================================================


def _parse_criteria_evidence_context(
    context: str,
) -> tuple[str | None, dict[str, str] | None, bool]:
    """Parse context to extract choice, criteria evidence, and user approval.

    Supports both legacy string format and new JSON dict format.

    Args:
        context: Context string from user input

    Returns:
        Tuple of (choice, criteria_evidence, user_approval) where:
        - choice: The chosen next node/workflow
        - criteria_evidence: Dict of criterion -> evidence details
        - user_approval: Whether user has provided explicit approval

    Examples:
        Legacy format: "choose: blueprint"
        New format: '{"choose": "blueprint", "criteria_evidence": {"analysis_complete": "Found the issue"}, "user_approval": true}'
    """
    if not context or not isinstance(context, str):
        return None, None, False

    context = context.strip()

    # Try to parse as JSON first (new format)
    try:
        if context.startswith("{") and context.endswith("}"):
            context_dict = json.loads(context)

            if isinstance(context_dict, dict):
                choice = context_dict.get("choose")
                criteria_evidence = context_dict.get("criteria_evidence", {})
                user_approval = context_dict.get("user_approval", False)

                # Validate criteria_evidence is a dict
                if not isinstance(criteria_evidence, dict):
                    criteria_evidence = {}

                # Validate user_approval is a boolean
                if not isinstance(user_approval, bool):
                    user_approval = False

                return choice, criteria_evidence, user_approval
    except (json.JSONDecodeError, ValueError):
        # If JSON parsing fails, fall back to legacy format
        pass

    # Legacy string format parsing
    choice = extract_choice_from_context(context)
    return choice, None, False


# =============================================================================
# AUTOMATIC EVIDENCE EXTRACTION FUNCTIONS
# =============================================================================


def _extract_automatic_evidence_from_session(
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


# =============================================================================
# FORMATTING FUNCTIONS
# =============================================================================


def _format_yaml_error_guidance(
    error_msg: str, workflow_name: str | None = None
) -> str:
    """Format helpful error message with YAML format guidance."""
    base_msg = f"❌ **YAML Format Error:** {error_msg}\n\n"

    guidance = """**🔧 EXPECTED FORMAT:**

**Option 1 - Standard Format:**
```
workflow_guidance(
    action="start",
    context="workflow: Workflow Name\\nyaml: name: Workflow Name\\ndescription: Description\\nworkflow:\\n  goal: Goal\\n  root: start\\n  tree:\\n    start:\\n      goal: Goal text\\n      next_allowed_nodes: [next]"
)
```

**Option 2 - Multiline YAML:**
```
workflow_guidance(
    action="start", 
    context="workflow: Workflow Name
yaml: name: Workflow Name
description: Description
workflow:
  goal: Goal
  root: start
  tree:
    start:
      goal: Goal text
      next_allowed_nodes: [next]"
)
```

**🚨 AGENT INSTRUCTIONS:**
1. Use `read_file` to get the YAML content from `.accordo/workflows/`
2. Copy the ENTIRE YAML content exactly as it appears in the file
3. Use the format above with proper workflow name and YAML content

**Required YAML Structure:**
- `name`: Workflow display name
- `description`: Brief description
- `workflow.goal`: Main objective
- `workflow.root`: Starting node name
- `workflow.tree`: Node definitions with goals and transitions"""

    if workflow_name:
        guidance += f"\n\n**Detected Workflow Name:** {workflow_name}"
        guidance += "\n**Action Required:** Please provide the complete YAML content for this workflow."

    return base_msg + guidance


def format_enhanced_node_status(
    node: WorkflowNode, workflow: WorkflowDefinition, session
) -> str:
    """Format current node status with enhanced authoritative guidance.

    Args:
        node: Current workflow node
        workflow: The workflow definition
        session: Current workflow session

    Returns:
        Enhanced formatted status string with authoritative guidance
    """
    analysis = analyze_node_from_schema(node, workflow)
    transitions = get_available_transitions(node, workflow)

    # Apply placeholder replacement to the goal and acceptance criteria
    session_inputs = getattr(session, "inputs", {}) or {}

    # Process the goal with placeholder replacement
    processed_goal = replace_placeholders(analysis["goal"], session_inputs)
    analysis["goal"] = processed_goal

    # Process acceptance criteria with placeholder replacement
    if analysis["acceptance_criteria"]:
        processed_criteria = {}
        for key, value in analysis["acceptance_criteria"].items():
            processed_criteria[key] = replace_placeholders(value, session_inputs)
        analysis["acceptance_criteria"] = processed_criteria

    # Process transition goals with placeholder replacement
    processed_transitions = []
    for transition in transitions:
        processed_transition = transition.copy()
        processed_transition["goal"] = replace_placeholders(
            transition["goal"], session_inputs
        )
        processed_transitions.append(processed_transition)
    transitions = processed_transitions

    # Format acceptance criteria with enhanced detail
    criteria_text = ""
    if analysis["acceptance_criteria"]:
        criteria_items = []
        for key, value in analysis["acceptance_criteria"].items():
            criteria_items.append(f"   ✅ **{key}**: {value}")
        criteria_text = "\n".join(criteria_items)
    else:
        criteria_text = "   • No specific criteria defined"

    # Format next options with approval enforcement checking
    options_text = ""
    if transitions:
        # Check if any target nodes require approval
        approval_required_transitions = [
            t for t in transitions if t.get("needs_approval", False)
        ]

        if approval_required_transitions:
            # At least one target node requires approval - show prominent enforcement message
            options_text = "🚨 **APPROVAL REQUIRED FOR NEXT TRANSITIONS** 🚨\n\n"
            options_text += "One or more available next steps require explicit user approval before proceeding.\n\n"

        options_text += "**🎯 Available Next Steps:**\n"
        for transition in transitions:
            if transition.get("needs_approval", False):
                # Mark approval-required transitions clearly
                options_text += f"   • **{transition['name']}** ⚠️ **(REQUIRES APPROVAL)**: {transition['goal']}\n"
            else:
                options_text += f"   • **{transition['name']}**: {transition['goal']}\n"

        if approval_required_transitions:
            # Special approval guidance for nodes that require approval
            options_text += "\n⚠️ **MANDATORY APPROVAL PROCESS:**\n"
            options_text += "To proceed to nodes marked **(REQUIRES APPROVAL)**, you must provide explicit approval:\n"
            options_text += '📋 **Required Format:** Include "user_approval": true in your context\n'
            options_text += "🚨 **CRITICAL:** ALWAYS provide both approval AND criteria evidence when transitioning:\n"

            if len(approval_required_transitions) == 1:
                # Single approval-required option - provide specific example
                example_node = approval_required_transitions[0]["name"]
                options_text += f'**Example:** workflow_guidance(action="next", context=\'{{"choose": "{example_node}", "user_approval": true, "criteria_evidence": {{"criterion1": "detailed evidence"}}}}\')\n'
            else:
                # Multiple approval-required options - provide generic example
                options_text += '**Example:** workflow_guidance(action="next", context=\'{"choose": "node_name", "user_approval": true, "criteria_evidence": {"criterion1": "detailed evidence"}}\')\n'

            # Add guidance for non-approval transitions if any exist
            non_approval_transitions = [
                t for t in transitions if not t.get("needs_approval", False)
            ]
            if non_approval_transitions:
                options_text += "\n📋 **For non-approval transitions:** Standard format without user_approval:\n"
                example_node = non_approval_transitions[0]["name"]
                options_text += f'**Example:** workflow_guidance(action="next", context=\'{{"choose": "{example_node}", "criteria_evidence": {{"criterion1": "detailed evidence"}}}}\')'
        else:
            # Standard guidance without approval requirement
            options_text += '\n📋 **To Proceed:** Call workflow_guidance with context="choose: <option_name>"\n'
            options_text += "🚨 **CRITICAL:** ALWAYS provide criteria evidence when transitioning:\n"

            if len(transitions) == 1:
                # Single option - provide specific example
                example_node = transitions[0]["name"]
                options_text += f'**Example:** workflow_guidance(action="next", context=\'{{"choose": "{example_node}", "criteria_evidence": {{"criterion1": "detailed evidence"}}}}\')'
            else:
                # Multiple options - provide generic example
                options_text += '**Example:** workflow_guidance(action="next", context=\'{"choose": "node_name", "criteria_evidence": {"criterion1": "detailed evidence"}}\')'
    else:
        options_text = "**🏁 Status:** This is a terminal node (workflow complete)"

    # Get current session state for display
    session_state = export_session_to_markdown(session.session_id)

    return f"""{analysis["goal"]}

**📋 ACCEPTANCE CRITERIA:**
{criteria_text}

{options_text}

**📊 CURRENT WORKFLOW STATE:**
```markdown
{session_state}
```

**🚨 REMEMBER:** Follow the mandatory execution steps exactly as specified. Each phase has critical requirements that must be completed before proceeding."""


# =============================================================================
# WORKFLOW LOGIC FUNCTIONS
# =============================================================================


def _handle_dynamic_workflow(
    session,
    workflow_def,
    action: str,
    context: str,
    engine: WorkflowEngine,
    loader: WorkflowLoader,
) -> str:
    """Handle dynamic workflow execution based purely on schema."""
    try:
        current_node = workflow_def.workflow.tree.get(session.current_node)

        if not current_node:
            return f"❌ **Invalid workflow state:** Node '{session.current_node}' not found in workflow."

        # Handle choice selection with enhanced context parsing
        if (
            context
            and isinstance(context, str)
            and ("choose:" in context.lower() or context.strip().startswith("{"))
        ):
            choice, criteria_evidence, user_approval = _parse_criteria_evidence_context(
                context
            )

            if choice and validate_transition(current_node, choice, workflow_def):
                # Valid transition - use workflow engine for proper approval handling
                if choice in (current_node.next_allowed_nodes or []):
                    # Generate node completion outputs before transitioning
                    # This ensures that the current node's work is properly documented
                    completion_outputs = _generate_node_completion_outputs(
                        session.current_node, current_node, session, criteria_evidence
                    )

                    # Use workflow engine for transition with approval validation
                    success = engine.execute_transition(
                        session,
                        workflow_def,
                        choice,
                        outputs=completion_outputs,
                        user_approval=user_approval,
                    )

                    if success:
                        # Sync session to filesystem after successful transition
                        from ..utils.session_id_utils import (
                            sync_session_after_modification,
                        )

                        sync_session_after_modification(session.session_id)

                        new_node = workflow_def.workflow.tree[choice]
                        status = format_enhanced_node_status(
                            new_node, workflow_def, session
                        )

                        return f"""✅ **Transitioned to:** {choice.upper()}

{status}"""
                    else:
                        # Transition failed (likely due to missing approval)
                        return f"❌ **Transition Failed:** Unable to transition to '{choice}'. Current node requires explicit user approval before transition. Provide 'user_approval': true in your context to proceed, ONLY WHEN THE USER HAS PROVIDED EXPLICIT APPROVAL."

                elif choice in (current_node.next_allowed_workflows or []):
                    # Workflow transition - not implemented yet
                    return f"❌ **Workflow transitions not yet implemented:** {choice}"

            else:
                # Invalid choice
                transitions = get_available_transitions(current_node, workflow_def)
                valid_options = [t["name"] for t in transitions]

                return f"""❌ **Invalid choice:** {choice}

**Valid options:** {", ".join(valid_options)}

**Usage:** Use context="choose: <option_name>" with exact option name."""

        # Default: show current status with enhanced guidance
        status = format_enhanced_node_status(current_node, workflow_def, session)
        return status

    except Exception as e:
        return f"❌ **Dynamic workflow error:** {str(e)}"


def _generate_node_completion_outputs(
    node_name: str,
    node_def: WorkflowNode,
    session,
    criteria_evidence: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Generate completion outputs for a workflow node.

    This function creates structured completion evidence that can be used for
    reporting and workflow analysis. It now supports actual agent-provided
    evidence instead of just hardcoded generic strings.

    Args:
        node_name: Name of the completed node
        node_def: The workflow node definition
        session: Current workflow session
        criteria_evidence: Optional dict of criterion -> evidence details provided by agent

    Returns:
        Dict containing completion outputs including evidence for acceptance criteria

    Note:
        Enhanced to capture actual agent work details instead of generic strings.
        Falls back to descriptive evidence when agent doesn't provide specific details.
    """
    outputs = {
        "goal_achieved": True,
        "completion_timestamp": datetime.now(UTC).isoformat(),
        "node_name": node_name,
    }

    # Generate evidence for acceptance criteria
    if node_def.acceptance_criteria:
        completed_criteria = {}

        # Step 1: Try to use agent-provided evidence (JSON context format)
        agent_provided_evidence = criteria_evidence or {}

        # Step 2: For criteria without agent evidence, try automatic extraction
        if not criteria_evidence or len(agent_provided_evidence) < len(
            node_def.acceptance_criteria
        ):
            automatic_evidence = _extract_automatic_evidence_from_session(
                session, node_name, node_def.acceptance_criteria
            )
            # Merge automatic evidence with agent-provided evidence (agent takes precedence)
            for criterion, auto_evidence in automatic_evidence.items():
                if criterion not in agent_provided_evidence:
                    agent_provided_evidence[criterion] = auto_evidence

        # Step 3: Generate final completed criteria with evidence or fallback
        for criterion, description in node_def.acceptance_criteria.items():
            if criterion in agent_provided_evidence:
                # Use available evidence (either agent-provided or automatically extracted)
                evidence = agent_provided_evidence[criterion].strip()
                if evidence:
                    completed_criteria[criterion] = evidence
                else:
                    # Fallback if evidence is empty
                    completed_criteria[criterion] = (
                        f"Criterion {criterion} completed (no details provided)"
                    )
            else:
                # Final fallback - enhanced description instead of generic YAML text
                completed_criteria[criterion] = (
                    f"Criterion '{criterion}' satisfied - {description}"
                )

        outputs["completed_criteria"] = completed_criteria

    # Add any additional context from session
    if hasattr(session, "execution_context") and session.execution_context:
        outputs["execution_context"] = dict(session.execution_context)

    return outputs


# =============================================================================
# MAIN REGISTRATION FUNCTION
# =============================================================================


# =============================================================================
# CACHE MANAGEMENT FUNCTIONS
# =============================================================================


def _handle_cache_restore_operation(client_id: str) -> str:
    """Handle cache restore operation."""
    try:
        # Use the fixed session sync service instead of the old broken session manager function
        from ..services import get_session_sync_service

        session_sync_service = get_session_sync_service()
        restored_count = session_sync_service.restore_sessions_from_cache(client_id)
        if restored_count > 0:
            return f"✅ Successfully restored {restored_count} workflow session(s) from cache for client '{client_id}'"
        else:
            return f"📭 No workflow sessions found in cache for client '{client_id}'"

    except Exception as e:
        return f"❌ Error restoring sessions from cache: {str(e)}"


def _extract_acceptance_criteria_from_text(text: str) -> list[str]:
    """Extract actual acceptance criteria from text content."""
    if not text:
        return []

    # Split text into sentences for analysis
    sentences = []
    for delimiter in [".", "!", "?"]:
        text = text.replace(delimiter, "|||SPLIT|||")

    potential_sentences = text.split("|||SPLIT|||")
    for sentence in potential_sentences:
        clean_sentence = sentence.strip()
        if len(clean_sentence) > 10:  # Ignore very short fragments
            sentences.append(clean_sentence)

    # Return the sentences as criteria
    return sentences


def _generate_temporal_insights(results: list) -> str:
    """Generate temporal pattern insights."""
    if not results:
        return "No results to analyze"

    from datetime import datetime, timedelta

    now = datetime.now(UTC)
    recent = len(
        [
            r
            for r in results
            if (now - r.metadata.last_updated.replace(tzinfo=None)) < timedelta(days=7)
        ]
    )
    this_month = len(
        [
            r
            for r in results
            if (now - r.metadata.last_updated.replace(tzinfo=None)) < timedelta(days=30)
        ]
    )

    oldest = min(results, key=lambda x: x.metadata.last_updated)
    newest = max(results, key=lambda x: x.metadata.last_updated)

    return f"• Recent activity (last 7 days): {recent} workflows\n• This month: {this_month} workflows\n• Timespan: {oldest.metadata.last_updated.strftime('%Y-%m-%d')} to {newest.metadata.last_updated.strftime('%Y-%m-%d')}"


def _handle_cache_list_operation(client_id: str) -> str:
    """Handle cache list operation."""
    try:
        # Use the session sync service for consistency
        from ..services import get_session_sync_service

        session_sync_service = get_session_sync_service()
        sessions = session_sync_service.list_cached_sessions(client_id)
        if not sessions:
            return f"📭 No cached sessions found for client '{client_id}'"

        result = f"📋 **Cached Sessions for client '{client_id}':**\n\n"
        for session in sessions:
            if "total_cached_sessions" in session:
                # This is cache stats
                result += "**Cache Statistics:**\n"
                result += f"- Total cached sessions: {session.get('total_cached_sessions', 0)}\n"
                result += f"- Active sessions: {session.get('active_sessions', 0)}\n"
                result += (
                    f"- Completed sessions: {session.get('completed_sessions', 0)}\n"
                )
                if session.get("oldest_entry"):
                    result += f"- Oldest entry: {session['oldest_entry']}\n"
                if session.get("newest_entry"):
                    result += f"- Newest entry: {session['newest_entry']}\n"
            else:
                # Individual session info
                result += f"**Session: {session['session_id'][:8]}...**\n"
                result += f"- Workflow: {session.get('workflow_name', 'Unknown')}\n"
                result += f"- Status: {session.get('status', 'Unknown')}\n"
                result += f"- Current Node: {session.get('current_node', 'Unknown')}\n"
                result += (
                    f"- Task: {session.get('task_description', 'No description')}\n"
                )
                result += f"- Created: {session.get('created_at', 'Unknown')}\n"
                result += f"- Updated: {session.get('last_updated', 'Unknown')}\n\n"

        return result

    except Exception as e:
        return f"❌ Error listing cached sessions: {str(e)}"


def register_phase_prompts(app: FastMCP, config=None):
    """Register purely schema-driven workflow prompts.

    Args:
        app: FastMCP application instance
        config: ServerConfig instance with repository path settings (optional)
    """
    # Initialize session manager with server config for auto-sync
    if config:
        from ..utils.session_manager import set_server_config

        set_server_config(config)

    @app.tool()
    def workflow_guidance(
        task_description: str = Field(
            description="Task description in format 'Action: Brief description'"
        ),
        action: str = Field(
            default="",
            description="Workflow action: 'start', 'plan', 'build', 'revise', 'next'",
        ),
        context: str = Field(
            default="",
            description="🚨 MANDATORY CONTEXT FORMAT: When transitioning nodes, ALWAYS use JSON format with criteria evidence. "
            'PREFERRED: JSON format: \'{"choose": "node_name", "criteria_evidence": {"criterion1": "detailed evidence"}}\' - '
            "LEGACY: String format 'choose: node_name' (DISCOURAGED - provides poor work tracking). "
            "REQUIREMENT: Include specific evidence of actual work completed, not generic confirmations.",
        ),
        options: str = Field(
            default="",
            description="Optional parameters like project_config_path for specific actions",
        ),
        session_id: str = Field(
            default="",
            description="Optional session ID to target specific workflow session. "
            "🎯 **MULTI-SESSION SUPPORT**: Use this for parallel workflows or session continuity. "
            "Examples: workflow_guidance(session_id='abc-123', ...) to target specific session. "
            "If not provided, determines session from client context (backward compatibility). "
            "🔄 **BEST PRACTICE**: Always include session_id when working with multiple concurrent workflows.",
        ),
        ctx: Context = None,
    ) -> str:
        """Pure schema-driven workflow guidance.

        Provides guidance based entirely on workflow schema structure.
        No hardcoded behavior - everything driven by YAML definitions.

        🚨 CRITICAL AGENT REQUIREMENTS:
        - **MANDATORY**: When transitioning nodes, ALWAYS provide criteria_evidence in JSON format
        - **REQUIRED**: Use JSON context format: {"choose": "node_name", "criteria_evidence": {"criterion": "detailed evidence"}}
        - **NEVER**: Use simple string format "choose: node_name" - this provides poor tracking
        - **ALWAYS**: Include specific evidence of work completed for each acceptance criterion

        CRITICAL DISCOVERY-FIRST LOGIC:
        - If no session exists, FORCE discovery first regardless of action
        - Dynamic sessions continue with schema-driven workflow
        - Legacy only when YAML workflows unavailable

        🎯 AGENT EXECUTION STANDARDS:
        - Provide detailed evidence instead of generic confirmations
        - Document actual work performed, not just criterion names
        - Use JSON format for ALL node transitions to capture real work details
        """
        try:
            # Handle direct function calls where Field defaults may be FieldInfo objects
            if hasattr(action, "default"):  # FieldInfo object
                action = action.default if action.default else ""
            if hasattr(context, "default"):  # FieldInfo object
                context = context.default if context.default else ""
            if hasattr(session_id, "default"):  # FieldInfo object
                session_id = session_id.default if session_id.default else ""
            if hasattr(options, "default"):  # FieldInfo object
                options = options.default if options.default else ""

            # Ensure parameters are strings
            action = str(action) if action is not None else ""
            context = str(context) if context is not None else ""
            session_id = str(session_id) if session_id is not None else ""
            options = str(options) if options is not None else ""

            # Resolve session using new session ID approach
            target_session_id, client_id = resolve_session_context(
                session_id, context, ctx
            )

            # Initialize workflow engine and loader
            engine = WorkflowEngine()
            loader = WorkflowLoader()

            # Determine session handling approach
            if target_session_id:
                # Explicit session ID provided - work with specific session
                session = get_session(target_session_id)
                if not session:
                    return add_session_id_to_response(
                        f"❌ **Session Not Found:** {target_session_id}\n\nThe specified session does not exist.",
                        target_session_id,
                    )
                session_type = "dynamic" if session else None
            else:
                # No explicit session - check for client sessions (backward compatibility)
                session_type = (
                    get_session_type(client_id) if client_id != "default" else None
                )

                # For backward compatibility, try to get any existing client session
                if session_type == "dynamic":
                    session = get_or_create_dynamic_session(client_id, task_description)
                    target_session_id = session.session_id if session else None
                else:
                    session = None

            if session_type == "dynamic" and session:
                # Continue with existing dynamic workflow
                workflow_def = get_dynamic_session_workflow_def(target_session_id)

                # Try on-demand workflow definition restoration if missing
                if not workflow_def and session and session.workflow_name:
                    try:
                        # Use config to construct correct workflows directory
                        if config is not None:
                            workflows_dir = str(config.workflows_dir)
                        else:
                            workflows_dir = ".accordo/workflows"

                        # Import the restoration function
                        from ..utils.session_manager import _restore_workflow_definition

                        # Attempt restore with proper path
                        _restore_workflow_definition(session, workflows_dir)

                        # Check if workflow definition is now available
                        workflow_def = get_dynamic_session_workflow_def(
                            target_session_id
                        )

                    except Exception:
                        # If on-demand loading fails, continue to discovery requirement
                        pass

                # If on-demand loading failed, fall back to discovery requirement
                if not workflow_def:
                    # Try on-demand workflow definition loading before giving up
                    from ..utils.session_manager import _restore_workflow_definition

                    if session and session.workflow_name:
                        try:
                            # Use config to construct correct workflows directory
                            if config is not None:
                                workflows_dir = str(config.workflows_dir)
                            else:
                                workflows_dir = ".accordo/workflows"

                            # Attempt restore with proper path
                            _restore_workflow_definition(session, workflows_dir)

                            # Check if workflow definition is now available
                            workflow_def = get_dynamic_session_workflow_def(
                                target_session_id
                            )

                        except Exception:
                            # If on-demand loading fails, continue to discovery requirement
                            pass

                    # If on-demand loading failed, fall back to discovery requirement
                    if not workflow_def:
                        return add_session_id_to_response(
                            f"""❌ **Missing Workflow Definition**

Dynamic session exists but workflow definition is missing.

**⚠️ DISCOVERY REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="{task_description}")`
2. **Start workflow:** Follow the discovery instructions to provide workflow YAML content""",
                            target_session_id,
                        )

                result = _handle_dynamic_workflow(
                    session, workflow_def, action, context, engine, loader
                )
                return add_session_id_to_response(result, target_session_id)

            else:
                # session_type is None - NO SESSION EXISTS
                # MANDATORY DISCOVERY-FIRST ENFORCEMENT

                if action.lower() == "start" and context and isinstance(context, str):
                    # First, try to extract workflow name from context
                    workflow_name = None
                    if context.startswith("workflow:"):
                        workflow_name = context.split("workflow:", 1)[1].strip()
                        # Remove any additional content after workflow name
                        if "\n" in workflow_name:
                            workflow_name = workflow_name.split("\n")[0].strip()

                    if workflow_name:
                        # Try to find workflow in cache first (server-side discovery)
                        cached_workflow = get_cached_workflow(workflow_name)

                        if cached_workflow:
                            # Found in cache - use it directly
                            try:
                                # Create dynamic session directly with cached workflow
                                session = create_dynamic_session(
                                    client_id, task_description, cached_workflow
                                )

                                # Store workflow definition in cache for later retrieval
                                store_workflow_definition_in_cache(
                                    session.session_id, cached_workflow
                                )

                                # Get current node info
                                current_node = cached_workflow.workflow.tree[
                                    session.current_node
                                ]
                                status = format_enhanced_node_status(
                                    current_node, cached_workflow, session
                                )

                                return add_session_id_to_response(
                                    f"""🚀 **Workflow Started:** {cached_workflow.name}

**Task:** {task_description}

**Source:** Server-side discovery cache

{status}""",
                                    session.session_id,
                                )

                            except Exception as e:
                                return _format_yaml_error_guidance(
                                    f"Error starting cached workflow: {str(e)}",
                                    workflow_name,
                                )
                        else:
                            # Not in cache - check if YAML content was provided as fallback
                            workflow_name, yaml_content, error_msg = (
                                parse_and_validate_yaml_context(context)
                            )

                            if error_msg and "YAML content is missing" in error_msg:
                                # Workflow name provided but not in cache and no YAML - need discovery
                                return f"""❌ **Workflow Not Found:** {workflow_name}

The workflow '{workflow_name}' was not found in the server cache.

**🔍 SOLUTION OPTIONS:**

1. **Run discovery first:** `workflow_discovery(task_description="{task_description}")`
   - This will discover and cache available workflows
   - Then retry with: `workflow_guidance(action="start", context="workflow: {workflow_name}")`

2. **Provide YAML directly:** Use the format:
   ```
   workflow_guidance(action="start", context="workflow: {workflow_name}\\nyaml: <your_yaml_content>")
   ```

**Note:** Server-side discovery is preferred for better performance."""

                            elif yaml_content:
                                # YAML content provided as fallback - load it
                                try:
                                    selected_workflow = (
                                        loader.load_workflow_from_string(
                                            yaml_content, workflow_name
                                        )
                                    )

                                    if selected_workflow:
                                        # Create dynamic session directly with selected workflow
                                        session = create_dynamic_session(
                                            client_id,
                                            task_description,
                                            selected_workflow,
                                        )

                                        # Store workflow definition in cache for later retrieval
                                        store_workflow_definition_in_cache(
                                            session.session_id, selected_workflow
                                        )

                                        # Get current node info
                                        current_node = selected_workflow.workflow.tree[
                                            session.current_node
                                        ]
                                        status = format_enhanced_node_status(
                                            current_node, selected_workflow, session
                                        )

                                        return f"""🚀 **Workflow Started:** {selected_workflow.name}

**Task:** {task_description}

**Source:** YAML fallback (custom workflow)

{status}"""
                                    else:
                                        return _format_yaml_error_guidance(
                                            "Failed to load workflow from provided YAML - invalid structure",
                                            workflow_name,
                                        )

                                except Exception as e:
                                    return _format_yaml_error_guidance(
                                        f"Error loading workflow from YAML: {str(e)}",
                                        workflow_name,
                                    )
                            else:
                                return _format_yaml_error_guidance(
                                    error_msg, workflow_name
                                )

                    else:
                        # No workflow name provided - parse as full YAML context
                        workflow_name, yaml_content, error_msg = (
                            parse_and_validate_yaml_context(context)
                        )

                        if error_msg:
                            return _format_yaml_error_guidance(error_msg, workflow_name)

                        if workflow_name and yaml_content:
                            # Load workflow from validated YAML string
                            try:
                                selected_workflow = loader.load_workflow_from_string(
                                    yaml_content, workflow_name
                                )

                                if selected_workflow:
                                    # Create dynamic session directly with selected workflow
                                    session = create_dynamic_session(
                                        client_id, task_description, selected_workflow
                                    )

                                    # Store workflow definition in cache for later retrieval
                                    store_workflow_definition_in_cache(
                                        session.session_id, selected_workflow
                                    )

                                    # Get current node info
                                    current_node = selected_workflow.workflow.tree[
                                        session.current_node
                                    ]
                                    status = format_enhanced_node_status(
                                        current_node, selected_workflow, session
                                    )

                                    return f"""🚀 **Workflow Started:** {selected_workflow.name}

**Task:** {task_description}

**Source:** YAML content (custom workflow)

{status}"""
                                else:
                                    return _format_yaml_error_guidance(
                                        "Failed to load workflow from provided YAML - invalid structure",
                                        workflow_name,
                                    )

                            except Exception as e:
                                return _format_yaml_error_guidance(
                                    f"Error loading workflow from YAML: {str(e)}",
                                    workflow_name,
                                )
                        else:
                            return _format_yaml_error_guidance(
                                "Invalid context format", workflow_name
                            )

                elif action.lower() == "start":
                    # No context provided - show discovery
                    return f"""🔍 **Workflow Discovery Required**

**⚠️ AGENT ACTION REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="{task_description}")`
2. **Start workflow:** Use just the workflow name: `workflow_guidance(action="start", context="workflow: <name>")`

**Note:** Server-side discovery enables efficient workflow lookup by name only."""

                else:
                    # NO SESSION + NON-START ACTION = FORCE DISCOVERY FIRST
                    return f"""❌ **No Active Workflow Session**

You called workflow_guidance with action="{action}" but there's no active workflow session.

**⚠️ DISCOVERY REQUIRED FIRST:**

1. **Discover workflows:** `workflow_discovery(task_description="{task_description}")`
2. **Start workflow:** Use the discovery instructions to start a workflow
3. **Then continue:** `workflow_guidance(action="{action}", ...)`

🚨 **CRITICAL:** You must start a workflow session before using action="{action}". The system enforces discovery-first workflow initiation."""

        except Exception as e:
            # Any error requires workflow discovery
            import traceback

            traceback.print_exc()
            return f"""❌ **Error in schema-driven workflow:** {str(e)}

**⚠️ DISCOVERY REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="{task_description}")`
2. **Start workflow:** Follow the discovery instructions to provide workflow YAML content"""

    @app.tool()
    def workflow_state(
        operation: str = Field(
            description="State operation: 'get' (current status), 'update' (modify state), 'reset' (clear state)"
        ),
        updates: str = Field(
            default="",
            description='JSON string with state updates for \'update\' operation. Example: \'{"phase": "CONSTRUCT", "status": "RUNNING"}\'',
        ),
        session_id: str = Field(
            default="",
            description="Optional session ID to target specific workflow session. "
            "🎯 **MULTI-SESSION SUPPORT**: Use this to track state for specific workflow sessions. "
            "Examples: workflow_state(operation='get', session_id='abc-123') to check specific session status. "
            "If not provided, determines session from client context (backward compatibility). "
            "🔄 **BEST PRACTICE**: Always include session_id when managing multiple concurrent workflows.",
        ),
        ctx: Context = None,
    ) -> str:
        """Get or update workflow state."""
        try:
            # Resolve session using new session ID approach
            target_session_id, client_id = resolve_session_context(session_id, "", ctx)

            if operation == "get":
                # Determine which session to work with
                if target_session_id:
                    # Explicit session ID provided
                    session = get_session(target_session_id)
                    if not session:
                        return add_session_id_to_response(
                            f"❌ **Session Not Found:** {target_session_id}",
                            target_session_id,
                        )
                    workflow_def = get_dynamic_session_workflow_def(target_session_id)
                else:
                    # Fallback to client-based session (backward compatibility)
                    session_type = get_session_type(client_id)
                    if session_type == "dynamic":
                        session = get_or_create_dynamic_session(client_id, "")
                        workflow_def = get_dynamic_session_workflow_def(
                            session.session_id if session else None
                        )
                        target_session_id = session.session_id if session else None
                    else:
                        session = None
                        workflow_def = None

                # Try on-demand workflow definition restoration if missing
                if session and not workflow_def and session.workflow_name:
                    try:
                        # Use config to construct correct workflows directory (same approach as workflow_guidance)
                        if config is not None:
                            workflows_dir = str(config.workflows_dir)
                        else:
                            workflows_dir = ".accordo/workflows"

                        print(
                            f"🚨 DEBUG: Attempting on-demand workflow definition restore for session {target_session_id}"
                        )
                        print(
                            f"🚨 DEBUG: Session workflow_name: {session.workflow_name}"
                        )
                        print(f"🚨 DEBUG: Using workflows_dir: {workflows_dir}")

                        # Import the restoration function
                        from ..utils.session_manager import _restore_workflow_definition

                        # Attempt restore with proper path
                        _restore_workflow_definition(session, workflows_dir)
                        print(
                            "🚨 DEBUG: _restore_workflow_definition completed without exception"
                        )

                        # Check if workflow definition is now available
                        workflow_def = get_dynamic_session_workflow_def(
                            target_session_id
                        )
                        print(
                            f"🚨 DEBUG: After restore, workflow_def is: {workflow_def is not None}"
                        )

                    except Exception as e:
                        # If on-demand loading fails, continue with error
                        print(
                            f"🚨 DEBUG: On-demand workflow definition restore failed: {e}"
                        )
                        import traceback

                        traceback.print_exc()

                if session and workflow_def:
                    current_node = workflow_def.workflow.tree.get(session.current_node)
                    summary = get_workflow_summary(workflow_def)

                    result = f"""📊 **DYNAMIC WORKFLOW STATE**

**Workflow:** {summary["name"]}
**Current Node:** {session.current_node}
**Status:** {session.status}

**Current Goal:** {current_node.goal if current_node else "Unknown"}

**Progress:** {session.current_node} (Node {list(summary["all_nodes"]).index(session.current_node) + 1} of {summary["total_nodes"]})

**Workflow Structure:**
- **Root:** {summary["root_node"]}
- **Total Nodes:** {summary["total_nodes"]}
- **Decision Points:** {", ".join(summary["decision_nodes"]) if summary["decision_nodes"] else "None"}
- **Terminal Nodes:** {", ".join(summary["terminal_nodes"]) if summary["terminal_nodes"] else "None"}

**Session State:**
```markdown
{export_session_to_markdown(target_session_id)}
```"""
                    return add_session_id_to_response(result, target_session_id)
                elif session:
                    return add_session_id_to_response(
                        "❌ **Error:** Dynamic session has no workflow definition. Try manually restoring cache with workflow_cache_management(operation='restore').",
                        target_session_id,
                    )

                else:
                    # No dynamic session found
                    return """❌ **No Active Workflow Session**

No YAML workflow session is currently active.

**⚠️ DISCOVERY REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="Your task description")`
2. **Start workflow:** Follow the discovery instructions to provide workflow YAML content"""

            elif operation == "update":
                if not updates:
                    return add_session_id_to_response(
                        "❌ **Error:** No updates provided.", target_session_id
                    )

                try:
                    update_data = json.loads(updates)

                    # Determine which session to update
                    update_session_id = target_session_id
                    if not update_session_id:
                        # Fallback to client-based session (backward compatibility)
                        session_type = get_session_type(client_id)
                        if session_type == "dynamic":
                            session = get_or_create_dynamic_session(client_id, "")
                            update_session_id = session.session_id if session else None
                        else:
                            return add_session_id_to_response(
                                """❌ **No Active Workflow Session**

Cannot update state - no YAML workflow session is currently active.

**⚠️ DISCOVERY REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="Your task description")`
2. **Start workflow:** Follow the discovery instructions to provide workflow YAML content""",
                                None,
                            )

                    if update_session_id:
                        # Update dynamic session
                        if "node" in update_data:
                            update_dynamic_session_node(
                                update_session_id, update_data["node"]
                            )
                        if "status" in update_data:
                            update_dynamic_session_status(
                                update_session_id, update_data["status"]
                            )
                        if "log_entry" in update_data:
                            add_log_to_session(
                                update_session_id, update_data["log_entry"]
                            )

                        # Force immediate cache sync after state updates
                        from ..utils.session_manager import sync_session

                        sync_result = sync_session(update_session_id)
                        print(
                            f"Debug: Immediate cache sync after state update - session: {update_session_id[:8]}, success: {sync_result}"
                        )

                    return add_session_id_to_response(
                        "✅ **State updated successfully.**", update_session_id
                    )

                except json.JSONDecodeError:
                    return add_session_id_to_response(
                        "❌ **Error:** Invalid JSON in updates parameter.",
                        target_session_id,
                    )

            elif operation == "reset":
                # Reset session (implementation depends on session manager)
                return add_session_id_to_response(
                    "✅ **State reset - ready for new workflow.**", target_session_id
                )

            else:
                return add_session_id_to_response(
                    f"❌ **Invalid operation:** {operation}. Use 'get', 'update', or 'reset'.",
                    target_session_id,
                )

        except Exception as e:
            return add_session_id_to_response(
                f"❌ **Error in workflow_state:** {str(e)}", target_session_id
            )

    @app.tool()
    def workflow_cache_management(
        operation: str = Field(
            description="Cache operation: 'restore' (restore sessions from cache), 'list' (list cached sessions), 'stats' (cache statistics), 'regenerate_embeddings' (update embeddings with enhanced semantic content), 'force_regenerate_embeddings' (force regenerate all embeddings regardless of text changes)"
        ),
        client_id: str = Field(
            default="default",
            description="Client ID for cache operations. Defaults to 'default' if not specified.",
        ),
        ctx: Context = None,
    ) -> str:
        """Manage workflow session cache for persistence across MCP restarts."""
        try:
            # Resolve client ID from context if available
            if ctx is not None:
                try:
                    if hasattr(ctx, "client_id") and ctx.client_id:
                        client_id = ctx.client_id
                except AttributeError:
                    pass  # Use default client_id

            if operation == "restore":
                return _handle_cache_restore_operation(client_id)
            elif operation == "list":
                return _handle_cache_list_operation(client_id)
            elif operation == "stats":
                try:
                    from ..services import get_cache_service

                    cache_service = get_cache_service()

                    if not cache_service.is_available():
                        return "❌ Cache mode is not enabled or not available"

                    cache_manager = cache_service.get_cache_manager()

                    stats = cache_manager.get_cache_stats()
                    if not stats:
                        return "❌ Unable to retrieve cache statistics"

                    return f"""📊 **Cache Statistics:**

**Cache State:**
- Collection: {stats.collection_name}
- Total entries: {stats.total_entries}
- Active sessions: {stats.active_sessions} 
- Completed sessions: {stats.completed_sessions}
- Cache size: {stats.cache_size_mb:.2f} MB

**Entry Timeline:**
- Oldest entry: {stats.oldest_entry.isoformat() if stats.oldest_entry else "None"}
- Newest entry: {stats.newest_entry.isoformat() if stats.newest_entry else "None"}

**Cache Availability:** ✅ ChromaDB cache is active and available"""

                except Exception as e:
                    return f"❌ Error getting cache statistics: {str(e)}"
            elif operation == "regenerate_embeddings":
                try:
                    from ..services import get_cache_service

                    cache_service = get_cache_service()
                    if not cache_service.is_available():
                        return "❌ Cache mode is not enabled or not available"

                    cache_manager = cache_service.get_cache_manager()

                    # Regenerate embeddings with enhanced semantic content
                    regenerated_count = (
                        cache_manager.regenerate_embeddings_for_enhanced_search()
                    )

                    return f"""🔄 **Embedding Regeneration Complete:**

**Results:**
- Embeddings regenerated: {regenerated_count}
- Enhanced semantic content: ✅ Active
- Search improvement: ✅ Better similarity matching expected

**Next Steps:**
- Test semantic search with: `workflow_semantic_search(query="your search")`
- Enhanced embeddings now include detailed node completion evidence
- Similarity scores should be significantly improved"""

                except Exception as e:
                    return f"❌ Error regenerating embeddings: {str(e)}"
            elif operation == "force_regenerate_embeddings":
                try:
                    from ..services import get_cache_service

                    cache_service = get_cache_service()
                    if not cache_service.is_available():
                        return "❌ Cache mode is not enabled or not available"

                    cache_manager = cache_service.get_cache_manager()

                    # Force regenerate all embeddings regardless of text changes
                    regenerated_count = (
                        cache_manager.regenerate_embeddings_for_enhanced_search(
                            force_regenerate=True
                        )
                    )

                    return f"""🔄 **Force Embedding Regeneration Complete:**

**Results:**
- Embeddings force regenerated: {regenerated_count}
- All embeddings updated with current model
- Enhanced semantic content: ✅ Active
- Search improvement: ✅ Better similarity matching expected

**Next Steps:**
- Test semantic search with: `workflow_semantic_search(query="your search")`
- All embeddings now use current embedding model and enhanced text generation
- Similarity scores should be significantly improved"""

                except Exception as e:
                    return f"❌ Error force regenerating embeddings: {str(e)}"
            else:
                return f"❌ **Invalid operation:** {operation}. Valid operations: 'restore', 'list', 'stats', 'regenerate_embeddings', 'force_regenerate_embeddings'"

        except Exception as e:
            return f"❌ **Error in workflow_cache_management:** {str(e)}"

    @app.tool()
    def workflow_semantic_search(
        query: str = Field(
            description="Description of current task, problem, or context to find related past work"
        ),
        client_id: str = Field(
            default="default",
            description="Client ID to search within. Defaults to 'default' if not specified.",
        ),
        max_results: int = Field(
            default=3, description="Maximum number of results to return (1-100)"
        ),
        min_similarity: float = Field(
            default=0.1,
            description="Minimum similarity threshold (0.0-1.0, higher means more similar)",
        ),
        ctx: Context = None,
    ) -> str:
        """Find all relevant past workflow contexts and provide the raw context for agent analysis.

        Returns all findings without context cutting or analysis type filtering.
        """
        try:
            # Resolve client ID from context if available
            if ctx is not None:
                try:
                    if hasattr(ctx, "client_id") and ctx.client_id:
                        client_id = ctx.client_id
                except AttributeError:
                    pass

            # Validate parameters
            max_results = max(1, min(100, max_results))
            min_similarity = max(0.0, min(1.0, min_similarity))

            from ..services import get_cache_service

            cache_service = get_cache_service()
            if not cache_service.is_available():
                return "❌ Cache mode not enabled. Semantic analysis unavailable."

            cache_manager = cache_service.get_cache_manager()

            # Perform semantic search
            results = cache_manager.semantic_search(
                search_text=query,
                client_id=client_id,
                min_similarity=min_similarity,
                max_results=max_results,
            )

            if not results:
                return f"No results found for query: {query}"

            # Build simple result list - just split the results properly
            result_parts = []

            for i, search_result in enumerate(results, 1):
                metadata = search_result.metadata
                similarity_score = search_result.similarity_score

                # Get all available context without cutting
                context_parts = []

                if hasattr(metadata, "current_item") and metadata.current_item:
                    context_parts.append(f"Current Item: {metadata.current_item}")

                if (
                    hasattr(search_result, "matching_text")
                    and search_result.matching_text
                ):
                    context_parts.append(
                        f"Matching Text: {search_result.matching_text}"
                    )

                # Add node outputs (completed work and acceptance criteria evidence)
                if hasattr(metadata, "node_outputs") and metadata.node_outputs:
                    node_outputs_text = []
                    for node_name, outputs in metadata.node_outputs.items():
                        node_output_parts = [f"Node {node_name}:"]
                        for key, value in outputs.items():
                            # Handle different value types
                            if isinstance(value, dict):
                                # For nested dictionaries (like completed_criteria)
                                sub_parts = []
                                for sub_key, sub_value in value.items():
                                    sub_parts.append(f"{sub_key}: {sub_value}")
                                value_str = "{" + ", ".join(sub_parts) + "}"
                            else:
                                value_str = str(value)
                            node_output_parts.append(f"  {key}: {value_str}")
                        node_outputs_text.append("\n".join(node_output_parts))
                    context_parts.append(
                        f"Node Outputs:\n{chr(10).join(node_outputs_text)}"
                    )

                # Include ALL available metadata fields
                result_entry = f"""--- Result {i} ---
Workflow: {metadata.workflow_name}
Session: {metadata.session_id}
Client ID: {metadata.client_id}
Similarity: {similarity_score:.3f}
Status: {metadata.status}
Current Node: {metadata.current_node}
Workflow File: {metadata.workflow_file if metadata.workflow_file else "None"}
Created At: {metadata.created_at}
Last Updated: {metadata.last_updated}
Cache Created At: {metadata.cache_created_at}
Cache Version: {metadata.cache_version}

Context:
{chr(10).join(context_parts)}
"""
                result_parts.append(result_entry)

            return "\n".join(result_parts)

        except Exception as e:
            return f"❌ Error in workflow_semantic_search: {str(e)}"
