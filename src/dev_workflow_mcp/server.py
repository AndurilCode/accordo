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
  
  # Enable local session file storage in markdown format
  %(prog)s --enable-local-state-file --local-state-file-format MD
  
  # Enable local session file storage in JSON format  
  %(prog)s --repository-path ../my-project --enable-local-state-file --local-state-file-format JSON
  
  # Enable cache mode for persistent workflow states
  %(prog)s --enable-cache-mode --cache-embedding-model all-mpnet-base-v2
  
  # Enable both file storage and cache mode
  %(prog)s --enable-local-state-file --enable-cache-mode --cache-db-path ./cache
""",
    )

    parser.add_argument(
        "--repository-path",
        type=str,
        help="Path to the repository root where .workflow-commander folder should be located. "
        "Defaults to current directory if not specified.",
        metavar="PATH",
    )

    parser.add_argument(
        "--enable-local-state-file",
        action="store_true",
        help="Enable automatic synchronization of workflow state to local files in "
        ".workflow-commander/sessions/ directory. When enabled, every workflow state "
        "change is automatically persisted to the filesystem.",
    )

    parser.add_argument(
        "--local-state-file-format",
        type=str,
        choices=["MD", "JSON", "md", "json"],
        default="MD",
        help="Format for local state files when --enable-local-state-file is enabled. "
        "Supports 'MD' for markdown or 'JSON' for structured JSON format. (default: %(default)s)",
        metavar="FORMAT",
    )

    parser.add_argument(
        "--session-retention-hours",
        type=int,
        default=168,  # 7 days
        help="Hours to keep completed sessions before cleanup. Minimum 1 hour. (default: %(default)s = 7 days)",
        metavar="HOURS",
    )

    parser.add_argument(
        "--disable-session-archiving",
        action="store_true",
        help="Disable archiving of session files before cleanup. By default, completed sessions "
        "are archived with a completion timestamp before being cleaned up.",
    )

    parser.add_argument(
        "--enable-cache-mode",
        action="store_true",
        help="Enable ChromaDB-based caching for workflow state persistence between sessions. "
        "When enabled, workflow states are stored in a vector database for semantic search and "
        "session restoration after MCP server restarts.",
    )

    parser.add_argument(
        "--cache-db-path",
        type=str,
        help="Path to ChromaDB database directory. If not specified, defaults to "
        ".workflow-commander/cache in the repository directory.",
        metavar="PATH",
    )

    parser.add_argument(
        "--cache-collection-name",
        type=str,
        default="workflow_states",
        help="Name of ChromaDB collection for workflow states. (default: %(default)s)",
        metavar="NAME",
    )

    parser.add_argument(
        "--cache-embedding-model",
        type=str,
        default="all-mpnet-base-v2",
        help="Sentence transformer model for semantic embeddings. (default: %(default)s)",
        metavar="MODEL",
    )

    parser.add_argument(
        "--cache-max-results",
        type=int,
        default=50,
        help="Maximum number of results for semantic search queries. (default: %(default)s)",
        metavar="COUNT",
    )

    return parser


def main():
    """Run the MCP server."""
    # Parse command-line arguments
    parser = create_arg_parser()
    args = parser.parse_args()

    # Create configuration
    try:
        config = ServerConfig(
            repository_path=args.repository_path,
            enable_local_state_file=args.enable_local_state_file,
            local_state_file_format=args.local_state_file_format.upper(),
            session_retention_hours=args.session_retention_hours,
            enable_session_archiving=not args.disable_session_archiving,
            enable_cache_mode=args.enable_cache_mode,
            cache_db_path=args.cache_db_path,
            cache_collection_name=args.cache_collection_name,
            cache_embedding_model=args.cache_embedding_model,
            cache_max_results=args.cache_max_results,
        )
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
