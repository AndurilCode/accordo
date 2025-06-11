"""Interactive prompt utilities for configuration gathering."""

from pathlib import Path

import click
import typer

from ..models.config import (
    ConfigurationBuilder,
    ConfigurationTemplate,
    MCPServer,
    TemplateConfig,
)
from ..models.platform import Platform, PlatformInfo


def confirm_action(message: str, default: bool = True) -> bool:
    """Confirm an action with the user.

    Args:
        message: The confirmation message to display
        default: Default value if user just presses enter

    Returns:
        Boolean confirmation result
    """
    return typer.confirm(message, default=default)


def select_platform() -> Platform:
    """Select target platform interactively.

    Returns:
        Selected Platform enum value
    """
    typer.secho("🎯 Select target platform:", bold=True, fg=typer.colors.CYAN)
    typer.echo("1. Cursor")
    typer.echo("2. Claude Desktop")
    typer.echo("3. Claude Code")
    typer.echo("4. VS Code")

    while True:
        choice = typer.prompt("Enter your choice (1-4)", type=int)

        if choice == 1:
            return Platform.CURSOR
        elif choice == 2:
            return Platform.CLAUDE_DESKTOP
        elif choice == 3:
            return Platform.CLAUDE_CODE
        elif choice == 4:
            return Platform.VSCODE
        else:
            typer.secho(
                "❌ Invalid choice. Please select 1, 2, 3, or 4.", fg=typer.colors.RED
            )


def select_configuration_template() -> ConfigurationTemplate:
    """Select configuration template interactively.

    Returns:
        Selected ConfigurationTemplate enum value
    """
    typer.secho("📦 Select configuration template:", bold=True, fg=typer.colors.CYAN)
    typer.echo()

    # Display template options with descriptions
    basic_template = TemplateConfig.get_basic_template()
    advanced_template = TemplateConfig.get_advanced_template()
    cache_template = TemplateConfig.get_cache_enabled_template()

    typer.echo("1. 🚀 Basic Setup")
    typer.echo(f"   {basic_template.description}")
    typer.echo("   • Minimal configuration for getting started")
    typer.echo()

    typer.echo("2. ⚙️  Advanced Setup")
    typer.echo(f"   {advanced_template.description}")
    typer.echo("   • Includes local state files, cache mode, and comprehensive options")
    typer.echo()

    typer.echo("3. 🧠 Cache-Enabled Setup")
    typer.echo(f"   {cache_template.description}")
    typer.echo("   • Optimized for semantic workflow analysis and persistence")
    typer.echo()

    typer.echo("4. 🛠️  Custom Configuration")
    typer.echo("   Build your own configuration step by step")
    typer.echo()

    while True:
        choice = typer.prompt("Enter your choice (1-4)", type=int)

        if choice == 1:
            return ConfigurationTemplate.BASIC
        elif choice == 2:
            return ConfigurationTemplate.ADVANCED
        elif choice == 3:
            return ConfigurationTemplate.CACHE_ENABLED
        elif choice == 4:
            return None  # Custom configuration
        else:
            typer.secho(
                "❌ Invalid choice. Please select 1, 2, 3, or 4.", fg=typer.colors.RED
            )


def customize_configuration(builder: ConfigurationBuilder) -> ConfigurationBuilder:
    """Allow user to customize configuration options.

    Args:
        builder: ConfigurationBuilder instance to customize

    Returns:
        Customized ConfigurationBuilder
    """
    typer.secho("🔧 Customize Configuration", bold=True, fg=typer.colors.YELLOW)
    typer.echo(
        "You can modify the following options (press Enter to keep current values):"
    )
    typer.echo()

    # Repository location choice
    has_global = any(opt.flag == "--global" for opt in builder.options)
    has_local = any(opt.flag == "--local" for opt in builder.options)
    has_repository_path = any(
        opt.flag == "--repository-path" for opt in builder.options
    )

    if has_global or has_local or has_repository_path:
        current_choice = (
            "global" if has_global else ("local" if has_local else "custom")
        )
    else:
        current_choice = "global"  # Default

    repo_choice = typer.prompt(
        "Repository location (global/local/custom)",
        default=current_choice,
        type=click.Choice(["global", "local", "custom"]),
    )

    if repo_choice == "global":
        # Remove any existing repo options and add global flag
        builder.options = [
            opt
            for opt in builder.options
            if opt.flag not in ["--global", "--local", "--repository-path"]
        ]
        builder.add_global_flag()
    elif repo_choice == "local":
        # Remove any existing repo options and add local flag
        builder.options = [
            opt
            for opt in builder.options
            if opt.flag not in ["--global", "--local", "--repository-path"]
        ]
        builder.add_local_flag()
    else:  # custom
        # Ask for custom path and use deprecated repository-path option
        current_repo_path = next(
            (opt.value for opt in builder.options if opt.flag == "--repository-path"),
            ".",
        )
        new_repo_path = typer.prompt("Repository path", default=current_repo_path)
        builder.options = [
            opt
            for opt in builder.options
            if opt.flag not in ["--global", "--local", "--repository-path"]
        ]
        builder.add_repository_path(new_repo_path)

    # Local state file
    has_local_state = any(
        opt.flag == "--enable-local-state-file" for opt in builder.options
    )
    enable_local_state = typer.confirm(
        "Enable local state file storage?", default=has_local_state
    )

    if enable_local_state:
        current_format = next(
            (
                opt.value
                for opt in builder.options
                if opt.flag == "--local-state-file-format"
            ),
            "JSON",
        )
        format_choice = typer.prompt(
            "State file format (JSON/MD)", default=current_format
        )
        builder.enable_local_state_file(format_choice.upper())

        # Session retention
        current_retention = next(
            (
                opt.value
                for opt in builder.options
                if opt.flag == "--session-retention-hours"
            ),
            "72",
        )
        retention_hours = typer.prompt(
            "Session retention hours", default=int(current_retention), type=int
        )
        builder.set_session_retention(retention_hours)

    # Cache mode
    has_cache = any(opt.flag == "--enable-cache-mode" for opt in builder.options)
    enable_cache = typer.confirm(
        "Enable cache mode for semantic search?", default=has_cache
    )

    if enable_cache:
        current_model = next(
            (
                opt.value
                for opt in builder.options
                if opt.flag == "--cache-embedding-model"
            ),
            "all-MiniLM-L6-v2",
        )
        embedding_model = typer.prompt("Embedding model", default=current_model)
        builder.enable_cache_mode(embedding_model)

        # Cache path
        current_cache_path = next(
            (opt.value for opt in builder.options if opt.flag == "--cache-db-path"),
            ".accordo/cache",
        )
        cache_path = typer.prompt("Cache database path", default=current_cache_path)
        builder.set_cache_path(cache_path)

        # Max results
        current_max_results = next(
            (opt.value for opt in builder.options if opt.flag == "--cache-max-results"),
            "50",
        )
        max_results = typer.prompt(
            "Maximum search results", default=int(current_max_results), type=int
        )
        builder.set_cache_max_results(max_results)

    return builder


def build_custom_configuration() -> ConfigurationBuilder:
    """Build a custom configuration from scratch.

    Returns:
        ConfigurationBuilder with custom configuration
    """
    typer.secho("🛠️  Building Custom Configuration", bold=True, fg=typer.colors.MAGENTA)
    typer.echo("Let's build your configuration step by step:")
    typer.echo()

    builder = ConfigurationBuilder()

    # Repository location choice
    repo_choice = typer.prompt(
        "Repository location (global=home directory, local=current directory, custom=specify path)",
        default="global",
        type=click.Choice(["global", "local", "custom"]),
    )

    if repo_choice == "global":
        builder.add_global_flag()
        typer.echo("  → Using home directory (~/.accordo/)")
    elif repo_choice == "local":
        builder.add_local_flag()
        typer.echo("  → Using current directory (./.accordo/)")
    else:  # custom
        repo_path = typer.prompt("Repository path", default=".")
        builder.add_repository_path(repo_path)
        typer.echo(f"  → Using custom path: {repo_path}/.accordo/")

    # Local state file
    if typer.confirm("Enable local state file storage?", default=True):
        format_choice = typer.prompt("State file format (JSON/MD)", default="JSON")
        builder.enable_local_state_file(format_choice.upper())

        retention_hours = typer.prompt("Session retention hours", default=72, type=int)
        builder.set_session_retention(retention_hours)

    # Cache mode
    if typer.confirm("Enable cache mode for semantic search?", default=True):
        embedding_model = typer.prompt("Embedding model", default="all-MiniLM-L6-v2")
        builder.enable_cache_mode(embedding_model)

        cache_path = typer.prompt("Cache database path", default=".accordo/cache")
        builder.set_cache_path(cache_path)

        max_results = typer.prompt("Maximum search results", default=50, type=int)
        builder.set_cache_max_results(max_results)

    return builder


def get_workflow_commander_details() -> tuple[str, MCPServer]:
    """Get accordo server configuration details with guided setup.

    Returns:
        Tuple of (server_name, MCPServer)
    """
    typer.secho(
        "📦 Configuring Workflow Commander MCP Server", bold=True, fg=typer.colors.GREEN
    )
    typer.echo("Dynamic YAML-driven workflow guidance for AI agents")
    typer.echo()

    # Server name
    server_name = typer.prompt("Server name", default="accordo")

    # Template selection
    template = select_configuration_template()

    if template is None:
        # Custom configuration
        builder = build_custom_configuration()
    else:
        # Use template
        builder = ConfigurationBuilder(template)

        # Ask if user wants to customize
        if typer.confirm(
            "Would you like to customize this configuration?", default=False
        ):
            builder = customize_configuration(builder)

    # Build final configuration
    server_config = builder.build()

    # Display configuration summary
    typer.secho("\n📋 Server Configuration Summary:", bold=True)
    typer.echo(f"Name: {server_name}")
    typer.echo(f"Command: {server_config.command}")
    if server_config.args:
        typer.echo("Arguments:")
        for i, arg in enumerate(server_config.args):
            if i == 0 or arg.startswith("--"):
                typer.echo(f"  {arg}")
            else:
                typer.echo(f"    {arg}")

    return server_name, server_config


def select_config_location(platform_info: PlatformInfo) -> tuple[bool, Path | None]:
    """Select configuration file location.

    Args:
        platform_info: Platform information containing location details

    Returns:
        Tuple of (use_global, custom_path)
        - use_global: True for global config, False for project-specific
        - custom_path: Custom path if specified, None otherwise
    """
    typer.secho("📁 Select configuration location:", bold=True, fg=typer.colors.CYAN)

    # Show available options
    typer.echo(f"1. Global configuration: {platform_info.locations.get_global_path()}")

    if platform_info.locations.project_path:
        typer.echo(f"2. Project-specific: {platform_info.locations.project_path}")
        typer.echo("3. Custom path")
        max_choice = 3
    else:
        typer.echo("2. Custom path")
        max_choice = 2

    while True:
        choice = typer.prompt(f"Enter your choice (1-{max_choice})", type=int)

        if choice == 1:
            return True, None
        elif choice == 2 and platform_info.locations.project_path:
            return False, None
        elif (choice == 2 and not platform_info.locations.project_path) or choice == 3:
            # Custom path
            custom_path = typer.prompt(
                "Enter custom configuration file path", type=Path
            )
            return True, custom_path
        else:
            typer.secho(
                f"❌ Invalid choice. Please select 1-{max_choice}.", fg=typer.colors.RED
            )


def display_success_message(platform: str, server_name: str, config_path: Path) -> None:
    """Display success message after configuration.

    Args:
        platform: Target platform name
        server_name: Name of configured server
        config_path: Path to configuration file
    """
    typer.secho("✅ Configuration successful!", bold=True, fg=typer.colors.GREEN)
    typer.echo(f"Platform: {platform}")
    typer.echo(f"Server: {server_name}")
    typer.echo(f"Configuration saved to: {config_path}")
    typer.echo()
    typer.secho("🚀 Next steps:", bold=True)
    typer.echo("1. Restart your editor to load the new MCP server")
    typer.echo("2. The accordo server should now be available")


def display_error_message(error: str, suggestions: list[str] | None = None) -> None:
    """Display error message with optional suggestions.

    Args:
        error: Error message to display
        suggestions: Optional list of suggestions for fixing the error
    """
    typer.secho(f"❌ Error: {error}", fg=typer.colors.RED)

    if suggestions:
        typer.echo()
        typer.secho("💡 Suggestions:", bold=True)
        for suggestion in suggestions:
            typer.echo(f"  • {suggestion}")
