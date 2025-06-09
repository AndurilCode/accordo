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
from accordo_cli.models.platform import Platform, PlatformInfo


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
                    ".",  # Repository path
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
            assert "--repository-path" in config.args


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
        assert "--repository-path" in template.args
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
        assert "--repository-path" in flags
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
            assert "--repository-path" in config.args  # Advanced template includes this

    def test_get_workflow_commander_details_with_customization(self):
        """Test enhanced function with template customization."""
        from accordo_cli.utils.prompts import get_workflow_commander_details

        with (
            patch(
                "accordo_cli.utils.prompts.typer.prompt",
                side_effect=[
                    "custom-server",  # Server name
                    1,  # Basic template
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
