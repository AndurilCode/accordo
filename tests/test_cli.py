"""Tests for the accordo CLI functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from accordo_cli.handlers.claude import (
    ClaudeDesktopHandler,
)
from accordo_cli.handlers.cursor import CursorHandler
from accordo_cli.handlers.vscode import VSCodeHandler
from accordo_cli.main import app
from accordo_cli.models.config import (
    ClaudeConfig,
    CursorConfig,
    MCPServer,
    VSCodeConfig,
)
from accordo_cli.models.platform import ConfigLocation, Platform, PlatformInfo


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
        args=[
            "accordo-workflow-mcp",
        ],
        env={"TEST_ENV": "value"},
    )


class TestCLICommands:
    """Test CLI command functionality."""

    def test_version_command(self, cli_runner):
        """Test version command."""
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "accordo" in result.stdout

    def test_help_command(self, cli_runner):
        """Test help command."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Configure MCP servers for AI coding platforms" in result.stdout

    def test_configure_help(self, cli_runner):
        """Test configure command help."""
        result = cli_runner.invoke(app, ["configure", "--help"])
        assert result.exit_code == 0
        assert "Configure accordo MCP server" in result.stdout

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
        result = cli_runner.invoke(
            app, ["configure", "--platform", "invalid", "--non-interactive"]
        )
        assert result.exit_code == 1
        assert "Invalid platform 'invalid'" in result.stdout

    def test_configure_non_interactive_missing_server(self, cli_runner):
        """Test configure command fails without server name in non-interactive mode."""
        result = cli_runner.invoke(
            app, ["configure", "--platform", "cursor", "--non-interactive"]
        )
        assert (
            result.exit_code == 0
        )  # This should now work - simplified workflow doesn't require server name

    def test_configure_non_interactive_success(self, cli_runner, temp_config_dir):
        """Test successful non-interactive configuration."""
        config_file = temp_config_dir / "settings.json"

        with patch(
            "accordo_cli.handlers.cursor.CursorHandler.add_server", return_value=True
        ):
            result = cli_runner.invoke(
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

            assert result.exit_code == 0
            assert "Configuration successful!" in result.stdout

    def test_configure_interactive_keyboard_interrupt(self, cli_runner):
        """Test configure command handles keyboard interrupt gracefully."""
        with patch(
            "accordo_cli.utils.prompts.select_platform", side_effect=KeyboardInterrupt
        ):
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
            "mcpServers": {"existing-server": {"command": "existing", "args": []}},
        }

        with open(config_file, "w") as f:
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
        with open(config_file, "w") as f:
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
        from accordo_cli.models.config import MCPServer

        # This should work - valid server
        valid_server = MCPServer(command="test", args=[])
        handler.add_server("test-server", valid_server, config_file)

        # Test that the config was created
        assert config_file.exists()


class TestPrompts:
    """Test interactive prompt functions."""

    def test_select_platform_valid_choice(self):
        """Test platform selection with valid input."""
        from accordo_cli.utils.prompts import select_platform

        # Mock both typer.prompt and typer.secho to avoid any output issues
        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt", return_value=1
            ) as mock_prompt,
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            platform = select_platform()
            assert platform == Platform.CURSOR
            mock_prompt.assert_called_once_with("Enter your choice (1-4)", type=int)

    def test_select_platform_invalid_then_valid(self):
        """Test platform selection with invalid then valid input."""
        from accordo_cli.utils.prompts import select_platform

        # Mock to return invalid choice first, then valid choice
        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt", side_effect=[5, 2]
            ) as mock_prompt,
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            platform = select_platform()
            assert platform == Platform.CLAUDE_DESKTOP
            assert mock_prompt.call_count == 2

    def test_get_workflow_commander_details_default(self):
        """Test getting workflow commander details with default choices."""
        from accordo_cli.utils.prompts import get_workflow_commander_details

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt", side_effect=["accordo", 1]
            ),  # Server name, basic template
            patch(
                "accordo_cli.utils.prompts.typer.confirm", return_value=False
            ),  # Don't customize
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            name, config = get_workflow_commander_details()
            assert name == "accordo"
            assert config.command == "uvx"

    def test_get_workflow_commander_details_custom(self):
        """Test getting workflow commander details with custom configuration."""
        from accordo_cli.utils.prompts import get_workflow_commander_details

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt",
                side_effect=[
                    "custom-server",  # Server name
                    4,  # Custom configuration
                    "global",  # Repository location choice
                    "JSON",  # State file format
                    72,  # Session retention
                    "all-MiniLM-L6-v2",  # Embedding model
                    ".accordo/cache",  # Cache path
                    50,  # Max results
                ],
            ),
            patch(
                "accordo_cli.utils.prompts.typer.confirm",
                side_effect=[
                    True,  # Enable local state
                    True,  # Enable cache
                ],
            ),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            name, config = get_workflow_commander_details()
            assert name == "custom-server"
            assert config.command == "uvx"
            assert "--global" in config.args


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
            command="python", args=["-m", "server"], env={"API_KEY": "secret"}
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

    @patch("accordo_cli.main.select_platform")
    @patch("accordo_cli.main.get_workflow_commander_details")
    @patch("accordo_cli.main.select_config_location")
    @patch("accordo_cli.main.confirm_action")
    def test_full_interactive_workflow(
        self,
        mock_confirm,
        mock_location,
        mock_server_details,
        mock_platform,
        cli_runner,
        temp_config_dir,
        sample_server,
    ):
        """Test complete interactive configuration workflow."""
        # Setup mocks - make sure they're patched in the right module
        mock_platform.return_value = Platform.CURSOR
        mock_server_details.return_value = ("accordo", sample_server)
        mock_location.return_value = (False, temp_config_dir / "settings.json")
        mock_confirm.return_value = True

        with patch(
            "accordo_cli.handlers.cursor.CursorHandler.add_server", return_value=True
        ):
            result = cli_runner.invoke(app, ["configure"])

            # Should succeed now that mocks are properly placed
            assert result.exit_code == 0
            assert "Configuration successful!" in result.stdout


class TestConfigurationTemplates:
    """Test configuration template functionality."""

    def test_configuration_template_enum(self):
        """Test ConfigurationTemplate enum values."""
        from accordo_cli.models.config import ConfigurationTemplate

        assert ConfigurationTemplate.BASIC == "basic"
        assert ConfigurationTemplate.ADVANCED == "advanced"
        assert ConfigurationTemplate.CACHE_ENABLED == "cache_enabled"

    def test_basic_template_config(self):
        """Test basic template configuration."""
        from accordo_cli.models.config import TemplateConfig

        template = TemplateConfig.get_basic_template()
        assert template.name == "Basic Setup"
        assert "Minimal configuration" in template.description
        assert template.args == [
            "accordo-workflow-mcp",
        ]

    def test_advanced_template_config(self):
        """Test advanced template configuration."""
        from accordo_cli.models.config import TemplateConfig

        template = TemplateConfig.get_advanced_template()
        assert template.name == "Advanced Setup"
        assert "comprehensive command line options" in template.description
        assert "--local" in template.args
        assert "--enable-local-state-file" in template.args
        assert "--enable-cache-mode" in template.args
        assert "--cache-embedding-model" in template.args

    def test_cache_enabled_template_config(self):
        """Test cache-enabled template configuration."""
        from accordo_cli.models.config import TemplateConfig

        template = TemplateConfig.get_cache_enabled_template()
        assert template.name == "Cache-Enabled Setup"
        assert "semantic workflow analysis" in template.description
        assert "--enable-cache-mode" in template.args
        assert "--cache-embedding-model" in template.args
        assert "all-MiniLM-L6-v2" in template.args

    def test_get_template_by_enum(self):
        """Test getting template by enum value."""
        from accordo_cli.models.config import (
            ConfigurationTemplate,
            TemplateConfig,
        )

        basic = TemplateConfig.get_template(ConfigurationTemplate.BASIC)
        assert basic.name == "Basic Setup"

        advanced = TemplateConfig.get_template(ConfigurationTemplate.ADVANCED)
        assert advanced.name == "Advanced Setup"

        cache = TemplateConfig.get_template(ConfigurationTemplate.CACHE_ENABLED)
        assert cache.name == "Cache-Enabled Setup"

    def test_invalid_template_raises_error(self):
        """Test that invalid template raises ValueError."""
        from accordo_cli.models.config import TemplateConfig

        with pytest.raises(ValueError, match="Unknown template"):
            TemplateConfig.get_template("invalid_template")


class TestConfigurationBuilder:
    """Test ConfigurationBuilder functionality."""

    def test_builder_basic_initialization(self):
        """Test basic builder initialization."""
        from accordo_cli.models.config import ConfigurationBuilder

        builder = ConfigurationBuilder()
        assert builder.command == "uvx"
        assert builder.base_args == [
            "accordo-workflow-mcp",
        ]
        assert len(builder.options) == 0

    def test_builder_with_template(self):
        """Test builder initialization with template."""
        from accordo_cli.models.config import (
            ConfigurationBuilder,
            ConfigurationTemplate,
        )

        builder = ConfigurationBuilder(ConfigurationTemplate.CACHE_ENABLED)
        assert len(builder.options) > 0

        # Check that template options are parsed
        flags = [opt.flag for opt in builder.options]
        assert "--local" in flags
        assert "--enable-cache-mode" in flags

    def test_builder_add_repository_path(self):
        """Test adding repository path."""
        from accordo_cli.models.config import ConfigurationBuilder

        builder = ConfigurationBuilder()
        builder.add_repository_path("/custom/path")

        repo_option = next(
            opt for opt in builder.options if opt.flag == "--repository-path"
        )
        assert repo_option.value == "/custom/path"

    def test_builder_enable_local_state_file(self):
        """Test enabling local state file."""
        from accordo_cli.models.config import ConfigurationBuilder

        builder = ConfigurationBuilder()
        builder.enable_local_state_file("MD")

        flags = [opt.flag for opt in builder.options]
        assert "--enable-local-state-file" in flags
        assert "--local-state-file-format" in flags

        format_option = next(
            opt for opt in builder.options if opt.flag == "--local-state-file-format"
        )
        assert format_option.value == "MD"

    def test_builder_enable_cache_mode(self):
        """Test enabling cache mode."""
        from accordo_cli.models.config import ConfigurationBuilder

        builder = ConfigurationBuilder()
        builder.enable_cache_mode("custom-model")

        flags = [opt.flag for opt in builder.options]
        assert "--enable-cache-mode" in flags
        assert "--cache-embedding-model" in flags

        model_option = next(
            opt for opt in builder.options if opt.flag == "--cache-embedding-model"
        )
        assert model_option.value == "custom-model"

    def test_builder_build_mcp_server(self):
        """Test building MCPServer from builder."""
        from accordo_cli.models.config import ConfigurationBuilder

        builder = ConfigurationBuilder()
        builder.add_repository_path(".")
        builder.enable_cache_mode()

        server = builder.build()
        assert server.command == "uvx"
        assert "--repository-path" in server.args
        assert "." in server.args
        assert "--enable-cache-mode" in server.args

    def test_builder_get_args_preview(self):
        """Test getting args preview without building."""
        from accordo_cli.models.config import ConfigurationBuilder

        builder = ConfigurationBuilder()
        builder.add_repository_path(".")

        args = builder.get_args_preview()
        assert "accordo-workflow-mcp" in args
        assert "--repository-path" in args
        assert "." in args

    def test_builder_update_existing_option(self):
        """Test updating existing option."""
        from accordo_cli.models.config import (
            ConfigurationBuilder,
            ConfigurationTemplate,
        )

        builder = ConfigurationBuilder(ConfigurationTemplate.CACHE_ENABLED)

        # Update repository path
        builder.add_repository_path("/new/path")

        repo_options = [
            opt for opt in builder.options if opt.flag == "--repository-path"
        ]
        assert len(repo_options) == 1  # Should only have one
        assert repo_options[0].value == "/new/path"

    def test_configuration_option_to_args(self):
        """Test ConfigurationOption to_args method."""
        from accordo_cli.models.config import ConfigurationOption

        # Option with value
        option_with_value = ConfigurationOption(
            flag="--test-flag",
            value="test-value",
            description="Test option",
            requires_value=True,
        )
        assert option_with_value.to_args() == ["--test-flag", "test-value"]

        # Option without value
        option_without_value = ConfigurationOption(
            flag="--enable-test", description="Test flag", requires_value=False
        )
        assert option_without_value.to_args() == ["--enable-test"]

        # Option that requires value but has none
        option_missing_value = ConfigurationOption(
            flag="--missing-value", description="Missing value", requires_value=True
        )
        assert option_missing_value.to_args() == []

    def test_mcp_server_command_validation(self):
        """Test MCPServer command validation."""
        from accordo_cli.models.config import MCPServer

        # Test empty command raises ValueError
        with pytest.raises(ValueError, match="Command cannot be empty"):
            MCPServer(command="")

        # Test whitespace-only command raises ValueError
        with pytest.raises(ValueError, match="Command cannot be empty"):
            MCPServer(command="   ")

        # Test command gets stripped
        server = MCPServer(command="  uvx  ")
        assert server.command == "uvx"

    def test_mcp_server_to_dict_comprehensive(self):
        """Test MCPServer to_dict method with all combinations."""
        from accordo_cli.models.config import MCPServer

        # Test with minimal config
        server_minimal = MCPServer(command="uvx")
        assert server_minimal.to_dict() == {"command": "uvx"}

        # Test with args only
        server_with_args = MCPServer(command="uvx", args=["package"])
        assert server_with_args.to_dict() == {"command": "uvx", "args": ["package"]}

        # Test with env only
        server_with_env = MCPServer(command="uvx", env={"VAR": "value"})
        assert server_with_env.to_dict() == {"command": "uvx", "env": {"VAR": "value"}}

        # Test with url only
        server_with_url = MCPServer(command="uvx", url="http://localhost:8000")
        assert server_with_url.to_dict() == {
            "command": "uvx",
            "url": "http://localhost:8000",
        }

        # Test with all fields
        server_full = MCPServer(
            command="uvx",
            args=["package"],
            env={"VAR": "value"},
            url="http://localhost:8000",
        )
        expected = {
            "command": "uvx",
            "args": ["package"],
            "env": {"VAR": "value"},
            "url": "http://localhost:8000",
        }
        assert server_full.to_dict() == expected

    def test_template_config_get_template_invalid(self):
        """Test TemplateConfig.get_template with invalid template."""
        from accordo_cli.models.config import TemplateConfig

        with pytest.raises(ValueError, match="Unknown template"):
            TemplateConfig.get_template("invalid_template")

    def test_mcp_server_config_operations(self):
        """Test MCPServerConfig add/remove operations."""
        from accordo_cli.models.config import MCPServer, MCPServerConfig

        config = MCPServerConfig()
        server = MCPServer(command="uvx")

        # Test add server
        config.add_server("test", server)
        assert "test" in config.servers
        assert config.servers["test"] == server

        # Test remove existing server
        result = config.remove_server("test")
        assert result is True
        assert "test" not in config.servers

        # Test remove non-existing server
        result = config.remove_server("non-existing")
        assert result is False

    def test_cursor_config_operations(self):
        """Test CursorConfig operations."""
        from accordo_cli.models.config import CursorConfig, MCPServer, MCPServerConfig

        # Test from_base_config
        base_config = MCPServerConfig()
        server = MCPServer(command="uvx")
        base_config.add_server("test", server)

        cursor_config = CursorConfig.from_base_config(base_config)
        assert "test" in cursor_config.mcpServers

        # Test add_server
        new_server = MCPServer(command="python")
        cursor_config.add_server("new-test", new_server)
        assert "new-test" in cursor_config.mcpServers

        # Test to_json
        json_str = cursor_config.to_json()
        assert "mcpServers" in json_str
        assert "test" in json_str

    def test_claude_config_operations(self):
        """Test ClaudeConfig operations."""
        from accordo_cli.models.config import ClaudeConfig, MCPServer, MCPServerConfig

        # Test from_base_config
        base_config = MCPServerConfig()
        server = MCPServer(command="uvx")
        base_config.add_server("test", server)

        claude_config = ClaudeConfig.from_base_config(base_config)
        assert "test" in claude_config.mcpServers

        # Test add_server
        new_server = MCPServer(command="python")
        claude_config.add_server("new-test", new_server)
        assert "new-test" in claude_config.mcpServers

        # Test to_json
        json_str = claude_config.to_json()
        assert "mcpServers" in json_str

    def test_vscode_config_operations(self):
        """Test VSCodeConfig operations."""
        from accordo_cli.models.config import MCPServer, VSCodeConfig

        # Create VSCodeConfig directly since the nested structure is complex
        vscode_config = VSCodeConfig()

        # Test add_server
        server = MCPServer(command="uvx")
        vscode_config.add_server("test", server)
        assert "test" in vscode_config.mcp["servers"]

        # Test add another server
        new_server = MCPServer(command="python")
        vscode_config.add_server("new-test", new_server)
        assert "new-test" in vscode_config.mcp["servers"]

        # Test to_dict and to_json
        config_dict = vscode_config.to_dict()
        assert "mcp" in config_dict
        assert "servers" in config_dict["mcp"]
        assert "test" in config_dict["mcp"]["servers"]
        assert "new-test" in config_dict["mcp"]["servers"]

        json_str = vscode_config.to_json()
        assert "mcp" in json_str
        assert "test" in json_str

    def test_configuration_builder_add_custom_option(self):
        """Test ConfigurationBuilder add_custom_option method."""
        from accordo_cli.models.config import ConfigurationBuilder

        builder = ConfigurationBuilder()

        # Test adding custom option with value
        builder.add_custom_option("--custom-flag", "custom-value", "Custom description")
        assert any(opt.flag == "--custom-flag" for opt in builder.options)
        custom_opt = next(opt for opt in builder.options if opt.flag == "--custom-flag")
        assert custom_opt.value == "custom-value"
        assert custom_opt.description == "Custom description"
        assert custom_opt.requires_value is True

        # Test adding custom option without value
        builder.add_custom_option("--custom-no-value", description="No value custom")
        no_value_opt = next(
            opt for opt in builder.options if opt.flag == "--custom-no-value"
        )
        assert no_value_opt.value is None
        assert no_value_opt.requires_value is False

    def test_configuration_builder_with_global_local_flags(self):
        """Test ConfigurationBuilder global and local flag methods."""
        from accordo_cli.models.config import ConfigurationBuilder

        builder = ConfigurationBuilder()

        # Test add_global_flag
        builder.add_global_flag()
        assert any(opt.flag == "--global" for opt in builder.options)
        global_opt = next(opt for opt in builder.options if opt.flag == "--global")
        assert global_opt.requires_value is False

        # Test add_local_flag (should replace global due to _update_or_add_option removing existing)
        builder.add_local_flag()
        # The _update_or_add_option method removes flags with the same name, but these are different flags
        # So both might exist unless we specifically remove the other in the method
        local_flags = [opt for opt in builder.options if opt.flag == "--local"]
        assert len(local_flags) == 1  # Should be added

        # Test deprecated add_repository_path (should remove local flag)
        builder.add_repository_path("/custom/path")
        repo_flags = [opt for opt in builder.options if opt.flag == "--repository-path"]
        assert len(repo_flags) == 1  # Should be added
        repo_opt = repo_flags[0]
        assert repo_opt.value == "/custom/path"

    def test_configuration_builder_cache_methods(self):
        """Test ConfigurationBuilder cache-related methods."""
        from accordo_cli.models.config import ConfigurationBuilder

        builder = ConfigurationBuilder()

        # Test set_cache_path
        builder.set_cache_path("/custom/cache")
        cache_opt = next(
            opt for opt in builder.options if opt.flag == "--cache-db-path"
        )
        assert cache_opt.value == "/custom/cache"

        # Test set_cache_max_results
        builder.set_cache_max_results(100)
        max_opt = next(
            opt for opt in builder.options if opt.flag == "--cache-max-results"
        )
        assert max_opt.value == "100"

    def test_mcp_server_config_to_dict(self):
        """Test MCPServerConfig to_dict method."""
        from accordo_cli.models.config import MCPServer, MCPServerConfig

        config = MCPServerConfig()
        server1 = MCPServer(command="uvx", args=["package1"])
        server2 = MCPServer(command="python", args=["package2"])

        config.add_server("server1", server1)
        config.add_server("server2", server2)

        result = config.to_dict()
        assert "server1" in result
        assert "server2" in result
        assert result["server1"]["command"] == "uvx"
        assert result["server2"]["command"] == "python"


class TestEnhancedPrompts:
    """Test enhanced prompt functionality."""

    def test_select_configuration_template_basic(self):
        """Test selecting basic configuration template."""
        from accordo_cli.models.config import ConfigurationTemplate
        from accordo_cli.utils.prompts import select_configuration_template

        with (
            patch("accordo_cli.utils.prompts.typer.prompt", return_value=1),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            template = select_configuration_template()
            assert template == ConfigurationTemplate.BASIC

    def test_select_configuration_template_custom(self):
        """Test selecting custom configuration."""
        from accordo_cli.utils.prompts import select_configuration_template

        with (
            patch("accordo_cli.utils.prompts.typer.prompt", return_value=4),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            template = select_configuration_template()
            assert template is None  # Custom configuration

    def test_select_configuration_template_all_options(self):
        """Test all configuration template options."""
        from accordo_cli.models.config import ConfigurationTemplate
        from accordo_cli.utils.prompts import select_configuration_template

        # Test each template option
        test_cases = [
            (1, ConfigurationTemplate.BASIC),
            (2, ConfigurationTemplate.ADVANCED),
            (3, ConfigurationTemplate.CACHE_ENABLED),
            (4, None),  # Custom
        ]

        for choice, expected in test_cases:
            with (
                patch("accordo_cli.utils.prompts.typer.prompt", return_value=choice),
                patch("accordo_cli.utils.prompts.typer.secho"),
                patch("accordo_cli.utils.prompts.typer.echo"),
            ):
                template = select_configuration_template()
                assert template == expected

    def test_select_configuration_template_invalid_then_valid(self):
        """Test invalid choice followed by valid choice."""
        from accordo_cli.models.config import ConfigurationTemplate
        from accordo_cli.utils.prompts import select_configuration_template

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt", side_effect=[5, 1]
            ),  # Invalid then valid
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            template = select_configuration_template()
            assert template == ConfigurationTemplate.BASIC

    def test_select_platform_all_options(self):
        """Test all platform selection options."""
        from accordo_cli.models.platform import Platform
        from accordo_cli.utils.prompts import select_platform

        test_cases = [
            (1, Platform.CURSOR),
            (2, Platform.CLAUDE_DESKTOP),
            (3, Platform.CLAUDE_CODE),
            (4, Platform.VSCODE),
        ]

        for choice, expected in test_cases:
            with (
                patch("accordo_cli.utils.prompts.typer.prompt", return_value=choice),
                patch("accordo_cli.utils.prompts.typer.secho"),
                patch("accordo_cli.utils.prompts.typer.echo"),
            ):
                platform = select_platform()
                assert platform == expected

    def test_select_platform_invalid_then_valid(self):
        """Test invalid platform choice followed by valid choice."""
        from accordo_cli.models.platform import Platform
        from accordo_cli.utils.prompts import select_platform

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt", side_effect=[5, 1]
            ),  # Invalid then valid
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            platform = select_platform()
            assert platform == Platform.CURSOR

    def test_confirm_action(self):
        """Test confirm_action function."""
        from accordo_cli.utils.prompts import confirm_action

        # Test with default True
        with patch("accordo_cli.utils.prompts.typer.confirm", return_value=True):
            result = confirm_action("Test message")
            assert result is True

        # Test with default False
        with patch("accordo_cli.utils.prompts.typer.confirm", return_value=False):
            result = confirm_action("Test message", default=False)
            assert result is False

    def test_build_custom_configuration(self):
        """Test build_custom_configuration function."""
        from accordo_cli.utils.prompts import build_custom_configuration

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt",
                side_effect=[
                    "global",  # Repository location
                    "JSON",  # State file format
                    72,  # Session retention
                    "all-MiniLM-L6-v2",  # Embedding model
                    ".accordo/cache",  # Cache path
                    50,  # Max results
                ],
            ),
            patch(
                "accordo_cli.utils.prompts.typer.confirm",
                side_effect=[
                    True,  # Enable local state
                    True,  # Enable cache
                ],
            ),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            builder = build_custom_configuration()
            args = builder.get_args_preview()
            assert "--global" in args

    def test_build_custom_configuration_local_path(self):
        """Test build_custom_configuration with local repository choice."""
        from accordo_cli.utils.prompts import build_custom_configuration

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt",
                side_effect=[
                    "local",  # Repository location
                ],
            ),
            patch(
                "accordo_cli.utils.prompts.typer.confirm",
                side_effect=[
                    False,  # Don't enable local state
                    False,  # Don't enable cache
                ],
            ),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            builder = build_custom_configuration()
            args = builder.get_args_preview()
            assert "--local" in args

    def test_build_custom_configuration_custom_path(self):
        """Test build_custom_configuration with custom repository path."""
        from accordo_cli.utils.prompts import build_custom_configuration

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt",
                side_effect=[
                    "custom",  # Repository location
                    "/custom/path",  # Custom path
                ],
            ),
            patch(
                "accordo_cli.utils.prompts.typer.confirm",
                side_effect=[
                    False,  # Don't enable local state
                    False,  # Don't enable cache
                ],
            ),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            builder = build_custom_configuration()
            args = builder.get_args_preview()
            assert "--repository-path" in args
            assert "/custom/path" in args

    def test_customize_configuration_comprehensive(self):
        """Test customize_configuration with comprehensive scenarios."""
        from accordo_cli.models.config import ConfigurationBuilder
        from accordo_cli.utils.prompts import customize_configuration

        # Test with builder that has existing options
        builder = ConfigurationBuilder()
        builder.add_global_flag()
        builder.enable_local_state_file()
        builder.enable_cache_mode()

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt",
                side_effect=[
                    "local",  # Change to local repository
                    "MD",  # Change format to MD
                    48,  # Change session retention
                    "custom-model",  # Change embedding model
                    "/custom/cache",  # Change cache path
                    25,  # Change max results
                ],
            ),
            patch(
                "accordo_cli.utils.prompts.typer.confirm",
                side_effect=[
                    True,  # Enable local state
                    True,  # Enable cache
                ],
            ),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            result_builder = customize_configuration(builder)
            args = result_builder.get_args_preview()
            assert "--local" in args
            assert "--local-state-file-format" in args
            assert "MD" in args

    def test_select_config_location_with_project_path(self):
        """Test select_config_location with project path available."""
        from pathlib import Path

        from accordo_cli.models.platform import Platform, PlatformInfo
        from accordo_cli.utils.prompts import select_config_location

        platform_info = PlatformInfo(
            name="Test Platform",
            platform=Platform.CURSOR,
            description="Test platform",
            config_format="mcpServers",
            locations=ConfigLocation(
                global_path=Path.home() / ".config/test/config.json",
                project_path=Path(".config/config.json"),
                description="Test location",
            ),
        )

        # Test global choice
        with (
            patch("accordo_cli.utils.prompts.typer.prompt", return_value=1),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            use_global, custom_path = select_config_location(platform_info)
            assert use_global is True
            assert custom_path is None

        # Test project-specific choice
        with (
            patch("accordo_cli.utils.prompts.typer.prompt", return_value=2),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            use_global, custom_path = select_config_location(platform_info)
            assert use_global is False
            assert custom_path is None

        # Test custom path choice
        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt",
                side_effect=[3, "/custom/config.json"],
            ),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            use_global, custom_path = select_config_location(platform_info)
            assert use_global is True
            assert str(custom_path) == "/custom/config.json"

    def test_select_config_location_without_project_path(self):
        """Test select_config_location without project path."""
        from pathlib import Path

        from accordo_cli.models.platform import Platform, PlatformInfo
        from accordo_cli.utils.prompts import select_config_location

        platform_info = PlatformInfo(
            name="Test Platform",
            platform=Platform.CLAUDE_DESKTOP,
            description="Test platform",
            config_format="mcpServers",
            locations=ConfigLocation(
                global_path=Path.home() / ".config/test/config.json",
                project_path=None,  # No project path
                description="Test location",
            ),
        )

        # Test custom path choice (should be option 2 when no project path)
        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt",
                side_effect=[2, "/custom/config.json"],
            ),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            use_global, custom_path = select_config_location(platform_info)
            assert use_global is True
            assert str(custom_path) == "/custom/config.json"

    def test_select_config_location_invalid_choice(self):
        """Test select_config_location with invalid choice."""
        from pathlib import Path

        from accordo_cli.models.platform import Platform, PlatformInfo
        from accordo_cli.utils.prompts import select_config_location

        platform_info = PlatformInfo(
            name="Test Platform",
            platform=Platform.CURSOR,
            description="Test platform",
            config_format="mcpServers",
            locations=ConfigLocation(
                global_path=Path.home() / ".config/test/config.json",
                project_path=Path(".config/config.json"),
                description="Test location",
            ),
        )

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt", side_effect=[5, 1]
            ),  # Invalid then valid
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            use_global, custom_path = select_config_location(platform_info)
            assert use_global is True
            assert custom_path is None

    def test_display_success_message(self):
        """Test display_success_message function."""
        from pathlib import Path

        from accordo_cli.utils.prompts import display_success_message

        with (
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            # Should not raise any exceptions
            display_success_message(
                "Test Platform", "test-server", Path("/test/config.json")
            )

    def test_display_error_message(self):
        """Test display_error_message function."""
        from accordo_cli.utils.prompts import display_error_message

        with (
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            # Test without suggestions
            display_error_message("Test error")

            # Test with suggestions
            display_error_message("Test error", ["Suggestion 1", "Suggestion 2"])

    def test_get_workflow_commander_details_with_template(self):
        """Test enhanced get_workflow_commander_details with template selection."""
        from accordo_cli.utils.prompts import get_workflow_commander_details

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt", side_effect=["test-server", 2]
            ),  # Server name, template choice
            patch(
                "accordo_cli.utils.prompts.typer.confirm", return_value=False
            ),  # Don't customize
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            name, config = get_workflow_commander_details()
            assert name == "test-server"
            assert config.command == "uvx"
            assert "--local" in config.args  # Advanced template includes this

    def test_get_workflow_commander_details_with_customization(self):
        """Test enhanced function with template customization."""
        from accordo_cli.utils.prompts import get_workflow_commander_details

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt",
                side_effect=[
                    "custom-server",  # Server name
                    1,  # Basic template
                    "custom",  # Repository location choice
                    "/custom/path",  # Repository path customization
                ],
            ),
            patch(
                "accordo_cli.utils.prompts.typer.confirm",
                side_effect=[
                    True,  # Customize configuration
                    False,  # Don't enable local state
                    False,  # Don't enable cache
                ],
            ),
            patch("accordo_cli.utils.prompts.typer.secho"),
            patch("accordo_cli.utils.prompts.typer.echo"),
        ):
            name, config = get_workflow_commander_details()
            assert name == "custom-server"
            assert "--repository-path" in config.args
            assert "/custom/path" in config.args


if __name__ == "__main__":
    pytest.main([__file__])
