"""YAML parsing and validation functions for workflow operations.

This module provides functions to parse, validate, and reformat YAML workflow content.
"""

import json

import yaml

from ..utils.schema_analyzer import extract_choice_from_context


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
                if workflow_name:
                    return workflow_name, None, None

        # Method 2: Try parsing as pure YAML content
        if _looks_like_yaml(context):
            result = _parse_pure_yaml(context)
            if result and len(result) == 2:
                workflow_name, yaml_content = result
                if workflow_name and yaml_content:
                    # Validate and reformat YAML
                    formatted_yaml = _validate_and_reformat_yaml(yaml_content)
                    if formatted_yaml:
                        return workflow_name, formatted_yaml, None

        # Method 3: Extract only workflow name if that's all that's provided
        workflow_name = _extract_workflow_name_only(context)
        if workflow_name:
            return workflow_name, None, None

        return None, None, "Could not parse workflow name or YAML content from context"

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


def parse_criteria_evidence_context(
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