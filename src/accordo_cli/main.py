"""Main entry point for Workflow Commander CLI."""

from pathlib import Path

import typer

from .handlers.claude import ClaudeCodeHandler, ClaudeDesktopHandler
from .handlers.cursor import CursorHandler
from .handlers.vscode import VSCodeHandler
from .models.config import MCPServer
from .models.platform import Platform, PlatformInfo
from .utils.bootstrap import BootstrapManager
from .utils.prompts import (
    confirm_action,
    display_error_message,
    display_success_message,
    get_workflow_commander_details,
    select_config_location,
    select_platform,
)

# Create the main Typer application
app = typer.Typer(
    name="accordo",
    help="Configure MCP servers for AI coding platforms",
    rich_markup_mode="rich",
)


def version_callback(value: bool):
    if value:
        from . import __description__, __version__

        typer.echo(f"accordo {__version__}")
        typer.echo(__description__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """🔧 Workflow Commander CLI - Configure MCP servers for Cursor, Claude, and VS Code."""
    pass


@app.command()
def configure(
    platform: str | None = typer.Option(
        None, "--platform", "-p", help="Target platform (cursor, claude, vscode)"
    ),
    server_name: str | None = typer.Option(
        None, "--server", "-s", help="Server name to configure"
    ),
    config_path: Path | None = typer.Option(  # noqa: B008
        None, "--config", "-c", help="Path to configuration file"
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        "-y",
        help="Run in non-interactive mode with defaults",
    ),
):
    """🚀 Configure accordo MCP server for your preferred platform."""

    try:
        # Step 1: Platform Selection
        if platform:
            try:
                platform_enum = Platform(platform.lower())
            except ValueError:
                display_error_message(
                    f"Invalid platform '{platform}'",
                    ["Valid platforms: cursor, claude, vscode"],
                )
                raise typer.Exit(1)  # noqa: B904
        else:
            if non_interactive:
                display_error_message(
                    "Platform must be specified in non-interactive mode"
                )
                raise typer.Exit(1)
            platform_enum = select_platform()

        platform_info = PlatformInfo.for_platform(platform_enum)

        # Step 2: Server Configuration (hardcoded to accordo)
        if non_interactive:
            # Non-interactive mode - use defaults
            server_name_configured = server_name if server_name else "accordo"
            server_config = MCPServer(
                command="uvx",
                args=[
                    "accordo-workflow-mcp",
                ],
            )
        else:
            # Interactive mode - get accordo details
            server_name_configured, server_config = get_workflow_commander_details()

        # Step 3: Configuration Location
        if config_path:
            use_global = True
            custom_path = config_path
        else:
            if non_interactive:
                use_global = True
                custom_path = None
            else:
                use_global, custom_path = select_config_location(platform_info)

        # Step 4: Initialize appropriate handler
        if platform_enum == Platform.CURSOR:
            handler = CursorHandler()
        elif platform_enum == Platform.CLAUDE_DESKTOP:
            handler = ClaudeDesktopHandler()
        elif platform_enum == Platform.CLAUDE_CODE:
            handler = ClaudeCodeHandler()
        elif platform_enum == Platform.VSCODE:
            handler = VSCodeHandler()
        else:
            display_error_message(f"Unsupported platform: {platform_enum}")
            raise typer.Exit(1)

        # Step 5: Determine config path
        if custom_path:
            final_config_path = custom_path
        else:
            final_config_path = handler.get_config_path(use_global=use_global)

        # Step 6: Confirmation
        if not non_interactive:
            typer.secho("\n📋 Configuration Summary:", bold=True)
            typer.echo(f"Platform: {platform_info.name}")
            typer.echo(f"Server: {server_name_configured}")
            typer.echo(
                f"Command: {server_config.command} {' '.join(server_config.args)}"
            )
            typer.echo(f"Config file: {final_config_path}")

            if not confirm_action("Proceed with configuration?"):
                typer.echo("Configuration cancelled.")
                raise typer.Exit()

        # Step 7: Add server to configuration
        success = handler.add_server(
            name=server_name_configured,
            server=server_config,
            config_path=final_config_path,
            use_global=use_global,
        )

        if success:
            display_success_message(
                platform=platform_info.name,
                server_name=server_name_configured,
                config_path=final_config_path,
            )
        else:
            display_error_message("Failed to save configuration")
            raise typer.Exit(1)

    except Exception as e:
        display_error_message(str(e))
        raise typer.Exit(1)  # noqa: B904


@app.command()
def list_platforms():
    """List supported AI coding platforms and their configuration paths."""

    typer.secho("🎯 Supported AI Coding Platforms", bold=True)
    typer.echo()

    all_platforms = PlatformInfo.get_all_platforms()

    for platform, info in all_platforms.items():
        typer.secho(f"{info.name} ({platform.value})", bold=True)
        typer.echo(f"  {info.description}")
        typer.echo(f"  Global config: {info.locations.get_global_path()}")
        if info.locations.project_path:
            typer.echo(f"  Project config: ./{info.locations.project_path}")
        if info.documentation_url:
            typer.echo(f"  Documentation: {info.documentation_url}")
        typer.echo("")


@app.command()
def list_servers(
    platform: str | None = typer.Option(
        None,
        "--platform",
        "-p",
        help="Platform to list servers for (cursor, claude, vscode)",
    ),
    config_path: Path | None = typer.Option(  # noqa: B008
        None, "--config", "-c", help="Path to configuration file"
    ),
):
    """📋 List configured MCP servers."""

    try:
        # Platform selection
        if platform:
            try:
                platform_enum = Platform(platform.lower())
            except ValueError:
                display_error_message(
                    f"Invalid platform '{platform}'",
                    ["Valid platforms: cursor, claude, vscode"],
                )
                raise typer.Exit(1)  # noqa: B904
        else:
            platform_enum = select_platform()

        platform_info = PlatformInfo.for_platform(platform_enum)

        # Initialize handler
        if platform_enum == Platform.CURSOR:
            handler = CursorHandler()
        elif platform_enum == Platform.CLAUDE:
            handler = ClaudeDesktopHandler()
        elif platform_enum == Platform.VSCODE:
            handler = VSCodeHandler()
        else:
            display_error_message(f"Unsupported platform: {platform_enum}")
            raise typer.Exit(1)

        # Determine config path
        if config_path:
            final_config_path = config_path
        else:
            final_config_path = handler.get_config_path(use_global=True)

        # List servers
        servers = handler.list_existing_servers(final_config_path)

        if not servers:
            typer.secho(
                f"📭 No MCP servers configured for {platform_info.name}",
                fg=typer.colors.YELLOW,
            )
            typer.echo(f"Configuration file: {final_config_path}")
        else:
            typer.secho(
                f"📋 Configured MCP servers for {platform_info.name}:", bold=True
            )
            typer.echo(f"Configuration file: {final_config_path}")
            typer.echo()
            for i, server_name in enumerate(servers, 1):
                typer.echo(f"{i}. {server_name}")

    except Exception as e:
        display_error_message(str(e))
        raise typer.Exit(1)  # noqa: B904


@app.command()
def remove_server(
    server_name: str = typer.Argument(..., help="Name of server to remove"),
    platform: str | None = typer.Option(
        None,
        "--platform",
        "-p",
        help="Platform to remove server from (cursor, claude, vscode)",
    ),
    config_path: Path | None = typer.Option(  # noqa: B008
        None, "--config", "-c", help="Path to configuration file"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """🗑️ Remove an MCP server from configuration."""

    try:
        # Platform selection
        if platform:
            try:
                platform_enum = Platform(platform.lower())
            except ValueError:
                display_error_message(
                    f"Invalid platform '{platform}'",
                    ["Valid platforms: cursor, claude, vscode"],
                )
                raise typer.Exit(1)  # noqa: B904
        else:
            platform_enum = select_platform()

        platform_info = PlatformInfo.for_platform(platform_enum)

        # Initialize handler
        if platform_enum == Platform.CURSOR:
            handler = CursorHandler()
        elif platform_enum == Platform.CLAUDE:
            handler = ClaudeDesktopHandler()
        elif platform_enum == Platform.VSCODE:
            handler = VSCodeHandler()
        else:
            display_error_message(f"Unsupported platform: {platform_enum}")
            raise typer.Exit(1)

        # Determine config path
        if config_path:
            final_config_path = config_path
        else:
            final_config_path = handler.get_config_path(use_global=True)

        # Confirmation
        if not force:
            typer.secho(
                f"⚠️ Remove server '{server_name}' from {platform_info.name}?",
                fg=typer.colors.YELLOW,
            )
            typer.echo(f"Configuration file: {final_config_path}")

            if not confirm_action("Are you sure?", default=False):
                typer.echo("Removal cancelled.")
                raise typer.Exit()

        # Remove server
        success = handler.remove_server(
            name=server_name, config_path=final_config_path, use_global=True
        )

        if success:
            typer.secho(
                f"✅ Server '{server_name}' removed successfully!",
                fg=typer.colors.GREEN,
            )
        else:
            display_error_message(f"Failed to remove server '{server_name}'")
            raise typer.Exit(1)

    except Exception as e:
        display_error_message(str(e))
        raise typer.Exit(1)  # noqa: B904


@app.command()
def validate(
    platform: str | None = typer.Option(
        None, "--platform", "-p", help="Platform to validate (cursor, claude, vscode)"
    ),
    config_path: Path | None = typer.Option(  # noqa: B008
        None, "--config", "-c", help="Path to configuration file"
    ),
):
    """✅ Validate MCP server configurations."""

    try:
        # Platform selection
        if platform:
            try:
                platform_enum = Platform(platform.lower())
            except ValueError:
                display_error_message(
                    f"Invalid platform '{platform}'",
                    ["Valid platforms: cursor, claude, vscode"],
                )
                raise typer.Exit(1)  # noqa: B904
        else:
            platform_enum = select_platform()

        platform_info = PlatformInfo.for_platform(platform_enum)

        # Initialize handler
        if platform_enum == Platform.CURSOR:
            handler = CursorHandler()
        elif platform_enum == Platform.CLAUDE:
            handler = ClaudeDesktopHandler()
        elif platform_enum == Platform.VSCODE:
            handler = VSCodeHandler()
        else:
            display_error_message(f"Unsupported platform: {platform_enum}")
            raise typer.Exit(1)

        # Determine config path
        if config_path:
            final_config_path = config_path
        else:
            final_config_path = handler.get_config_path(use_global=True)

        # Load and validate configuration
        if not final_config_path.exists():
            display_error_message(f"Configuration file not found: {final_config_path}")
            raise typer.Exit(1)

        config = handler.load_config(final_config_path)
        servers = handler.get_servers_from_config(config)

        typer.secho(f"🔍 Validating {platform_info.name} configuration:", bold=True)
        typer.echo(f"Configuration file: {final_config_path}")
        typer.echo()

        all_valid = True

        for server_name, server_config in servers.items():
            typer.secho(f"📦 {server_name}:", bold=True)

            validation_errors = handler.validate_server_config(server_config)
            if validation_errors:
                typer.echo("  ❌ Validation errors:")
                for error in validation_errors:
                    typer.echo(f"    - {error}")
                all_valid = False
            else:
                typer.echo("  ✅ Valid configuration")
                typer.echo(f"    Command: {server_config.command}")
                if server_config.args:
                    typer.echo(f"    Arguments: {' '.join(server_config.args)}")
                if server_config.env:
                    typer.echo(f"    Environment: {len(server_config.env)} variables")

        if all_valid:
            typer.secho(
                "\n✅ All configurations are valid!", bold=True, fg=typer.colors.GREEN
            )
        else:
            typer.secho(
                "\n❌ Some configurations have errors", bold=True, fg=typer.colors.RED
            )
            raise typer.Exit(1)

    except Exception as e:
        display_error_message(str(e))
        raise typer.Exit(1)  # noqa: B904


@app.command("bootstrap-rules")
def bootstrap_rules(
    assistants: list[str] = typer.Argument(  # noqa: B008
        None, help="Assistant types to deploy to (cursor, copilot, claude, all)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing content if present"
    ),
):
    """🚀 Deploy workflow system guidelines to AI assistant configuration files."""

    try:
        # Default to 'all' if no assistants specified
        if not assistants:
            assistants = ["all"]

        # Validate assistant types
        valid_assistants = {"cursor", "copilot", "claude", "all"}
        for assistant in assistants:
            if assistant not in valid_assistants:
                display_error_message(
                    f"Invalid assistant type '{assistant}'",
                    [f"Valid options: {', '.join(sorted(valid_assistants))}"],
                )
                raise typer.Exit(1)

        # Initialize bootstrap manager
        bootstrap_manager = BootstrapManager()

        # Track deployment results
        success_count = 0
        total_count = 0

        # Process each assistant type
        for assistant in assistants:
            if assistant == "all":
                # Deploy to all assistants
                results = bootstrap_manager.deploy_all(force=force)
                total_count += len(results)
                success_count += sum(1 for result in results.values() if result)
            else:
                # Deploy to specific assistant
                total_count += 1
                if bootstrap_manager.deploy_to_assistant(assistant, force=force):
                    success_count += 1

        # Summary
        typer.echo()
        typer.secho("📊 Deployment Summary:", bold=True, fg=typer.colors.BLUE)
        typer.echo(f"Successful deployments: {success_count}")
        typer.echo(f"Total attempted: {total_count}")

        if success_count == total_count:
            typer.secho(
                "✅ All deployments completed successfully!",
                bold=True,
                fg=typer.colors.GREEN,
            )
        else:
            typer.secho(
                "⚠️ Some deployments encountered issues. Check output above.",
                bold=True,
                fg=typer.colors.YELLOW,
            )
            raise typer.Exit(1)

    except Exception as e:
        display_error_message(str(e))
        raise typer.Exit(1)  # noqa: B904


if __name__ == "__main__":
    app()
