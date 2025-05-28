"""Management prompts for workflow completion, iteration, and error handling."""

from fastmcp import Context, FastMCP
from pydantic import Field

from ..models.workflow_state import WorkflowPhase, WorkflowStatus
from ..utils.session_manager import (
    add_log_to_session,
    get_session,
    mark_item_completed_in_session,
    update_session_state,
)


def register_management_prompts(mcp: FastMCP):
    """Register all management-related prompts."""

    @mcp.tool()
    def complete_workflow_guidance(task_description: str, ctx: Context) -> str:
        """Guide the agent through workflow completion with mandatory execution steps."""
        # Update session to completed status
        client_id = ctx.client_id if ctx else "default"
        session = get_session(client_id)
        
        if session:
            update_session_state(client_id, status=WorkflowStatus.COMPLETED)
            # Mark current item as completed if it matches task description
            for item in session.items:
                if item.description == task_description and item.status == "pending":
                    mark_item_completed_in_session(client_id, item.id)
                    break
        
        return f"""🎉 COMPLETING WORKFLOW

        Task: {task_description}

        REQUIRED ACTIONS:
        1. Update workflow_state.md: Status=COMPLETED

        2. Mark item as 'completed' in ## Items table

        3. Update project changelog (call changelog_update_guidance if needed)

        4. Archive current ## Log to ## ArchiveLog if > 5000 chars

        5. Check for next pending items in workflow

        ✅ IF MORE ITEMS EXIST:
        Call prompt: 'iterate_next_item_guidance'
        Parameters: None

        ✅ IF ALL ITEMS COMPLETE:
        Call prompt: 'finalize_workflow_guidance'
        Parameters: None

        🎯 WORKFLOW COMPLETE FOR THIS TASK!
"""

    @mcp.tool()
    def iterate_next_item_guidance(ctx: Context) -> str:
        """Guide the agent to process the next workflow item with mandatory execution steps."""
        # Find next pending item and update session
        client_id = ctx.client_id if ctx else "default"
        session = get_session(client_id)
        
        next_item = None
        if session:
            next_item = session.get_next_pending_item()
            if next_item:
                update_session_state(
                    client_id=client_id,
                    phase=WorkflowPhase.ANALYZE,
                    status=WorkflowStatus.READY,
                    current_item=next_item.description
                )
        
        return """🔄 ITERATING TO NEXT ITEM

        REQUIRED ACTIONS:
        1. Find next 'pending' item in ## Items table

        2. Update workflow_state.md:
        - CurrentItem: <next item description>
        - Phase: ANALYZE
        - Status: READY

        3. Clear ## Log section (move to ## ArchiveLog if needed)

        ✅ WHEN READY:
        Call prompt: 'analyze_phase_guidance'
        Parameters: task_description="<next item description>"
"""

    @mcp.tool()
    def finalize_workflow_guidance(ctx: Context) -> str:
        """Guide the agent to finalize the entire workflow with mandatory execution steps."""
        # Reset session to initial state
        client_id = ctx.client_id if ctx else "default"
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.INIT,
            status=WorkflowStatus.READY,
            current_item=None
        )
        
        return """🏁 FINALIZING WORKFLOW

        REQUIRED ACTIONS:
        1. Update workflow_state.md: Phase=INIT, Status=READY, CurrentItem=null

        2. Archive final ## Log to ## ArchiveLog

        3. Create workflow summary in ## Log:
        - Total items completed
        - Key achievements
        - Final state

        4. Ensure all files are saved and committed (if using version control)

        🎉 ENTIRE WORKFLOW COMPLETE!
        No further prompts needed - workflow is finished.
"""

    @mcp.tool()
    def error_recovery_guidance(
        task_description: str,
        ctx: Context,
        error_details: str = Field(
            description="Description of the error that occurred"
        ),  
    ) -> str:
        """Guide the agent through error recovery with mandatory execution steps."""
        # Log error in session
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        add_log_to_session(client_id, f"ERROR: {error_details}")
        
        return f"""🚨 ERROR RECOVERY MODE

        Task: {task_description}
        Error: {error_details}

        REQUIRED ACTIONS:
        1. Log error details in ## Log section

        2. Analyze the error and determine fix strategy

        3. Choose recovery path:
        - Simple fix: Fix and continue current phase
        - Complex issue: Return to BLUEPRINT phase
        - Critical error: Escalate to user

        ✅ FOR SIMPLE FIXES:
        Call prompt: 'construct_phase_guidance'
        Parameters: task_description="{task_description}"

        🔄 FOR COMPLEX ISSUES:
        Call prompt: 'blueprint_phase_guidance'
        Parameters: task_description="{task_description}", requirements_summary="Error occurred: {error_details}"

        ⚠️  FOR CRITICAL ERRORS:
        Call prompt: 'escalate_to_user_guidance'
        Parameters: task_description="{task_description}", error_details="{error_details}"
"""

    @mcp.tool()
    def fix_validation_issues_guidance(
        task_description: str,
        ctx: Context,
        issues: str = Field(description="Description of validation issues found"),
    ) -> str:
        """Guide the agent to fix validation issues with mandatory execution steps."""
        # Log validation issues in session
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        add_log_to_session(client_id, f"VALIDATION ISSUES: {issues}")
        
        return f"""🔧 FIXING VALIDATION ISSUES

        Task: {task_description}
        Issues: {issues}

        REQUIRED ACTIONS:
        1. Log validation issues in ## Log section

        2. Analyze each issue and determine fixes needed

        3. Apply fixes systematically:
        - Fix one issue at a time
        - Test after each fix
        - Log progress

        4. Re-run validation after all fixes

        ✅ WHEN ALL ISSUES FIXED:
        Call prompt: 'validate_phase_guidance'
        Parameters: task_description="{task_description}"

        🚨 IF ISSUES PERSIST:
        Call prompt: 'error_recovery_guidance'
        Parameters: task_description="{task_description}", error_details="Persistent validation issues: {issues}"
        """

    @mcp.tool()
    def escalate_to_user_guidance(
        task_description: str,
        ctx: Context,
        error_details: str = Field(
            description="Critical error details requiring user intervention"
        ),
    ) -> str:
        """Guide the agent to escalate critical issues to the user with mandatory execution steps."""
        # Update session to error status and log
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        update_session_state(client_id, status=WorkflowStatus.ERROR)
        add_log_to_session(client_id, f"CRITICAL ERROR - ESCALATED: {error_details}")
        
        return f"""⚠️  ESCALATING TO USER

        Task: {task_description}
        Critical Error: {error_details}

        REQUIRED ACTIONS:
        1. Update workflow_state.md: Status=ERROR

        2. Log complete error details in ## Log section

        3. Prepare clear summary for user:
        - What was being attempted
        - What went wrong
        - What has been tried
        - What user input is needed

        4. Present the issue to the user and wait for guidance

        ✅ WHEN USER PROVIDES GUIDANCE:
        Follow user instructions and call appropriate prompt based on their guidance.

        🔄 TO RETRY AFTER USER FIX:
        Call prompt: 'construct_phase_guidance'
        Parameters: task_description="{task_description}"
"""

    @mcp.tool()
    def changelog_update_guidance(
        task_description: str,
        ctx: Context,
        project_config_path: str = Field(
            default="project_config.md",
            description="Path to project configuration file",
        ),        
    ) -> str:
        """Guide the agent to update the project changelog with mandatory execution steps."""
        # Log changelog update in session
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        add_log_to_session(client_id, f"Updating project changelog for: {task_description}")
        
        return f"""📝 UPDATING CHANGELOG

        Task: {task_description}

        REQUIRED ACTIONS:
        1. Read {project_config_path} to locate ## Changelog section

        2. Create concise changelog entry:
        - One sentence summary of completed work
        - Focus on user-visible changes
        - Use past tense

        3. Insert new entry as first item after ## Changelog heading

        4. Maintain existing changelog format

        5. Save the updated file

        ✅ WHEN COMPLETE:
        Return to calling prompt or complete workflow as appropriate.
        """
