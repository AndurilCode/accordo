"""Transition prompts for state management and workflow file operations."""

from fastmcp import Context, FastMCP

from ..models.workflow_state import WorkflowPhase, WorkflowStatus
from ..utils.session_manager import (
    add_log_to_session,
    export_session_to_markdown,
    get_or_create_session,
    update_session_state,
)


def register_transition_prompts(mcp: FastMCP):
    """Register all transition-related prompts."""

    @mcp.tool()
    def update_workflow_state_guidance(
        phase: str,
        status: str,
        ctx: Context,
        current_item: str | None = None,
        log_entry: str | None = None,
    ) -> str:
        """Guide agent to update the workflow state with mandatory execution steps."""
        # Get client session and update state
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        
        # Convert string parameters to enums
        try:
            phase_enum = WorkflowPhase(phase)
            status_enum = WorkflowStatus(status)
        except ValueError:
            # Fallback for invalid enum values
            phase_enum = WorkflowPhase.INIT
            status_enum = WorkflowStatus.READY
        
        # Update session state
        update_session_state(
            client_id=client_id,
            phase=phase_enum,
            status=status_enum,
            current_item=current_item
        )
        
        # Add log entry if provided
        if log_entry:
            add_log_to_session(client_id, log_entry)
        
        # Get updated state to return
        updated_state = export_session_to_markdown(client_id)
        
        return f"""📝 WORKFLOW STATE UPDATED

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → {phase}
- Status → {status}
- CurrentItem → {current_item or "null"}
{f"- Log entry added: {log_entry}" if log_entry else ""}

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```

**🔄 NEXT STEP:**
Return to your previous workflow prompt as instructed.

🎯 **State updated automatically - continue with your workflow!**
"""

    @mcp.tool()
    def get_workflow_state_markdown(ctx: Context) -> str:
        """Guide agent to get current workflow state as markdown for debugging/display."""
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        markdown = export_session_to_markdown(client_id)
        
        if markdown:
            return f"""📋 CURRENT WORKFLOW STATE

**Client:** {client_id}

```markdown
{markdown}
```

💡 **This shows the complete current workflow state from the centralized session.**
"""
        else:
            return f"❌ No workflow session found for client: {client_id}"
