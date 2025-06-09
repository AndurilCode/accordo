"""Cursor-specific configuration handler."""

import json
from pathlib import Path
from typing import Any

from ..models.config import MCPServer
from ..models.platform import Platform, PlatformInfo
from .base import BaseConfigHandler


class CursorHandler(BaseConfigHandler):
    """Configuration handler for Cursor IDE."""

    def __init__(self):
        """Initialize with Cursor platform information."""
        platform_info = PlatformInfo.get_all_platforms()[Platform.CURSOR]
        super().__init__(platform_info)

    def create_config(self, servers: dict[str, MCPServer]) -> dict[str, Any]:
        """Create Cursor-specific configuration from MCP servers.

        Args:
            servers: Dictionary of MCP server configurations

        Returns:
            Cursor-specific configuration dictionary with mcpServers format
        """
        mcp_servers = {}

        for server_name, server_config in servers.items():
            mcp_servers[server_name] = {
                "command": server_config.command,
                "args": server_config.args or [],
            }

            # Add environment variables if present
            if server_config.env:
                mcp_servers[server_name]["env"] = server_config.env

        return {"mcpServers": mcp_servers}

    def get_servers_from_config(self, config: dict[str, Any]) -> dict[str, MCPServer]:
        """Extract MCP servers from Cursor configuration.

        Args:
            config: Cursor configuration dictionary

        Returns:
            Dictionary of server name to MCPServer objects
        """
        servers = {}

        mcp_servers = config.get("mcpServers", {})
        for server_name, server_config in mcp_servers.items():
            servers[server_name] = MCPServer(
                command=server_config.get("command", ""),
                args=server_config.get("args", []),
                env=server_config.get("env"),
            )

        return servers

    def load_existing_config(self, config_path: Path) -> dict[str, Any] | None:
        """Load existing Cursor configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            Existing configuration dictionary or None if not found
        """
        if not config_path.exists():
            return None

        try:
            content = config_path.read_text()
            return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return None

    def merge_configs(
        self, existing: dict[str, Any], new: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge new configuration with existing Cursor configuration.

        Args:
            existing: Existing configuration
            new: New configuration to merge

        Returns:
            Merged configuration
        """
        # Start with existing configuration
        merged = existing.copy()

        # Ensure mcpServers section exists
        if "mcpServers" not in merged:
            merged["mcpServers"] = {}

        # Merge new servers
        if "mcpServers" in new:
            merged["mcpServers"].update(new["mcpServers"])

        return merged

    def _extract_server_names(self, config: dict[str, Any]) -> list[str]:
        """Extract server names from Cursor configuration.

        Args:
            config: Cursor configuration

        Returns:
            List of server names
        """
        mcp_servers = config.get("mcpServers", {})
        return list(mcp_servers.keys())

    def add_server(
        self,
        name: str,
        server: MCPServer,
        config_path: Path | None = None,
        use_global: bool = True,
    ) -> bool:
        """Add a new MCP server to Cursor configuration.

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
            existing_config = {"mcpServers": {}}

        # Create new server configuration
        new_config = self.create_config({name: server})

        # Merge configurations
        merged_config = self.merge_configs(existing_config, new_config)

        # Save merged configuration
        return self.save_config(merged_config, config_path)

    def remove_server(
        self, name: str, config_path: Path | None = None, use_global: bool = True
    ) -> bool:
        """Remove an MCP server from Cursor configuration.

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
        if existing_config is None or "mcpServers" not in existing_config:
            return False  # Nothing to remove

        mcp_servers = existing_config["mcpServers"]
        if name not in mcp_servers:
            return False  # Server not found

        # Remove the server
        del mcp_servers[name]

        # Save updated configuration
        return self.save_config(existing_config, config_path)

    def validate_cursor_config(self, config: dict[str, Any]) -> bool:
        """Validate Cursor-specific configuration structure.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, raises ConfigValidationError if invalid
        """
        # Call base validation first
        self.validate_config(config)

        # Cursor-specific validation
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        if "mcpServers" in config:
            mcp_servers = config["mcpServers"]
            if not isinstance(mcp_servers, dict):
                raise ValueError("mcpServers must be a dictionary")

            # Validate each server configuration
            for server_name, server_config in mcp_servers.items():
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
                    raise ValueError(f"Server '{server_name}' env must be a dictionary")

        return True
