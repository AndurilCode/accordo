"""Pydantic models for MCP server configurations."""

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MCPServer(BaseModel):
    """Model representing an MCP server configuration."""
    
    command: str = Field(..., description="Command to run the MCP server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] | None = Field(default=None, description="Environment variables")
    url: str | None = Field(default=None, description="Server URL for network transport")
    
    @field_validator('command')
    @classmethod
    def command_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Command cannot be empty')
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
    
    mcpServers: dict[str, MCPServer] = Field(default_factory=dict)
    
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
            "mcpServers": {name: server.to_dict() for name, server in self.mcpServers.items()}
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class ClaudeConfig(BaseModel):
    """Claude Desktop-specific MCP configuration."""
    
    mcpServers: dict[str, MCPServer] = Field(default_factory=dict)
    
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
            "mcpServers": {name: server.to_dict() for name, server in self.mcpServers.items()}
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class VSCodeConfig(BaseModel):
    """VS Code-specific MCP configuration."""
    
    mcp: dict[str, dict[str, dict[str, MCPServer]]] = Field(default_factory=lambda: {"servers": {}})
    
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
            servers_dict = {name: server.to_dict() for name, server in self.mcp["servers"].items()}
            return {"mcp": {"servers": servers_dict}}
        return {"mcp": {"servers": {}}}
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent) 