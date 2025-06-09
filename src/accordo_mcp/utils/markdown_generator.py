"""Markdown generator for workflow state visualization."""

from ..models.workflow_state import WorkflowState


def generate_workflow_markdown(state: WorkflowState) -> str:
    """Generate markdown representation of workflow state.

    This function delegates to the WorkflowState.to_markdown() method
    but provides a standalone function interface for consistency.
    """
    return state.to_markdown()


def format_workflow_state_for_display(
    state: WorkflowState, include_metadata: bool = False
) -> str:
    """Generate a formatted markdown with optional metadata section."""
    markdown = state.to_markdown()

    if include_metadata:
        metadata_section = f"""
## Metadata
- **Client ID**: {state.client_id}
- **Created**: {state.created_at.strftime("%Y-%m-%d %H:%M:%S")}
- **Last Updated**: {state.last_updated.strftime("%Y-%m-%d %H:%M:%S")}
- **Items Count**: {len(state.items)}
- **Log Length**: {len(state.log)} characters
- **Archive Log Length**: {len(state.archive_log)} characters

"""
        # Insert metadata before the ArchiveLog section
        lines = markdown.split("\n")
        archive_log_index = -1

        for i, line in enumerate(lines):
            if line.strip() == "## ArchiveLog":
                archive_log_index = i
                break

        if archive_log_index >= 0:
            lines.insert(archive_log_index, metadata_section.strip())
            markdown = "\n".join(lines)
        else:
            markdown += metadata_section

    return markdown


def generate_summary_markdown(state: WorkflowState) -> str:
    """Generate a concise summary of workflow state."""
    completed_items = [item for item in state.items if item.status == "completed"]
    pending_items = [item for item in state.items if item.status == "pending"]

    # Calculate progress percentage
    total_items = len(state.items)
    completed_count = len(completed_items)
    progress_pct = (completed_count / total_items * 100) if total_items > 0 else 0.0

    summary = f"""# Workflow Summary

**Client**: {state.client_id}  
**Phase**: {state.phase}  
**Status**: {state.status}  
**Current Item**: {state.current_item or "None"}

## Progress
- **Total Items**: {total_items}
- **Completed**: {completed_count}
- **Pending**: {len(pending_items)}
- **Progress**: {completed_count}/{total_items} ({progress_pct:.1f}%)

## Recent Activity
{state.log[-500:] if state.log else "No recent activity"}

## Next Steps
"""

    if pending_items:
        next_item = pending_items[0]
        summary += f"- Next item: {next_item.description}\n"
    else:
        summary += "- All items completed\n"

    return summary


def export_session_report(state: WorkflowState) -> str:
    """Generate a comprehensive report for session export."""
    return f"""# Workflow Session Report

**Generated**: {state.last_updated.strftime("%Y-%m-%d %H:%M:%S")}

{generate_workflow_markdown(state)}

---

{generate_summary_markdown(state)}
"""
