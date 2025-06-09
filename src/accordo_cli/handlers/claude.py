"""Claude Desktop-specific configuration handler."""

import json
from pathlib import Path
from typing import Any

from ..models.config import MCPServer
from ..models.platform import Platform, PlatformInfo
from .base import BaseConfigHandler


class ClaudeDesktopHandler(BaseConfigHandler):
    """Handler for Claude Desktop MCP configuration."""

    def __init__(self, platform_info: PlatformInfo | None = None):
        """Initialize Claude Desktop handler."""
        if platform_info is None:
            platform_info = PlatformInfo.for_platform(Platform.CLAUDE_DESKTOP)
        super().__init__(platform_info)

    def create_config(self, servers: dict[str, MCPServer]) -> dict[str, Any]:
        """Create Claude Desktop-specific configuration from MCP servers.

        Args:
            servers: Dictionary mapping server names to MCPServer objects

        Returns:
            Dictionary in Claude Desktop configuration format
        """
        return {
            "mcpServers": {name: server.to_dict() for name, server in servers.items()}
        }

    def get_servers_from_config(self, config: dict[str, Any]) -> dict[str, MCPServer]:
        """Extract MCP servers from Claude Desktop configuration.

        Args:
            config: Claude Desktop configuration dictionary

        Returns:
            Dictionary mapping server names to MCPServer objects
        """
        servers = {}
        mcp_servers = config.get("mcpServers", {})

        for name, server_config in mcp_servers.items():
            if isinstance(server_config, dict):
                servers[name] = MCPServer(**server_config)

        return servers

    def load_existing_config(self, config_path: Path) -> dict[str, Any] | None:
        """Load existing Claude Desktop configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary or None if file doesn't exist
        """
        try:
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    return json.load(f)
            return {"mcpServers": {}}
        except (OSError, json.JSONDecodeError):
            return {"mcpServers": {}}

    def merge_configs(
        self, existing: dict[str, Any], new: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge new configuration with existing Claude Desktop configuration.

        Args:
            existing: Existing configuration
            new: New configuration to merge

        Returns:
            Merged configuration
        """
        merged = existing.copy()

        # Initialize mcpServers if it doesn't exist
        if "mcpServers" not in merged:
            merged["mcpServers"] = {}

        # Merge new servers
        if "mcpServers" in new:
            merged["mcpServers"].update(new["mcpServers"])

        return merged

    def _extract_server_names(self, config: dict[str, Any]) -> list[str]:
        """Extract server names from Claude Desktop configuration.

        Args:
            config: Configuration dictionary

        Returns:
            List of server names
        """
        mcp_servers = config.get("mcpServers", {})
        return list(mcp_servers.keys())

    def add_server(
        self, name: str, server: MCPServer, config_path: Path | None = None
    ) -> bool:
        """Add a new MCP server to Claude Desktop configuration.

        Args:
            name: Server name
            server: MCPServer configuration
            config_path: Optional custom config path

        Returns:
            True if successful, False otherwise
        """
        if config_path is None:
            config_path = self.get_config_path(use_global=True)

        existing_config = self.load_existing_config(config_path) or {"mcpServers": {}}
        new_config = self.create_config({name: server})
        merged_config = self.merge_configs(existing_config, new_config)

        return self.save_config(merged_config, config_path)

    def remove_server(self, name: str, config_path: Path | None = None) -> bool:
        """Remove an MCP server from Claude Desktop configuration.

        Args:
            name: Server name to remove
            config_path: Optional custom config path

        Returns:
            True if successful, False otherwise
        """
        if config_path is None:
            config_path = self.get_config_path(use_global=True)

        existing_config = self.load_existing_config(config_path)
        if not existing_config or "mcpServers" not in existing_config:
            return False

        if name in existing_config["mcpServers"]:
            del existing_config["mcpServers"][name]

        return self.save_config(existing_config, config_path)

    def validate_claude_config(self, config: dict[str, Any]) -> bool:
        """Validate Claude Desktop-specific configuration structure.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(config, dict):
            return False

        # Check for required mcpServers key
        if "mcpServers" not in config:
            return False

        mcp_servers = config["mcpServers"]
        if not isinstance(mcp_servers, dict):
            return False

        # Validate each server configuration
        for _server_name, server_config in mcp_servers.items():
            if not isinstance(server_config, dict):
                return False

            if "command" not in server_config:
                return False

        return True


# Keep backward compatibility alias
ClaudeHandler = ClaudeDesktopHandler


class ClaudeCodeHandler(BaseConfigHandler):
    """Handler for Claude Code MCP configuration (.mcp.json files)."""

    def __init__(self, platform_info: PlatformInfo | None = None):
        """Initialize Claude Code handler."""
        if platform_info is None:
            platform_info = PlatformInfo.for_platform(Platform.CLAUDE_CODE)
        super().__init__(platform_info)

    def create_config(self, servers: dict[str, MCPServer]) -> dict[str, Any]:
        """Create Claude Code-specific configuration from MCP servers.

        Args:
            servers: Dictionary mapping server names to MCPServer objects

        Returns:
            Dictionary in Claude Code configuration format (.mcp.json)
        """
        return {
            "mcpServers": {name: server.to_dict() for name, server in servers.items()}
        }

    def get_servers_from_config(self, config: dict[str, Any]) -> dict[str, MCPServer]:
        """Extract MCP servers from Claude Code configuration.

        Args:
            config: Claude Code configuration dictionary

        Returns:
            Dictionary mapping server names to MCPServer objects
        """
        servers = {}
        mcp_servers = config.get("mcpServers", {})

        for name, server_config in mcp_servers.items():
            if isinstance(server_config, dict):
                servers[name] = MCPServer(**server_config)

        return servers

    def load_existing_config(self, config_path: Path) -> dict[str, Any] | None:
        """Load existing Claude Code configuration from .mcp.json file.

        Args:
            config_path: Path to .mcp.json file

        Returns:
            Configuration dictionary or None if file doesn't exist
        """
        try:
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    return json.load(f)
            return {"mcpServers": {}}
        except (OSError, json.JSONDecodeError):
            return {"mcpServers": {}}

    def merge_configs(
        self, existing: dict[str, Any], new: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge new configuration with existing Claude Code configuration.

        Args:
            existing: Existing configuration
            new: New configuration to merge

        Returns:
            Merged configuration
        """
        merged = existing.copy()

        # Initialize mcpServers if it doesn't exist
        if "mcpServers" not in merged:
            merged["mcpServers"] = {}

        # Merge new servers
        if "mcpServers" in new:
            merged["mcpServers"].update(new["mcpServers"])

        return merged

    def _extract_server_names(self, config: dict[str, Any]) -> list[str]:
        """Extract server names from Claude Code configuration.

        Args:
            config: Configuration dictionary

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
        use_global: bool = False,
    ) -> bool:
        """Add a new MCP server to Claude Code configuration.

        Args:
            name: Server name
            server: MCPServer configuration
            config_path: Optional custom config path
            use_global: Whether to use global config (default: False, use project config)

        Returns:
            True if successful, False otherwise
        """
        if config_path is None:
            config_path = self.get_config_path(use_global=use_global)

        existing_config = self.load_existing_config(config_path) or {"mcpServers": {}}
        new_config = self.create_config({name: server})
        merged_config = self.merge_configs(existing_config, new_config)

        return self.save_config(merged_config, config_path)

    def remove_server(
        self, name: str, config_path: Path | None = None, use_global: bool = False
    ) -> bool:
        """Remove an MCP server from Claude Code configuration.

        Args:
            name: Server name to remove
            config_path: Optional custom config path
            use_global: Whether to use global config (default: False, use project config)

        Returns:
            True if successful, False otherwise
        """
        if config_path is None:
            config_path = self.get_config_path(use_global=use_global)

        existing_config = self.load_existing_config(config_path)
        if not existing_config or "mcpServers" not in existing_config:
            return False

        if name in existing_config["mcpServers"]:
            del existing_config["mcpServers"][name]

        return self.save_config(existing_config, config_path)

    def validate_claude_code_config(self, config: dict[str, Any]) -> bool:
        """Validate Claude Code-specific configuration structure.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(config, dict):
            return False

        # Check for required mcpServers key
        if "mcpServers" not in config:
            return False

        mcp_servers = config["mcpServers"]
        if not isinstance(mcp_servers, dict):
            return False

        # Validate each server configuration
        for _server_name, server_config in mcp_servers.items():
            if not isinstance(server_config, dict):
                return False

            if "command" not in server_config:
                return False

        return True
