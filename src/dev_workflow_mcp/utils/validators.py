"""Validation utilities for project configuration files."""

from pathlib import Path


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


def validate_project_files(
    project_config_path: str = "project_config.md",
) -> tuple[bool, list[str]]:
    """Validate project configuration file.

    Args:
        project_config_path: Path to project config file

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    # Validate project config
    config_valid, config_issues = validate_project_config(project_config_path)
    if not config_valid:
        return False, [f"project_config.md: {issue}" for issue in config_issues]

    return True, []
