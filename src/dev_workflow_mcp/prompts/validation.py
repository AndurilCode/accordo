"""Input validation functions for workflow operations.

This module provides validation for task descriptions and other input parameters.
"""


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
