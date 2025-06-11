"""Pydantic models for MCP server configurations."""

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConfigurationTemplate(str, Enum):
    """Available configuration templates for MCP server setup."""

    BASIC = "basic"
    ADVANCED = "advanced"
    CACHE_ENABLED = "cache_enabled"


class TemplateConfig(BaseModel):
    """Configuration template with predefined arguments."""

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    args: list[str] = Field(
        default_factory=list, description="Default arguments for this template"
    )

    @classmethod
    def get_basic_template(cls) -> "TemplateConfig":
        """Get basic configuration template with minimal options."""
        return cls(
            name="Basic Setup",
            description="Minimal configuration for getting started",
            args=[
                "accordo-workflow-mcp",
            ],
        )

    @classmethod
    def get_advanced_template(cls) -> "TemplateConfig":
        """Get advanced configuration template with comprehensive options."""
        return cls(
            name="Advanced Setup",
            description="Configuration with comprehensive command line options including cache features",
            args=[
                "accordo-workflow-mcp",
                "--local",
                "--enable-local-state-file",
                "--local-state-file-format",
                "JSON",
                "--session-retention-hours",
                "72",
                "--enable-cache-mode",
                "--cache-embedding-model",
                "all-MiniLM-L6-v2",
                "--cache-db-path",
                ".accordo/cache",
                "--cache-max-results",
                "50",
            ],
        )

    @classmethod
    def get_cache_enabled_template(cls) -> "TemplateConfig":
        """Get cache-enabled configuration template."""
        return cls(
            name="Cache-Enabled Setup",
            description="Focused configuration highlighting cache features for semantic workflow analysis",
            args=[
                "accordo-workflow-mcp",
                "--local",
                "--enable-local-state-file",
                "--local-state-file-format",
                "JSON",
                "--enable-cache-mode",
                "--cache-embedding-model",
                "all-MiniLM-L6-v2",
            ],
        )

    @classmethod
    def get_template(cls, template: ConfigurationTemplate) -> "TemplateConfig":
        """Get template configuration by enum value."""
        if template == ConfigurationTemplate.BASIC:
            return cls.get_basic_template()
        elif template == ConfigurationTemplate.ADVANCED:
            return cls.get_advanced_template()
        elif template == ConfigurationTemplate.CACHE_ENABLED:
            return cls.get_cache_enabled_template()
        else:
            raise ValueError(f"Unknown template: {template}")


class ConfigurationOption(BaseModel):
    """Individual configuration option for building custom configurations."""

    flag: str = Field(..., description="Command line flag")
    value: str | None = Field(default=None, description="Optional value for the flag")
    description: str = Field(..., description="Description of what this option does")
    requires_value: bool = Field(
        default=False, description="Whether this flag requires a value"
    )

    def to_args(self) -> list[str]:
        """Convert this option to command line arguments."""
        if self.requires_value and self.value:
            return [self.flag, self.value]
        elif not self.requires_value:
            return [self.flag]
        else:
            return []


class MCPServer(BaseModel):
    """Model representing an MCP server configuration."""

    command: str = Field(..., description="Command to run the MCP server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] | None = Field(
        default=None, description="Environment variables"
    )
    url: str | None = Field(
        default=None, description="Server URL for network transport"
    )

    @field_validator("command")
    @classmethod
    def command_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format suitable for JSON serialization."""
        data = {"command": self.command}
        if self.args:
            data["args"] = self.args
        if self.env:
            data["env"] = self.env
        if self.url:
            data["url"] = self.url
        return data


class ConfigurationBuilder:
    """Builder class for constructing MCP server configurations."""

    def __init__(self, base_template: ConfigurationTemplate | None = None):
        """Initialize builder with optional base template."""
        self.command = "uvx"
        self.base_args = [
            "accordo-workflow-mcp",
        ]
        self.options: list[ConfigurationOption] = []

        if base_template:
            template_config = TemplateConfig.get_template(base_template)
            # Extract additional options from template (skip the base uvx command)
            template_args = template_config.args[1:]  # Skip "accordo-workflow-mcp"
            self._parse_template_args(template_args)

    def _parse_template_args(self, args: list[str]) -> None:
        """Parse template arguments into configuration options."""
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                # Check if next arg is a value (doesn't start with --)
                if i + 1 < len(args) and not args[i + 1].startswith("--"):
                    self.options.append(
                        ConfigurationOption(
                            flag=arg,
                            value=args[i + 1],
                            description=f"Template option: {arg}",
                            requires_value=True,
                        )
                    )
                    i += 2
                else:
                    self.options.append(
                        ConfigurationOption(
                            flag=arg,
                            description=f"Template option: {arg}",
                            requires_value=False,
                        )
                    )
                    i += 1
            else:
                i += 1

    def add_global_flag(self) -> "ConfigurationBuilder":
        """Add --global flag for home directory repository root."""
        self._update_or_add_option(
            "--global", None, "Use home directory as repository root", False
        )
        return self

    def add_local_flag(self) -> "ConfigurationBuilder":
        """Add --local flag for current directory repository root."""
        self._update_or_add_option(
            "--local", None, "Use current directory as repository root", False
        )
        return self

    def add_repository_path(self, path: str = ".") -> "ConfigurationBuilder":
        """[DEPRECATED] Add repository path option. Use add_global_flag() or add_local_flag() instead."""
        self._update_or_add_option(
            "--repository-path", path, "[DEPRECATED] Repository root path"
        )
        return self

    def enable_local_state_file(
        self, format_type: str = "JSON"
    ) -> "ConfigurationBuilder":
        """Enable local state file with optional format."""
        self._update_or_add_option(
            "--enable-local-state-file", None, "Enable local state file storage", False
        )
        self._update_or_add_option(
            "--local-state-file-format", format_type, "Local state file format"
        )
        return self

    def set_session_retention(self, hours: int = 72) -> "ConfigurationBuilder":
        """Set session retention hours."""
        self._update_or_add_option(
            "--session-retention-hours", str(hours), "Session retention period"
        )
        return self

    def enable_cache_mode(
        self, embedding_model: str = "all-MiniLM-L6-v2"
    ) -> "ConfigurationBuilder":
        """Enable cache mode with embedding model."""
        self._update_or_add_option(
            "--enable-cache-mode", None, "Enable ChromaDB caching", False
        )
        self._update_or_add_option(
            "--cache-embedding-model", embedding_model, "Semantic embedding model"
        )
        return self

    def set_cache_path(self, path: str = ".accordo/cache") -> "ConfigurationBuilder":
        """Set cache database path."""
        self._update_or_add_option("--cache-db-path", path, "Cache database path")
        return self

    def set_cache_max_results(self, max_results: int = 50) -> "ConfigurationBuilder":
        """Set maximum cache search results."""
        self._update_or_add_option(
            "--cache-max-results", str(max_results), "Maximum search results"
        )
        return self

    def add_custom_option(
        self, flag: str, value: str | None = None, description: str = "Custom option"
    ) -> "ConfigurationBuilder":
        """Add a custom configuration option."""
        self._update_or_add_option(flag, value, description, value is not None)
        return self

    def _update_or_add_option(
        self,
        flag: str,
        value: str | None,
        description: str,
        requires_value: bool = True,
    ) -> None:
        """Update existing option or add new one."""
        # Remove existing option with same flag
        self.options = [opt for opt in self.options if opt.flag != flag]

        # Add new option
        self.options.append(
            ConfigurationOption(
                flag=flag,
                value=value,
                description=description,
                requires_value=requires_value,
            )
        )

    def build(self) -> MCPServer:
        """Build the final MCPServer configuration."""
        args = self.base_args.copy()

        # Add all options
        for option in self.options:
            args.extend(option.to_args())

        return MCPServer(command=self.command, args=args)

    def get_args_preview(self) -> list[str]:
        """Get preview of final arguments without building MCPServer."""
        args = self.base_args.copy()
        for option in self.options:
            args.extend(option.to_args())
        return args


class MCPServerConfig(BaseModel):
    """Base configuration for MCP servers."""

    servers: dict[str, MCPServer] = Field(default_factory=dict)

    def add_server(self, name: str, server: MCPServer) -> None:
        """Add a new MCP server to the configuration."""
        self.servers[name] = server

    def remove_server(self, name: str) -> bool:
        """Remove an MCP server from the configuration."""
        if name in self.servers:
            del self.servers[name]
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        return {name: server.to_dict() for name, server in self.servers.items()}


class CursorConfig(BaseModel):
    """Cursor-specific MCP configuration."""

    mcpServers: dict[str, MCPServer] = Field(default_factory=dict)  # noqa: N815

    @classmethod
    def from_base_config(cls, base_config: MCPServerConfig) -> "CursorConfig":
        """Create Cursor config from base configuration."""
        return cls(mcpServers=base_config.servers)

    def add_server(self, name: str, server: MCPServer) -> None:
        """Add a new MCP server to the configuration."""
        self.mcpServers[name] = server

    def to_dict(self) -> dict[str, Any]:
        """Convert to Cursor configuration format."""
        return {
            "mcpServers": {
                name: server.to_dict() for name, server in self.mcpServers.items()
            }
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class ClaudeConfig(BaseModel):
    """Claude Desktop-specific MCP configuration."""

    mcpServers: dict[str, MCPServer] = Field(default_factory=dict)  # noqa: N815

    @classmethod
    def from_base_config(cls, base_config: MCPServerConfig) -> "ClaudeConfig":
        """Create Claude config from base configuration."""
        return cls(mcpServers=base_config.servers)

    def add_server(self, name: str, server: MCPServer) -> None:
        """Add a new MCP server to the configuration."""
        self.mcpServers[name] = server

    def to_dict(self) -> dict[str, Any]:
        """Convert to Claude Desktop configuration format."""
        return {
            "mcpServers": {
                name: server.to_dict() for name, server in self.mcpServers.items()
            }
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class VSCodeConfig(BaseModel):
    """VS Code-specific MCP configuration."""

    mcp: dict[str, dict[str, dict[str, MCPServer]]] = Field(
        default_factory=lambda: {"servers": {}}
    )

    @classmethod
    def from_base_config(cls, base_config: MCPServerConfig) -> "VSCodeConfig":
        """Create VS Code config from base configuration."""
        return cls(mcp={"servers": base_config.servers})

    def add_server(self, name: str, server: MCPServer) -> None:
        """Add a new MCP server to the configuration."""
        if "servers" not in self.mcp:
            self.mcp["servers"] = {}
        self.mcp["servers"][name] = server

    def to_dict(self) -> dict[str, Any]:
        """Convert to VS Code configuration format."""
        if "servers" in self.mcp:
            servers_dict = {
                name: server.to_dict() for name, server in self.mcp["servers"].items()
            }
            return {"mcp": {"servers": servers_dict}}
        return {"mcp": {"servers": {}}}

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
