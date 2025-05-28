"""Main MCP server implementation."""

from fastmcp import FastMCP, Context

from .prompts.management_prompts import register_management_prompts
from .prompts.phase_prompts import register_phase_prompts
from .prompts.transition_prompts import register_transition_prompts
from .utils import session_manager
from .utils.session_manager import get_session_stats, export_session_to_markdown

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


@mcp.tool()
def get_session_statistics() -> str:
    """Get statistics about current workflow sessions."""
    stats = get_session_stats()
    
    result = f"""📊 **Workflow Session Statistics**

**Total Active Sessions**: {stats['total_sessions']}

**Sessions by Phase**:
"""
    for phase, count in stats['sessions_by_phase'].items():
        result += f"- {phase}: {count}\n"
    
    result += "\n**Sessions by Status**:\n"
    for status, count in stats['sessions_by_status'].items():
        result += f"- {status}: {count}\n"
    
    return result


@mcp.tool()
def export_client_session(ctx: Context = None) -> str:
    """Export current client's workflow session as markdown."""
    client_id = ctx.client_id if ctx else "default"
    markdown = export_session_to_markdown(client_id)
    
    if markdown:
        return f"""📄 **Session Export for Client: {client_id}**

```markdown
{markdown}
```
"""
    else:
        return f"❌ No session found for client: {client_id}"


@mcp.tool()
def health_check_sessions() -> str:
    """Health check for session management system."""
    try:
        stats = get_session_stats()
        total_sessions = stats['total_sessions']
        
        # Check if session system is working
        test_client = "health_check_test"
        from .utils.session_manager import create_session, delete_session
        
        # Create and delete test session
        test_session = create_session(test_client, "Health check test")
        if test_session and delete_session(test_client):
            return f"""✅ **Session Health Check: PASSED**

- Session creation: ✅ Working
- Session deletion: ✅ Working  
- Active sessions: {total_sessions}
- System status: 🟢 Healthy
"""
        else:
            return """❌ **Session Health Check: FAILED**

- Session operations: ❌ Not working properly
- System status: 🔴 Unhealthy
"""
    
    except Exception as e:
        return f"""❌ **Session Health Check: ERROR**

- Error: {str(e)}
- System status: 🔴 Error state
"""


@mcp.tool()
def cleanup_old_sessions(hours: int = 24) -> str:
    """Clean up completed sessions older than specified hours."""
    from .utils.session_manager import cleanup_completed_sessions
    
    try:
        removed_count = cleanup_completed_sessions(hours)
        return f"""🧹 **Session Cleanup Complete**

- Sessions removed: {removed_count}
- Cleanup criteria: Completed sessions older than {hours} hours
- Status: ✅ Success
"""
    except Exception as e:
        return f"""❌ **Session Cleanup Error**

- Error: {str(e)}
- Status: 🔴 Failed
"""


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
