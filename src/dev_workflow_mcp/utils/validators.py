"""Validation utilities for workflow files."""

import re
from pathlib import Path


def validate_workflow_state(
    file_path: str = "workflow_state.md",
) -> tuple[bool, list[str]]:
    """Validate workflow_state.md file structure.

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    if not Path(file_path).exists():
        return False, ["workflow_state.md file does not exist"]

    try:
        with open(file_path) as f:
            content = f.read()
    except Exception as e:
        return False, [f"Could not read file: {e}"]

    # Required sections
    required_sections = [
        "## State",
        "## Plan",
        "## Rules",
        "## Items",
        "## Log",
        "## ArchiveLog",
    ]

    for section in required_sections:
        if section not in content:
            issues.append(f"Missing required section: {section}")

    # Check State section format
    state_match = re.search(r"## State\s*\n(.*?)\n## ", content, re.DOTALL)
    if state_match:
        state_content = state_match.group(1)
        required_fields = ["Phase:", "Status:", "CurrentItem:"]
        for field in required_fields:
            if field not in state_content:
                issues.append(f"Missing field in State section: {field}")
    else:
        issues.append("Could not parse State section")

    # Check Items table format
    if "## Items" in content:
        items_match = re.search(r"## Items\s*\n(.*?)\n## ", content, re.DOTALL)
        if items_match:
            items_content = items_match.group(1)
            if "| id | description | status |" not in items_content:
                issues.append("Items section missing proper table header")
        else:
            # Items might be the last section
            items_match = re.search(r"## Items\s*\n(.*?)$", content, re.DOTALL)
            if items_match:
                items_content = items_match.group(1)
                if "| id | description | status |" not in items_content:
                    issues.append("Items section missing proper table header")

    return len(issues) == 0, issues


def validate_project_config(
    file_path: str = "project_config.md",
) -> tuple[bool, list[str]]:
    """Validate project_config.md file structure.

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    if not Path(file_path).exists():
        return False, ["project_config.md file does not exist"]

    try:
        with open(file_path) as f:
            content = f.read()
    except Exception as e:
        return False, [f"Could not read file: {e}"]

    # Required sections
    required_sections = [
        "## Project Info",
        "## Dependencies",
        "## Test Commands",
        "## Changelog",
    ]

    for section in required_sections:
        if section not in content:
            issues.append(f"Missing required section: {section}")

    return len(issues) == 0, issues


def validate_workflow_files(
    workflow_state_path: str = "workflow_state.md",
    project_config_path: str = "project_config.md",
) -> tuple[bool, list[str]]:
    """Validate both workflow_state.md and project_config.md files.

    Args:
        workflow_state_path: Path to workflow state file
        project_config_path: Path to project config file

    Returns:
        Tuple of (all_valid, list_of_all_issues)
    """
    all_issues = []

    # Validate workflow state
    state_valid, state_issues = validate_workflow_state(workflow_state_path)
    if not state_valid:
        all_issues.extend([f"workflow_state.md: {issue}" for issue in state_issues])

    # Validate project config
    config_valid, config_issues = validate_project_config(project_config_path)
    if not config_valid:
        all_issues.extend([f"project_config.md: {issue}" for issue in config_issues])

    return len(all_issues) == 0, all_issues
