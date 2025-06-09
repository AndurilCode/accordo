"""Path utilities for workflow commander configuration and state files."""

from pathlib import Path


def get_workflow_dir(base_path: str | Path = ".") -> Path:
    """Get the .accordo directory, creating it if it doesn't exist.

    Args:
        base_path: Base path where .accordo should be located

    Returns:
        Path to .accordo directory

    Raises:
        OSError: If directory cannot be created
    """
    base = Path(base_path)
    workflow_dir = base / ".accordo"

    try:
        workflow_dir.mkdir(exist_ok=True)
        return workflow_dir
    except OSError as e:
        # Log warning but don't fail - fallback to current directory
        print(f"Warning: Could not create .accordo directory: {e}")
        print("Falling back to current directory for workflow files")
        return base


def get_project_config_path(base_path: str | Path = ".") -> Path:
    """Get the path to project_config.md in .accordo directory.

    Args:
        base_path: Base path where .accordo should be located

    Returns:
        Path to .accordo/project_config.md
    """
    workflow_dir = get_workflow_dir(base_path)
    return workflow_dir / "project_config.md"


def get_workflow_state_path(
    format_type: str = "md", base_path: str | Path = "."
) -> Path:
    """Get the path to workflow state file in .accordo directory.

    Args:
        format_type: File format ('md' or 'json')
        base_path: Base path where .accordo should be located

    Returns:
        Path to .accordo/workflow_state.md or .accordo/workflow_state.json
    """
    workflow_dir = get_workflow_dir(base_path)
    extension = "json" if format_type.lower() == "json" else "md"
    return workflow_dir / f"workflow_state.{extension}"


def migrate_config_file(
    old_path: str | Path = "project_config.md", base_path: str | Path = "."
) -> bool:
    """Migrate existing project_config.md to .accordo directory.

    Args:
        old_path: Path to existing project_config.md file
        base_path: Base path where .accordo should be located

    Returns:
        True if migration succeeded or file didn't exist, False if migration failed
    """
    old_file = Path(old_path)
    if not old_file.exists():
        return True  # Nothing to migrate

    try:
        new_path = get_project_config_path(base_path)
        if new_path.exists():
            # Backup existing file in .accordo
            backup_path = new_path.with_suffix(".md.backup")
            new_path.rename(backup_path)
            print(f"Backed up existing {new_path} to {backup_path}")

        # Move the old file to new location
        old_file.rename(new_path)
        print(f"Migrated {old_file} to {new_path}")
        return True
    except OSError as e:
        print(f"Warning: Could not migrate {old_file}: {e}")
        return False


def migrate_workflow_state_files(base_path: str | Path = ".") -> bool:
    """Migrate existing workflow state files to .accordo directory.

    Args:
        base_path: Base path where .accordo should be located

    Returns:
        True if migration succeeded or no files to migrate, False if migration failed
    """
    base = Path(base_path)
    success = True

    # Check for workflow_state.md
    old_md = base / "workflow_state.md"
    if old_md.exists():
        try:
            new_md = get_workflow_state_path("md", base_path)
            if new_md.exists():
                backup_md = new_md.with_suffix(".md.backup")
                new_md.rename(backup_md)
                print(f"Backed up existing {new_md} to {backup_md}")
            old_md.rename(new_md)
            print(f"Migrated {old_md} to {new_md}")
        except OSError as e:
            print(f"Warning: Could not migrate {old_md}: {e}")
            success = False

    # Check for workflow_state.json
    old_json = base / "workflow_state.json"
    if old_json.exists():
        try:
            new_json = get_workflow_state_path("json", base_path)
            if new_json.exists():
                backup_json = new_json.with_suffix(".json.backup")
                new_json.rename(backup_json)
                print(f"Backed up existing {new_json} to {backup_json}")
            old_json.rename(new_json)
            print(f"Migrated {old_json} to {new_json}")
        except OSError as e:
            print(f"Warning: Could not migrate {old_json}: {e}")
            success = False

    return success
