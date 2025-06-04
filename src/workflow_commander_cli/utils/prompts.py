"""Interactive prompt utilities for configuration gathering."""

from pathlib import Path

import typer

from ..models.config import MCPServer
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
            typer.secho("❌ Invalid choice. Please select 1, 2, 3, or 4.", fg=typer.colors.RED)


def get_workflow_commander_details() -> tuple[str, MCPServer]:
    """Get workflow-commander server configuration details.
    
    Returns:
        Tuple of (server_name, MCPServer)
    """
    typer.secho("📦 Configuring Workflow Commander MCP Server", bold=True, fg=typer.colors.GREEN)
    typer.echo("Dynamic YAML-driven workflow guidance for AI agents")
    
    # Default configuration for workflow-commander
    default_name = "workflow-commander"
    default_command = "uvx"
    default_args = ["--from", "git+https://github.com/AndurilCode/workflow-commander@main", "dev-workflow-mcp"]
    
    # Ask for server name (with sensible default)
    server_name = typer.prompt("Server name", default=default_name)
    
    # Ask if user wants to customize the command
    use_default = typer.confirm("Use default installation command?", default=True)
    
    if use_default:
        command = default_command
        args = default_args
    else:
        typer.echo("Custom installation:")
        command = typer.prompt("Command", default=default_command)
        args_input = typer.prompt("Arguments (space-separated)", default=" ".join(default_args))
        args = args_input.split() if args_input.strip() else []
    
    # Create server configuration
    server_config = MCPServer(
        command=command,
        args=args
    )
    
    # Display configuration summary
    typer.secho("\n📋 Server Configuration Summary:", bold=True)
    typer.echo(f"Name: {server_name}")
    typer.echo(f"Command: {server_config.command}")
    if server_config.args:
        typer.echo(f"Arguments: {' '.join(server_config.args)}")
    
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
            custom_path = typer.prompt("Enter custom configuration file path", type=Path)
            return True, custom_path
        else:
            typer.secho(f"❌ Invalid choice. Please select 1-{max_choice}.", fg=typer.colors.RED)


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
    typer.echo("2. The workflow-commander server should now be available")


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