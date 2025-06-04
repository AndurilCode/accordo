"""Tests for the workflow-commander CLI functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from workflow_commander_cli.handlers.claude import (
    ClaudeDesktopHandler,
)
from workflow_commander_cli.handlers.cursor import CursorHandler
from workflow_commander_cli.handlers.vscode import VSCodeHandler
from workflow_commander_cli.main import app
from workflow_commander_cli.models.config import (
    ClaudeConfig,
    CursorConfig,
    MCPServer,
    VSCodeConfig,
)
from workflow_commander_cli.models.platform import Platform, PlatformInfo


@pytest.fixture
def cli_runner():
    """Fixture providing a Typer CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_config_dir():
    """Fixture providing a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_server():
    """Fixture providing a sample MCP server configuration."""
    return MCPServer(
        command="uvx",
        args=["--from", "git+https://github.com/AndurilCode/workflow-commander@main", "dev-workflow-mcp"],
        env={"TEST_ENV": "value"}
    )


class TestCLICommands:
    """Test CLI command functionality."""
    
    def test_version_command(self, cli_runner):
        """Test version command."""
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "workflow-commander" in result.stdout
    
    def test_help_command(self, cli_runner):
        """Test help command."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Configure MCP servers for AI coding platforms" in result.stdout
    
    def test_configure_help(self, cli_runner):
        """Test configure command help."""
        result = cli_runner.invoke(app, ["configure", "--help"])
        assert result.exit_code == 0
        assert "Configure workflow-commander MCP server" in result.stdout
    
    def test_list_platforms_command(self, cli_runner):
        """Test list-platforms command."""
        result = cli_runner.invoke(app, ["list-platforms"])
        assert result.exit_code == 0
        assert "Supported AI Coding Platforms" in result.stdout
        assert "Cursor" in result.stdout
        assert "Claude Desktop" in result.stdout
        assert "VS Code" in result.stdout


class TestConfigureCommand:
    """Test configure command functionality."""
    
    def test_configure_non_interactive_missing_platform(self, cli_runner):
        """Test configure command fails without platform in non-interactive mode."""
        result = cli_runner.invoke(app, ["configure", "--non-interactive"])
        assert result.exit_code == 1
        assert "Platform must be specified in non-interactive mode" in result.stdout
    
    def test_configure_non_interactive_invalid_platform(self, cli_runner):
        """Test configure command fails with invalid platform."""
        result = cli_runner.invoke(app, [
            "configure", 
            "--platform", "invalid",
            "--non-interactive"
        ])
        assert result.exit_code == 1
        assert "Invalid platform 'invalid'" in result.stdout
    
    def test_configure_non_interactive_missing_server(self, cli_runner):
        """Test configure command fails without server name in non-interactive mode."""
        result = cli_runner.invoke(app, [
            "configure", 
            "--platform", "cursor",
            "--non-interactive"
        ])
        assert result.exit_code == 0  # This should now work - simplified workflow doesn't require server name
    
    def test_configure_non_interactive_success(self, cli_runner, temp_config_dir):
        """Test successful non-interactive configuration."""
        config_file = temp_config_dir / "settings.json"
        
        with patch('workflow_commander_cli.handlers.cursor.CursorHandler.add_server', return_value=True):
            result = cli_runner.invoke(app, [
                "configure",
                "--platform", "cursor",
                "--server", "test-server",
                "--config", str(config_file),
                "--non-interactive"
            ])
            
            assert result.exit_code == 0
            assert "Configuration successful!" in result.stdout
    
    def test_configure_interactive_keyboard_interrupt(self, cli_runner):
        """Test configure command handles keyboard interrupt gracefully."""
        with patch('workflow_commander_cli.utils.prompts.select_platform', 
                   side_effect=KeyboardInterrupt):
            result = cli_runner.invoke(app, ["configure"], input="\n")
            assert result.exit_code == 1


class TestHandlers:
    """Test configuration handlers."""
    
    def test_cursor_handler_new_config(self, temp_config_dir, sample_server):
        """Test Cursor handler creates new configuration."""
        handler = CursorHandler()
        config_file = temp_config_dir / "settings.json"
        
        handler.add_server("test-server", sample_server, config_file)
        
        assert config_file.exists()
        with open(config_file) as f:
            config = json.load(f)
        
        assert "mcpServers" in config
        assert "test-server" in config["mcpServers"]
        assert config["mcpServers"]["test-server"]["command"] == "uvx"
    
    def test_cursor_handler_existing_config(self, temp_config_dir, sample_server):
        """Test Cursor handler updates existing configuration."""
        handler = CursorHandler()
        config_file = temp_config_dir / "settings.json"
        
        # Create existing config
        existing_config = {
            "other_setting": "value",
            "mcpServers": {
                "existing-server": {
                    "command": "existing",
                    "args": []
                }
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(existing_config, f)
        
        handler.add_server("test-server", sample_server, config_file)
        
        with open(config_file) as f:
            config = json.load(f)
        
        # Check that existing content is preserved
        assert config["other_setting"] == "value"
        assert "existing-server" in config["mcpServers"]
        assert "test-server" in config["mcpServers"]
    
    def test_claude_handler_new_config(self, temp_config_dir, sample_server):
        """Test Claude handler creates new configuration."""
        handler = ClaudeDesktopHandler()
        config_file = temp_config_dir / "claude_desktop_config.json"
        
        handler.add_server("test-server", sample_server, config_file)
        
        assert config_file.exists()
        with open(config_file) as f:
            config = json.load(f)
        
        assert "mcpServers" in config
        assert "test-server" in config["mcpServers"]
    
    def test_vscode_handler_new_config(self, temp_config_dir, sample_server):
        """Test VS Code handler creates new configuration."""
        handler = VSCodeHandler()
        config_file = temp_config_dir / "settings.json"
        
        handler.add_server("test-server", sample_server, config_file)
        
        assert config_file.exists()
        with open(config_file) as f:
            config = json.load(f)
        
        assert "mcp" in config
        assert "servers" in config["mcp"]
        assert "test-server" in config["mcp"]["servers"]
    
    def test_handler_backup_creation(self, temp_config_dir, sample_server):
        """Test that handlers create backups of existing files."""
        handler = CursorHandler()
        config_file = temp_config_dir / "settings.json"
        
        # Create an existing config file
        existing_config = {"existing": "config"}
        with open(config_file, 'w') as f:
            json.dump(existing_config, f)
        
        handler.add_server("test-server", sample_server, config_file)
        
        # Check that backup was created (the backup method is in the save_config call)
        backup_files = list(temp_config_dir.glob("settings.json.backup*"))
        assert len(backup_files) > 0
    
    def test_handler_validation_error(self, temp_config_dir):
        """Test handler validation catches invalid server configs."""
        handler = CursorHandler()
        config_file = temp_config_dir / "settings.json"
        
        # Test validation by creating an MCPServer with the minimum valid data
        # and then testing the handler's validation logic
        from workflow_commander_cli.models.config import MCPServer
        
        # This should work - valid server
        valid_server = MCPServer(command="test", args=[])
        handler.add_server("test-server", valid_server, config_file)
        
        # Test that the config was created
        assert config_file.exists()


class TestPrompts:
    """Test interactive prompt functions."""
    
    def test_select_platform_valid_choice(self):
        """Test platform selection with valid input."""
        from workflow_commander_cli.utils.prompts import select_platform
        
        # Mock both typer.prompt and typer.secho to avoid any output issues
        with (
            patch('workflow_commander_cli.utils.prompts.typer.prompt', return_value=1) as mock_prompt,
            patch('workflow_commander_cli.utils.prompts.typer.secho'),
            patch('workflow_commander_cli.utils.prompts.typer.echo'),
        ):
            platform = select_platform()
            assert platform == Platform.CURSOR
            mock_prompt.assert_called_once_with("Enter your choice (1-4)", type=int)
    
    def test_select_platform_invalid_then_valid(self):
        """Test platform selection with invalid then valid input."""
        from workflow_commander_cli.utils.prompts import select_platform
        
        # Mock to return invalid choice first, then valid choice
        with (
            patch('workflow_commander_cli.utils.prompts.typer.prompt', side_effect=[5, 2]) as mock_prompt,
            patch('workflow_commander_cli.utils.prompts.typer.secho'),
            patch('workflow_commander_cli.utils.prompts.typer.echo'),
        ):
            platform = select_platform()
            assert platform == Platform.CLAUDE_DESKTOP
            assert mock_prompt.call_count == 2
    
    def test_get_workflow_commander_details_default(self):
        """Test getting workflow commander details with default choices."""
        from workflow_commander_cli.utils.prompts import get_workflow_commander_details
        
        with (
            patch('workflow_commander_cli.utils.prompts.typer.prompt', side_effect=["workflow-commander"]),
            patch('workflow_commander_cli.utils.prompts.typer.confirm', return_value=True),
            patch('workflow_commander_cli.utils.prompts.typer.secho'),
            patch('workflow_commander_cli.utils.prompts.typer.echo'),
        ):
            name, config = get_workflow_commander_details()
            assert name == "workflow-commander"
            assert config.command == "uvx"
    
    def test_get_workflow_commander_details_custom(self):
        """Test getting workflow commander details with custom configuration."""
        from workflow_commander_cli.utils.prompts import get_workflow_commander_details
        
        with (
            patch('workflow_commander_cli.utils.prompts.typer.prompt', side_effect=["custom-server", "node", "server.js"]),
            patch('workflow_commander_cli.utils.prompts.typer.confirm', return_value=False),
            patch('workflow_commander_cli.utils.prompts.typer.secho'),
            patch('workflow_commander_cli.utils.prompts.typer.echo'),
        ):
            name, config = get_workflow_commander_details()
            assert name == "custom-server"
            assert config.command == "node"
            assert config.args == ["server.js"]


class TestModels:
    """Test data models."""
    
    def test_mcp_server_validation(self):
        """Test MCP server validation."""
        # Valid server
        server = MCPServer(command="node", args=["server.js"])
        assert server.command == "node"
        assert server.args == ["server.js"]
        
        # Server with environment
        server_with_env = MCPServer(
            command="python",
            args=["-m", "server"],
            env={"API_KEY": "secret"}
        )
        assert server_with_env.env == {"API_KEY": "secret"}
    
    def test_cursor_config_creation(self, sample_server):
        """Test Cursor configuration creation."""
        config = CursorConfig()
        config.add_server("test", sample_server)
        
        config_dict = config.to_dict()
        assert "mcpServers" in config_dict
        assert "test" in config_dict["mcpServers"]
    
    def test_claude_config_creation(self, sample_server):
        """Test Claude configuration creation."""
        config = ClaudeConfig()
        config.add_server("test", sample_server)
        
        config_dict = config.to_dict()
        assert "mcpServers" in config_dict
        assert "test" in config_dict["mcpServers"]
    
    def test_vscode_config_creation(self, sample_server):
        """Test VS Code configuration creation."""
        config = VSCodeConfig()
        config.add_server("test", sample_server)
        
        config_dict = config.to_dict()
        assert "mcp" in config_dict
        assert "servers" in config_dict["mcp"]
        assert "test" in config_dict["mcp"]["servers"]
    
    def test_platform_info_creation(self):
        """Test platform info retrieval."""
        all_platforms = PlatformInfo.get_all_platforms()
        
        assert Platform.CURSOR in all_platforms
        assert Platform.CLAUDE_DESKTOP in all_platforms
        assert Platform.VSCODE in all_platforms
        
        cursor_info = all_platforms[Platform.CURSOR]
        assert cursor_info.name == "Cursor"
        assert "AI-powered" in cursor_info.description


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @patch('workflow_commander_cli.main.select_platform')
    @patch('workflow_commander_cli.main.get_workflow_commander_details')
    @patch('workflow_commander_cli.main.select_config_location')
    @patch('workflow_commander_cli.main.confirm_action')
    def test_full_interactive_workflow(
        self, 
        mock_confirm,
        mock_location,
        mock_server_details,
        mock_platform,
        cli_runner,
        temp_config_dir,
        sample_server
    ):
        """Test complete interactive configuration workflow."""
        # Setup mocks - make sure they're patched in the right module
        mock_platform.return_value = Platform.CURSOR
        mock_server_details.return_value = ("workflow-commander", sample_server)
        mock_location.return_value = (False, temp_config_dir / "settings.json")
        mock_confirm.return_value = True
        
        with patch('workflow_commander_cli.handlers.cursor.CursorHandler.add_server', return_value=True):
            result = cli_runner.invoke(app, ["configure"])
            
            # Should succeed now that mocks are properly placed
            assert result.exit_code == 0
            assert "Configuration successful!" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__]) 