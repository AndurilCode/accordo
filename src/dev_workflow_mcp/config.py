"""Configuration management for the MCP server."""

from pathlib import Path


class ServerConfig:
    """Configuration settings for the MCP server."""

    def __init__(self, repository_path: str | None = None):
        """Initialize server configuration.

        Args:
            repository_path: Optional path to the repository root where .workflow-commander
                           folder should be located. Defaults to current directory.
        """
        if repository_path:
            self.repository_path = Path(repository_path).resolve()
        else:
            self.repository_path = Path.cwd()

        # Validate the repository path exists
        if not self.repository_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repository_path}")

        if not self.repository_path.is_dir():
            raise ValueError(
                f"Repository path is not a directory: {self.repository_path}"
            )

    @property
    def workflow_commander_dir(self) -> Path:
        """Get the .workflow-commander directory path."""
        return self.repository_path / ".workflow-commander"

    @property
    def workflows_dir(self) -> Path:
        """Get the workflows directory path."""
        return self.workflow_commander_dir / "workflows"

    @property
    def project_config_path(self) -> Path:
        """Get the project configuration file path."""
        return self.workflow_commander_dir / "project_config.md"

    def ensure_workflow_commander_dir(self) -> bool:
        """Ensure the .workflow-commander directory exists.

        Returns:
            True if directory exists or was created successfully, False otherwise.
        """
        try:
            self.workflow_commander_dir.mkdir(exist_ok=True)
            return True
        except (OSError, PermissionError):
            return False

    def ensure_workflows_dir(self) -> bool:
        """Ensure the workflows directory exists.

        Returns:
            True if directory exists or was created successfully, False otherwise.
        """
        try:
            if self.ensure_workflow_commander_dir():
                self.workflows_dir.mkdir(exist_ok=True)
                return True
            return False
        except (OSError, PermissionError):
            return False

    def validate_configuration(self) -> tuple[bool, list[str]]:
        """Validate the configuration and provide status information.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check repository path
        if not self.repository_path.exists():
            issues.append(f"Repository path does not exist: {self.repository_path}")
        elif not self.repository_path.is_dir():
            issues.append(f"Repository path is not a directory: {self.repository_path}")

        # Check .workflow-commander directory (not required to exist)
        if (
            self.workflow_commander_dir.exists()
            and not self.workflow_commander_dir.is_dir()
        ):
            issues.append(
                f".workflow-commander exists but is not a directory: {self.workflow_commander_dir}"
            )

        # Check workflows directory (not required to exist)
        if self.workflows_dir.exists() and not self.workflows_dir.is_dir():
            issues.append(
                f"workflows directory exists but is not a directory: {self.workflows_dir}"
            )

        return len(issues) == 0, issues

    def __str__(self) -> str:
        """String representation of the configuration."""
        return f"ServerConfig(repository_path={self.repository_path})"

    def __repr__(self) -> str:
        """Detailed string representation of the configuration."""
        return f"ServerConfig(repository_path='{self.repository_path}', workflows_dir='{self.workflows_dir}')"
