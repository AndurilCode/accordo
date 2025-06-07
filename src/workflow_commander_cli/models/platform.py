"""Platform-specific models and enums."""

import os
import platform
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Supported AI platforms."""

    CURSOR = "cursor"
    CLAUDE_DESKTOP = "claude-desktop"
    CLAUDE_CODE = "claude-code"
    VSCODE = "vscode"


class ConfigLocation(BaseModel):
    """Configuration file location information."""

    global_path: Path = Field(..., description="Global configuration file path")
    project_path: Path | None = Field(
        default=None, description="Project-specific configuration path"
    )
    description: str = Field(
        ..., description="Human-readable description of the location"
    )

    def get_global_path(self) -> Path:
        """Get the expanded global configuration path."""
        return Path(os.path.expanduser(str(self.global_path)))

    def get_project_path(self, project_root: Path | None = None) -> Path | None:
        """Get the project configuration path relative to project root."""
        if self.project_path is None:
            return None

        if project_root is None:
            project_root = Path.cwd()

        return project_root / self.project_path

    def ensure_directories(self) -> bool:
        """Ensure that the configuration directories exist."""
        try:
            # Ensure global config directory exists
            global_path = self.get_global_path()
            global_path.parent.mkdir(parents=True, exist_ok=True)

            return True
        except (OSError, PermissionError):
            return False


class PlatformInfo(BaseModel):
    """Information about a specific AI platform."""

    name: str = Field(..., description="Platform display name")
    platform: Platform = Field(..., description="Platform enum value")
    description: str = Field(..., description="Platform description")
    config_format: str = Field(
        ..., description="Configuration format (e.g., 'mcpServers' or 'mcp.servers')"
    )
    locations: ConfigLocation = Field(..., description="Configuration file locations")
    supported_transports: list[str] = Field(
        default_factory=list, description="Supported MCP transport types"
    )
    documentation_url: str | None = Field(
        default=None, description="Link to platform documentation"
    )

    @classmethod
    def get_cursor_info(cls) -> "PlatformInfo":
        """Get platform information for Cursor."""
        system = platform.system().lower()

        if system == "windows":
            global_path = Path("~/AppData/Roaming/Cursor/User/mcp.json")
        elif system == "darwin":  # macOS
            global_path = Path("~/Library/Application Support/Cursor/User/mcp.json")
        else:  # Linux and others
            global_path = Path("~/.config/Cursor/User/mcp.json")

        return cls(
            name="Cursor",
            platform=Platform.CURSOR,
            description="Modern AI-powered code editor with built-in AI assistance",
            config_format="mcpServers",
            locations=ConfigLocation(
                global_path=global_path,
                project_path=Path(".cursor/mcp.json"),
                description="User settings directory or project .cursor folder",
            ),
            supported_transports=["stdio", "sse", "streamable-http"],
            documentation_url="https://docs.cursor.com/advanced/mcp",
        )

    @classmethod
    def get_claude_info(cls) -> "PlatformInfo":
        """Get platform information for Claude Desktop."""
        system = platform.system().lower()

        if system == "windows":
            global_path = Path("~/AppData/Roaming/Claude/claude_desktop_config.json")
        elif system == "darwin":  # macOS
            global_path = Path(
                "~/Library/Application Support/Claude/claude_desktop_config.json"
            )
        else:  # Linux and others
            global_path = Path("~/.config/Claude/claude_desktop_config.json")

        return cls(
            name="Claude Desktop",
            platform=Platform.CLAUDE_DESKTOP,
            description="Anthropic's desktop application for Claude AI",
            config_format="mcpServers",
            locations=ConfigLocation(
                global_path=global_path,
                project_path=None,  # Claude Desktop doesn't support project configs
                description="Application support directory",
            ),
            supported_transports=["stdio"],
            documentation_url="https://modelcontextprotocol.io/quickstart/user",
        )

    @classmethod
    def get_claude_code_info(cls) -> "PlatformInfo":
        """Get platform information for Claude Code."""
        # Claude Code uses .mcp.json files in project directories
        # Global configuration is not typically used for Claude Code
        return cls(
            name="Claude Code",
            platform=Platform.CLAUDE_CODE,
            description="Anthropic's command-line coding assistant",
            config_format="mcpServers",
            locations=ConfigLocation(
                global_path=Path("~/.mcp.json"),  # Global fallback, though rarely used
                project_path=Path(".mcp.json"),  # Primary location for Claude Code
                description="Project root directory or user home directory",
            ),
            supported_transports=["stdio"],
            documentation_url="https://docs.anthropic.com/en/docs/claude-code/tutorials#set-up-model-context-protocol-mcp",
        )

    @classmethod
    def get_vscode_info(cls) -> "PlatformInfo":
        """Get platform information for VS Code."""
        system = platform.system().lower()

        if system == "windows":
            global_path = Path("~/AppData/Roaming/Code/User/settings.json")
        elif system == "darwin":  # macOS
            global_path = Path("~/Library/Application Support/Code/User/settings.json")
        else:  # Linux and others
            global_path = Path("~/.config/Code/User/settings.json")

        return cls(
            name="VS Code",
            platform=Platform.VSCODE,
            description="Visual Studio Code with GitHub Copilot integration",
            config_format="mcp.servers",
            locations=ConfigLocation(
                global_path=global_path,
                project_path=Path(".vscode/settings.json"),
                description="User settings or workspace .vscode folder",
            ),
            supported_transports=["stdio", "sse"],
            documentation_url="https://code.visualstudio.com/docs",
        )

    @classmethod
    def get_all_platforms(cls) -> dict[Platform, "PlatformInfo"]:
        """Get information for all supported platforms."""
        return {
            Platform.CURSOR: cls.get_cursor_info(),
            Platform.CLAUDE_DESKTOP: cls.get_claude_info(),
            Platform.CLAUDE_CODE: cls.get_claude_code_info(),
            Platform.VSCODE: cls.get_vscode_info(),
        }

    @classmethod
    def for_platform(cls, platform: Platform) -> "PlatformInfo":
        """Get platform information for a specific platform.

        Args:
            platform: The platform enum value

        Returns:
            PlatformInfo for the specified platform

        Raises:
            ValueError: If platform is not supported
        """
        platform_map = cls.get_all_platforms()
        if platform not in platform_map:
            raise ValueError(f"Unsupported platform: {platform}")
        return platform_map[platform]
