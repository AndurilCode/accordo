"""Tests for CLI commands."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from accordo_cli.main import app
from accordo_cli.models.config import MCPServer


class TestCliCommands:
    """Test suite for CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.test_config_dir = Path("/tmp/test_workflow_commander")
        self.test_config_dir.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_config_dir.exists():
            import shutil

            shutil.rmtree(self.test_config_dir)

    def test_version_command(self):
        """Test version command."""
        result = self.runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "accordo CLI v0.1.0" in result.stdout

    def test_help_command(self):
        """Test help command."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Configure MCP servers for AI coding platforms" in result.stdout
        assert "configure" in result.stdout
        assert "list-platforms" in result.stdout
        assert "list-servers" in result.stdout
        assert "remove-server" in result.stdout
        assert "validate" in result.stdout

    def test_list_platforms_command(self):
        """Test list-platforms command."""
        result = self.runner.invoke(app, ["list-platforms"])
        assert result.exit_code == 0
        assert "Supported AI Coding Platforms" in result.stdout
        assert "Cursor" in result.stdout
        assert "Claude Desktop" in result.stdout
        assert "VS Code" in result.stdout

    @patch("typer.prompt")
    @patch("typer.confirm")
    def test_configure_command_interactive(self, mock_confirm, mock_prompt):
        """Test configure command in interactive mode."""
        # Mock user inputs in sequence
        mock_prompt.side_effect = ["1", "1"]  # Platform choice, server choice
        mock_confirm.side_effect = [True, True, True]  # Various confirmation prompts

        # Use a specific config path
        config_file = self.test_config_dir / "mcp.json"

        result = self.runner.invoke(app, ["configure", "--config", str(config_file)])

        # Should succeed and create configuration
        assert result.exit_code == 0
        assert "Configuration Summary" in result.stdout

        # Check that config file was created
        assert config_file.exists()

        # Verify config content
        config = json.loads(config_file.read_text())
        assert "mcpServers" in config
        assert "accordo" in config["mcpServers"]

    def test_configure_command_non_interactive(self):
        """Test configure command in non-interactive mode."""
        config_file = self.test_config_dir / "cursor_mcp.json"

        result = self.runner.invoke(
            app,
            [
                "configure",
                "--platform",
                "cursor",
                "--server",
                "test-server",
                "--config",
                str(config_file),
                "--non-interactive",
            ],
        )

        # Should succeed
        assert result.exit_code == 0

        # Check that config file was created
        assert config_file.exists()

        # Verify config content
        config = json.loads(config_file.read_text())
        assert "mcpServers" in config
        assert "test-server" in config["mcpServers"]

    def test_configure_command_invalid_platform(self):
        """Test configure command with invalid platform."""
        result = self.runner.invoke(
            app, ["configure", "--platform", "invalid", "--non-interactive"]
        )

        assert result.exit_code == 1
        assert "Invalid platform: invalid" in result.stdout

    def test_list_servers_command_with_config(self):
        """Test list-servers command with existing configuration."""
        # Create test configuration
        config_file = self.test_config_dir / "mcp.json"
        test_config = {
            "mcpServers": {
                "accordo": {
                    "command": "uvx",
                    "args": [
                        
                        "accordo-workflow-mcp",
                        "accordo-mcp",
                    ],
                },
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "secret"},
                },
            }
        }
        config_file.write_text(json.dumps(test_config, indent=2))

        result = self.runner.invoke(
            app, ["list-servers", "--platform", "cursor", "--config", str(config_file)]
        )

        assert result.exit_code == 0
        assert "MCP Servers in Cursor" in result.stdout
        assert "accordo" in result.stdout
        assert "github" in result.stdout
        assert "Environment: 1 variables" in result.stdout

    def test_list_servers_command_no_config(self):
        """Test list-servers command with no configuration file."""
        config_file = self.test_config_dir / "nonexistent.json"

        result = self.runner.invoke(
            app, ["list-servers", "--platform", "cursor", "--config", str(config_file)]
        )

        assert result.exit_code == 1
        assert "Configuration file not found" in result.stdout

    def test_list_servers_command_empty_config(self):
        """Test list-servers command with empty configuration."""
        config_file = self.test_config_dir / "empty.json"
        config_file.write_text(json.dumps({"mcpServers": {}}, indent=2))

        result = self.runner.invoke(
            app, ["list-servers", "--platform", "cursor", "--config", str(config_file)]
        )

        assert result.exit_code == 0
        assert "No MCP servers configured" in result.stdout

    def test_remove_server_command(self):
        """Test remove-server command."""
        # Create test configuration
        config_file = self.test_config_dir / "mcp.json"
        test_config = {
            "mcpServers": {
                "accordo": {
                    "command": "uvx",
                    "args": [
                        
                        "accordo-workflow-mcp",
                        "accordo-mcp",
                    ],
                },
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                },
            }
        }
        config_file.write_text(json.dumps(test_config, indent=2))

        result = self.runner.invoke(
            app,
            [
                "remove-server",
                "github",
                "--platform",
                "cursor",
                "--config",
                str(config_file),
                "--force",
            ],
        )

        assert result.exit_code == 0
        assert "Server 'github' removed successfully" in result.stdout

        # Verify server was removed
        updated_config = json.loads(config_file.read_text())
        assert "github" not in updated_config["mcpServers"]
        assert "accordo" in updated_config["mcpServers"]

    def test_remove_server_command_not_found(self):
        """Test remove-server command with non-existent server."""
        config_file = self.test_config_dir / "mcp.json"
        test_config = {"mcpServers": {}}
        config_file.write_text(json.dumps(test_config, indent=2))

        result = self.runner.invoke(
            app,
            [
                "remove-server",
                "nonexistent",
                "--platform",
                "cursor",
                "--config",
                str(config_file),
                "--force",
            ],
        )

        assert result.exit_code == 1
        assert "Server 'nonexistent' not found" in result.stdout

    def test_validate_command_valid_config(self):
        """Test validate command with valid configuration."""
        config_file = self.test_config_dir / "mcp.json"
        test_config = {
            "mcpServers": {
                "accordo": {
                    "command": "uvx",
                    "args": [
                        
                        "accordo-workflow-mcp",
                        "accordo-mcp",
                    ],
                }
            }
        }
        config_file.write_text(json.dumps(test_config, indent=2))

        result = self.runner.invoke(
            app, ["validate", "--platform", "cursor", "--config", str(config_file)]
        )

        assert result.exit_code == 0
        assert "Validating Cursor configuration" in result.stdout
        assert "All configurations are valid!" in result.stdout

    def test_validate_command_invalid_config(self):
        """Test validate command with invalid configuration."""
        config_file = self.test_config_dir / "mcp.json"
        test_config = {
            "mcpServers": {
                "invalid-server": {
                    "command": "",  # Invalid: empty command
                    "args": "not a list",  # Invalid: should be list
                }
            }
        }
        config_file.write_text(json.dumps(test_config, indent=2))

        result = self.runner.invoke(
            app, ["validate", "--platform", "cursor", "--config", str(config_file)]
        )

        assert result.exit_code == 1
        assert "Validation failed:" in result.stdout
        assert "Command cannot be empty" in result.stdout

    def test_validate_command_no_servers(self):
        """Test validate command with no servers configured."""
        config_file = self.test_config_dir / "mcp.json"
        test_config = {"mcpServers": {}}
        config_file.write_text(json.dumps(test_config, indent=2))

        result = self.runner.invoke(
            app, ["validate", "--platform", "cursor", "--config", str(config_file)]
        )

        assert result.exit_code == 0
        assert "No servers configured" in result.stdout


class TestPlatformSpecificHandlers:
    """Test platform-specific configuration handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_config_dir = Path("/tmp/test_workflow_commander")
        self.test_config_dir.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_config_dir.exists():
            import shutil

            shutil.rmtree(self.test_config_dir)

    def test_cursor_config_format(self):
        """Test Cursor configuration format."""
        from accordo_cli.handlers.cursor import CursorHandler

        handler = CursorHandler()
        servers = {
            "test-server": MCPServer(
                command="test-command", args=["arg1", "arg2"], env={"VAR": "value"}
            )
        }

        config = handler.create_config(servers)

        assert "mcpServers" in config
        assert "test-server" in config["mcpServers"]
        assert config["mcpServers"]["test-server"]["command"] == "test-command"
        assert config["mcpServers"]["test-server"]["args"] == ["arg1", "arg2"]
        assert config["mcpServers"]["test-server"]["env"] == {"VAR": "value"}

    def test_vscode_config_format(self):
        """Test VS Code configuration format."""
        from accordo_cli.handlers.vscode import VSCodeHandler

        handler = VSCodeHandler()
        servers = {
            "test-server": MCPServer(command="test-command", args=["arg1", "arg2"])
        }

        config = handler.create_config(servers)

        assert "mcp" in config
        assert "servers" in config["mcp"]
        assert "test-server" in config["mcp"]["servers"]
        assert config["mcp"]["servers"]["test-server"]["command"] == "test-command"
        assert config["mcp"]["servers"]["test-server"]["args"] == ["arg1", "arg2"]

    def test_claude_config_format(self):
        """Test Claude Desktop configuration format."""
        from accordo_cli.handlers.claude import ClaudeHandler

        handler = ClaudeHandler()
        servers = {
            "test-server": MCPServer(
                command="test-command", args=["arg1", "arg2"], env={"TOKEN": "secret"}
            )
        }

        config = handler.create_config(servers)

        assert "mcpServers" in config
        assert "test-server" in config["mcpServers"]
        assert config["mcpServers"]["test-server"]["command"] == "test-command"
        assert config["mcpServers"]["test-server"]["args"] == ["arg1", "arg2"]
        assert config["mcpServers"]["test-server"]["env"] == {"TOKEN": "secret"}


if __name__ == "__main__":
    pytest.main([__file__])
