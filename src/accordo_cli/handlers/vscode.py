"""VS Code-specific configuration handler."""

import json
from pathlib import Path
from typing import Any

from ..models.config import MCPServer
from ..models.platform import PlatformInfo
from .base import BaseConfigHandler


class VSCodeHandler(BaseConfigHandler):
    """Configuration handler for VS Code with GitHub Copilot."""

    def __init__(self):
        """Initialize with VS Code platform information."""
        super().__init__(PlatformInfo.get_vscode_info())

    def create_config(self, servers: dict[str, MCPServer]) -> dict[str, Any]:
        """Create VS Code-specific configuration from MCP servers.

        Args:
            servers: Dictionary of MCP server configurations

        Returns:
            VS Code configuration dictionary with mcp.servers format
        """
        return {
            "mcp": {
                "servers": {name: server.to_dict() for name, server in servers.items()}
            }
        }

    def get_servers_from_config(self, config: dict[str, Any]) -> dict[str, MCPServer]:
        """Extract MCP servers from VS Code configuration.

        Args:
            config: VS Code configuration dictionary

        Returns:
            Dictionary of server name to MCPServer objects
        """
        servers = {}

        mcp_section = config.get("mcp", {})
        mcp_servers = mcp_section.get("servers", {})

        for server_name, server_config in mcp_servers.items():
            servers[server_name] = MCPServer(
                command=server_config.get("command", ""),
                args=server_config.get("args", []),
                env=server_config.get("env"),
            )

        return servers

    def load_existing_config(self, config_path: Path) -> dict[str, Any] | None:
        """Load existing VS Code configuration from settings.json file.

        Args:
            config_path: Path to settings.json file

        Returns:
            Existing configuration dictionary or None if not found/invalid
        """
        if not config_path.exists():
            return None

        try:
            content = config_path.read_text()
            if not content.strip():
                return {"mcp": {"servers": {}}}

            config = json.loads(content)

            # Ensure the config has the expected structure
            if not isinstance(config, dict):
                return {"mcp": {"servers": {}}}

            # Initialize mcp section if not present
            if "mcp" not in config or not isinstance(config["mcp"], dict):
                config["mcp"] = {"servers": {}}

            # Initialize servers section if not present
            if "servers" not in config["mcp"] or not isinstance(
                config["mcp"]["servers"], dict
            ):
                config["mcp"]["servers"] = {}

            return config

        except (json.JSONDecodeError, OSError):
            # Return empty config structure on error
            return {"mcp": {"servers": {}}}

    def merge_configs(
        self, existing: dict[str, Any], new: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge new configuration with existing VS Code configuration.

        Args:
            existing: Existing configuration
            new: New configuration to merge

        Returns:
            Merged configuration with new servers added/updated
        """
        # Create a copy of existing config
        merged = existing.copy()

        # Ensure existing config has mcp.servers structure
        if "mcp" not in merged:
            merged["mcp"] = {"servers": {}}
        elif "servers" not in merged["mcp"]:
            merged["mcp"]["servers"] = {}

        # Check if new config has mcp.servers structure
        if "mcp" not in new or "servers" not in new["mcp"]:
            return merged

        # Merge servers sections
        existing_servers = merged["mcp"]["servers"].copy()
        new_servers = new["mcp"]["servers"]

        # Update existing servers with new ones (new takes precedence)
        existing_servers.update(new_servers)
        merged["mcp"]["servers"] = existing_servers

        return merged

    def _extract_server_names(self, config: dict[str, Any]) -> list[str]:
        """Extract server names from VS Code configuration.

        Args:
            config: VS Code configuration dictionary

        Returns:
            List of MCP server names
        """
        if not config or "mcp" not in config:
            return []

        mcp_section = config["mcp"]
        if not isinstance(mcp_section, dict) or "servers" not in mcp_section:
            return []

        servers = mcp_section["servers"]
        if not isinstance(servers, dict):
            return []

        return list(servers.keys())

    def add_server(
        self,
        name: str,
        server: MCPServer,
        config_path: Path | None = None,
        use_global: bool = True,
    ) -> bool:
        """Add a new MCP server to VS Code configuration.

        Args:
            name: Server name
            server: MCP server configuration
            config_path: Optional specific config path
            use_global: Whether to use global configuration (default: True)

        Returns:
            True if server was added successfully
        """
        if config_path is None:
            config_path = self.get_config_path(use_global)

        # Load existing configuration
        existing_config = self.load_existing_config(config_path)
        if existing_config is None:
            existing_config = {"mcp": {"servers": {}}}

        # Create new server configuration
        new_config = self.create_config({name: server})

        # Merge configurations
        merged_config = self.merge_configs(existing_config, new_config)

        # Save merged configuration
        return self.save_config(merged_config, config_path)

    def remove_server(
        self, name: str, config_path: Path | None = None, use_global: bool = True
    ) -> bool:
        """Remove an MCP server from VS Code configuration.

        Args:
            name: Server name to remove
            config_path: Optional specific config path
            use_global: Whether to use global configuration (default: True)

        Returns:
            True if server was removed successfully
        """
        if config_path is None:
            config_path = self.get_config_path(use_global)

        # Load existing configuration
        existing_config = self.load_existing_config(config_path)
        if (
            existing_config is None
            or "mcp" not in existing_config
            or "servers" not in existing_config["mcp"]
        ):
            return False  # Nothing to remove

        servers = existing_config["mcp"]["servers"]
        if name not in servers:
            return False  # Server not found

        # Remove the server
        del servers[name]

        # Save updated configuration
        return self.save_config(existing_config, config_path)

    def validate_vscode_config(self, config: dict[str, Any]) -> bool:
        """Validate VS Code-specific configuration structure.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, raises ConfigValidationError if invalid
        """
        # Call base validation first
        self.validate_config(config)

        # VS Code-specific validation
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        if "mcp" in config:
            mcp_section = config["mcp"]
            if not isinstance(mcp_section, dict):
                raise ValueError("mcp section must be a dictionary")

            if "servers" in mcp_section:
                servers = mcp_section["servers"]
                if not isinstance(servers, dict):
                    raise ValueError("mcp.servers must be a dictionary")

                # Validate each server configuration
                for server_name, server_config in servers.items():
                    if not isinstance(server_config, dict):
                        raise ValueError(
                            f"Server '{server_name}' configuration must be a dictionary"
                        )

                    if "command" not in server_config:
                        raise ValueError(
                            f"Server '{server_name}' must have a 'command' field"
                        )

                    # Validate optional fields
                    if "args" in server_config and not isinstance(
                        server_config["args"], list
                    ):
                        raise ValueError(f"Server '{server_name}' args must be a list")

                    if "env" in server_config and not isinstance(
                        server_config["env"], dict
                    ):
                        raise ValueError(
                            f"Server '{server_name}' env must be a dictionary"
                        )

                    # VS Code supports both stdio and sse transports
                    if "url" in server_config:
                        # Network transports are supported but less common
                        pass

        return True

    def merge_with_existing_settings(
        self, mcp_config: dict[str, Any], existing_settings: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge MCP configuration with existing VS Code settings.

        This is useful when working with settings.json files that contain
        other VS Code settings beyond MCP configuration.

        Args:
            mcp_config: MCP configuration to add
            existing_settings: Existing VS Code settings

        Returns:
            Merged settings with MCP configuration added
        """
        merged_settings = existing_settings.copy()

        # Merge the MCP section
        if "mcp" in mcp_config:
            if "mcp" not in merged_settings:
                merged_settings["mcp"] = {}

            # Merge mcp.servers
            if "servers" in mcp_config["mcp"]:
                if "servers" not in merged_settings["mcp"]:
                    merged_settings["mcp"]["servers"] = {}

                merged_settings["mcp"]["servers"].update(mcp_config["mcp"]["servers"])

        return merged_settings
