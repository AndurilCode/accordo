"""Main MCP server implementation."""

from fastmcp import FastMCP

from .prompts.management_prompts import register_management_prompts
from .prompts.phase_prompts import register_phase_prompts
from .prompts.transition_prompts import register_transition_prompts

# Initialize the MCP server
mcp = FastMCP("Development Workflow")

# Register all workflow prompts
register_phase_prompts(mcp)
register_management_prompts(mcp)
register_transition_prompts(mcp)


@mcp.tool()
def hello_workflow() -> str:
    """A simple hello world workflow tool."""
    return "Hello from dev workflow MCP!"


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
