"""Main MCP server implementation."""

import argparse

from fastmcp import FastMCP

from .config import ServerConfig
from .prompts.discovery_prompts import register_discovery_prompts
from .prompts.phase_prompts import register_phase_prompts


def create_arg_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Development Workflow MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default repository path (current directory)
  %(prog)s
  
  # Run with specific repository path
  %(prog)s --repository-path /path/to/my/project
  
  # Run with relative repository path
  %(prog)s --repository-path ../my-project
""",
    )

    parser.add_argument(
        "--repository-path",
        type=str,
        help="Path to the repository root where .workflow-commander folder should be located. "
        "Defaults to current directory if not specified.",
        metavar="PATH",
    )

    return parser


def main():
    """Run the MCP server."""
    # Parse command-line arguments
    parser = create_arg_parser()
    args = parser.parse_args()

    # Create configuration
    try:
        config = ServerConfig(repository_path=args.repository_path)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    # Initialize the MCP server
    mcp = FastMCP("Development Workflow")

    # Register essential YAML workflow prompts with configuration
    register_phase_prompts(mcp, config)
    register_discovery_prompts(mcp, config)

    # Run the server
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    exit(main())
