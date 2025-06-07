"""Utility for processing placeholder replacement in workflow content.

This module handles the replacement of ${{ inputs.* }} placeholders with actual values.
"""

import re
from typing import Any


def replace_placeholders(content: str, inputs: dict[str, Any]) -> str:
    """Replace ${{ inputs.* }} placeholders in content with actual values.

    Args:
        content: String content containing placeholders
        inputs: Dictionary mapping input names to their values

    Returns:
        str: Content with placeholders replaced by actual values

    Examples:
        >>> replace_placeholders("Task: ${{ inputs.task_description }}", {"task_description": "Add authentication"})
        "Task: Add authentication"

        >>> replace_placeholders("Path: ${{ inputs.config_path }}", {"config_path": "/path/to/config"})
        "Path: /path/to/config"
    """
    if not content or not inputs:
        return content

    # Pattern to match ${{ inputs.variable_name }}
    pattern = r"\$\{\{\s*inputs\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"

    def replace_match(match):
        variable_name = match.group(1)
        if variable_name in inputs:
            value = inputs[variable_name]
            # Convert value to string, handling None and other types
            if value is None:
                return ""
            return str(value)
        else:
            # If variable not found, leave placeholder unchanged
            return match.group(0)

    return re.sub(pattern, replace_match, content)


def process_workflow_content(workflow_dict: dict, inputs: dict[str, Any]) -> dict:
    """Process a workflow dictionary to replace all placeholders with actual values.

    Args:
        workflow_dict: Dictionary representation of workflow
        inputs: Dictionary mapping input names to their values

    Returns:
        dict: Workflow dictionary with all placeholders replaced
    """
    if not inputs:
        return workflow_dict

    # Create a deep copy to avoid modifying the original
    import copy

    processed_workflow = copy.deepcopy(workflow_dict)

    # Recursively process all string values in the workflow
    _process_recursive(processed_workflow, inputs)

    return processed_workflow


def _process_recursive(obj: Any, inputs: dict[str, Any]) -> None:
    """Recursively process an object to replace placeholders in all string values.

    Args:
        obj: Object to process (modified in place)
        inputs: Dictionary mapping input names to their values
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str):
                obj[key] = replace_placeholders(value, inputs)
            else:
                _process_recursive(value, inputs)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str):
                obj[i] = replace_placeholders(item, inputs)
            else:
                _process_recursive(item, inputs)
