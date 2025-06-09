"""Base configuration handler with common functionality."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models.config import MCPServer
from ..models.platform import PlatformInfo


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails."""

    pass


class BaseConfigHandler(ABC):
    """Abstract base class for platform-specific configuration handlers."""

    def __init__(self, platform_info: PlatformInfo | None = None):
        """Initialize the handler with platform information.

        Args:
            platform_info: Platform-specific configuration information
        """
        self.platform_info = platform_info
        self.platform = platform_info.platform if platform_info else None

    @abstractmethod
    def create_config(self, servers: dict[str, MCPServer]) -> dict[str, Any]:
        """Create platform-specific configuration from MCP servers.

        Args:
            servers: Dictionary of MCP server configurations

        Returns:
            Platform-specific configuration dictionary
        """
        pass

    @abstractmethod
    def load_existing_config(self, config_path: Path) -> dict[str, Any] | None:
        """Load existing configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            Existing configuration dictionary or None if not found
        """
        pass

    def load_config(self, config_path: Path) -> dict[str, Any]:
        """Load configuration from file, raising exception if not found.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If configuration is invalid JSON
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            content = config_path.read_text()
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}") from e

    @abstractmethod
    def get_servers_from_config(self, config: dict[str, Any]) -> dict[str, MCPServer]:
        """Extract MCP servers from platform-specific configuration.

        Args:
            config: Platform-specific configuration

        Returns:
            Dictionary of server name to MCPServer objects
        """
        pass

    @abstractmethod
    def merge_configs(
        self, existing: dict[str, Any], new: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge new configuration with existing configuration.

        Args:
            existing: Existing configuration
            new: New configuration to merge

        Returns:
            Merged configuration
        """
        pass

    def validate_config_structure(self, config: dict[str, Any]) -> bool:
        """Validate basic configuration structure.

        Args:
            config: Configuration to validate

        Returns:
            True if valid structure
        """
        try:
            # Basic validation - ensure JSON serializable
            json.dumps(config)
            # Check that it's a dictionary
            return isinstance(config, dict)
        except (TypeError, ValueError):
            return False

    def validate_server_config(self, server_config: MCPServer) -> list[str]:
        """Validate an individual server configuration.

        Args:
            server_config: Server configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not server_config.command:
            errors.append("Command cannot be empty")

        if server_config.args is not None and not isinstance(server_config.args, list):
            errors.append("Args must be a list")

        if server_config.env is not None:
            if not isinstance(server_config.env, dict):
                errors.append("Environment variables must be a dictionary")
            else:
                for key, value in server_config.env.items():
                    if not isinstance(key, str) or not isinstance(value, str):
                        errors.append(
                            "Environment variable keys and values must be strings"
                        )

        return errors

    def validate_server_config_raw(
        self, server_name: str, server_config_dict: dict[str, Any]
    ) -> list[str]:
        """Validate raw server configuration dictionary before creating MCPServer object.

        Args:
            server_name: Name of the server
            server_config_dict: Raw server configuration dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check required fields
        if not server_config_dict.get("command"):
            errors.append("Command cannot be empty")

        # Check args type
        args = server_config_dict.get("args")
        if args is not None and not isinstance(args, list):
            errors.append("Args must be a list")

        # Check env type
        env = server_config_dict.get("env")
        if env is not None:
            if not isinstance(env, dict):
                errors.append("Environment variables must be a dictionary")
            else:
                for key, value in env.items():
                    if not isinstance(key, str) or not isinstance(value, str):
                        errors.append(
                            "Environment variable keys and values must be strings"
                        )

        return errors

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration structure.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, raises ConfigValidationError if invalid
        """
        try:
            # Basic validation - ensure JSON serializable
            json.dumps(config)
            return True
        except (TypeError, ValueError) as e:
            raise ConfigValidationError(f"Configuration is not valid JSON: {e}") from e

    def backup_config(self, config_path: Path) -> Path | None:
        """Create a backup of existing configuration.

        Args:
            config_path: Path to configuration file

        Returns:
            Path to backup file or None if no backup created
        """
        if not config_path.exists():
            return None

        backup_path = config_path.with_suffix(f"{config_path.suffix}.backup")
        counter = 1

        # Find unique backup filename
        while backup_path.exists():
            backup_path = config_path.with_suffix(
                f"{config_path.suffix}.backup.{counter}"
            )
            counter += 1

        try:
            backup_path.write_text(config_path.read_text())
            return backup_path
        except (OSError, PermissionError):
            return None

    def save_config(
        self, config: dict[str, Any], config_path: Path, create_backup: bool = True
    ) -> bool:
        """Save configuration to file.

        Args:
            config: Configuration to save
            config_path: Path to save configuration
            create_backup: Whether to create backup of existing file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate configuration
            self.validate_config(config)

            # Create backup if requested and file exists
            if create_backup and config_path.exists():
                self.backup_config(config_path)

            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write configuration
            config_json = json.dumps(config, indent=2)
            config_path.write_text(config_json)

            return True

        except (OSError, PermissionError, ConfigValidationError):
            return False

    def get_config_path(
        self, use_global: bool = True, project_root: Path | None = None
    ) -> Path:
        """Get appropriate configuration file path.

        Args:
            use_global: Whether to use global configuration
            project_root: Project root directory for project-specific config

        Returns:
            Path to configuration file
        """
        if use_global:
            return self.platform_info.locations.get_global_path()
        else:
            project_path = self.platform_info.locations.get_project_path(project_root)
            if project_path is None:
                raise ValueError(
                    f"Platform {self.platform} does not support project-specific configuration"
                )
            return project_path

    def ensure_config_directory(self, config_path: Path) -> bool:
        """Ensure configuration directory exists.

        Args:
            config_path: Path to configuration file

        Returns:
            True if directory exists or was created successfully
        """
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            return True
        except (OSError, PermissionError):
            return False

    def list_existing_servers(self, config_path: Path | None = None) -> list[str]:
        """List existing MCP servers in configuration.

        Args:
            config_path: Optional path to configuration file

        Returns:
            List of server names
        """
        if config_path is None:
            config_path = self.get_config_path()

        if not config_path.exists():
            return []

        try:
            config = self.load_existing_config(config_path)
            return self._extract_server_names(config) if config else []
        except Exception:
            return []

    @abstractmethod
    def _extract_server_names(self, config: dict[str, Any]) -> list[str]:
        """Extract server names from platform-specific configuration.

        Args:
            config: Platform-specific configuration

        Returns:
            List of server names
        """
        pass

    def remove_server(self, server_name: str, config_path: Path) -> bool:
        """Remove a server from configuration.

        Args:
            server_name: Name of server to remove
            config_path: Path to configuration file

        Returns:
            True if successful

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If server not found or removal fails
        """
        # Load existing configuration
        config = self.load_config(config_path)

        # Get current servers
        servers = self.get_servers_from_config(config)

        if server_name not in servers:
            raise ValueError(f"Server '{server_name}' not found in configuration")

        # Remove the server
        del servers[server_name]

        # Create new configuration without the server
        new_config = self.create_config(servers)

        # Save updated configuration
        success = self.save_config(new_config, config_path)

        if not success:
            raise ValueError(f"Failed to save updated configuration to {config_path}")

        return True

    def configure_server(
        self, server_name: str, server_config: MCPServer, config_path: Path
    ) -> bool:
        """Configure an MCP server for the platform.

        Args:
            server_name: Name of the server to configure
            server_config: MCP server configuration
            config_path: Path to the configuration file

        Returns:
            True if configuration was successful

        Raises:
            ValueError: If server configuration is invalid
        """
        # Validate server configuration
        if not server_config.command:
            raise ValueError("Server command cannot be empty")

        # Load existing configuration
        existing_config = self.load_existing_config(config_path)
        if existing_config is None:
            existing_config = {}

        # Create new server configuration
        new_config = self.create_config({server_name: server_config})

        # Merge configurations
        merged_config = self.merge_configs(existing_config, new_config)

        # Save merged configuration
        success = self.save_config(merged_config, config_path)

        if not success:
            raise ValueError(f"Failed to save configuration to {config_path}")

        return True
