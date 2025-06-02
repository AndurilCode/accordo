"""Main MCP server implementation."""

from fastmcp import FastMCP

from .prompts.discovery_prompts import register_discovery_prompts
from .prompts.phase_prompts import register_phase_prompts

# Initialize the MCP server
mcp = FastMCP("Development Workflow")

# Register essential YAML workflow prompts only
register_phase_prompts(mcp)
register_discovery_prompts(mcp)


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
