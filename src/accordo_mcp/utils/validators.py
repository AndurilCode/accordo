"""Validation utilities for project configuration files."""

from pathlib import Path

from .path_utils import get_project_config_path


def validate_project_config(
    file_path: str | None = None,
) -> tuple[bool, list[str]]:
    """Validate project_config.md file structure.

    Args:
        file_path: Optional path to project_config.md. If None, uses .accordo/project_config.md

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Use path utilities to get default path if none provided
    config_path = get_project_config_path() if file_path is None else Path(file_path)

    if not config_path.exists():
        return False, ["project_config.md file does not exist"]

    try:
        with open(config_path) as f:
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


def validate_project_files(
    project_config_path: str | None = None,
) -> tuple[bool, list[str]]:
    """Validate project configuration file.

    Args:
        project_config_path: Optional path to project config file. If None, uses .accordo/project_config.md

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    # Validate project config
    config_valid, config_issues = validate_project_config(project_config_path)
    if not config_valid:
        return False, [f"project_config.md: {issue}" for issue in config_issues]

    return True, []
