"""Main MCP server implementation."""

from fastmcp import FastMCP

from .prompts.management_prompts import register_management_prompts
from .prompts.phase_prompts import register_phase_prompts
from .prompts.project_prompts import register_project_prompts
from .prompts.transition_prompts import register_transition_prompts

# Initialize the MCP server
mcp = FastMCP("Development Workflow")

# Register all workflow prompts
register_phase_prompts(mcp)
register_management_prompts(mcp)
register_transition_prompts(mcp)
register_project_prompts(mcp)


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
