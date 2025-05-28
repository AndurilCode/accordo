"""Phase-specific workflow prompts with explicit next-prompt guidance."""

from fastmcp import Context, FastMCP
from pydantic import Field

from ..models.workflow_state import WorkflowPhase, WorkflowStatus
from ..utils.session_manager import (
    add_item_to_session,
    add_log_to_session,
    get_or_create_session,
    update_session_state,
)


def register_phase_prompts(mcp: FastMCP):
    """Register all phase-related prompts."""

    @mcp.tool()
    def init_workflow_guidance(task_description: str, ctx: Context) -> str:
        """Initialize a new development workflow with mandatory execution guidance."""
        # Get or create client session
        client_id = ctx.client_id if ctx else "default"
        session = get_or_create_session(client_id, task_description)
        
        # Add task to items if not already present
        if not any(item.description == task_description for item in session.items):
            add_item_to_session(client_id, task_description)
        
        return f"""🚀 INITIALIZING DEVELOPMENT WORKFLOW

        Task: {task_description}

        ACTIONS TO TAKE:
        1. Create or update workflow_state.md with:
        - Phase: INIT
        - Status: READY
        - CurrentItem: "{task_description}"

        2. Ensure project_config.md exists and is readable

        3. Append task to the Items table in workflow_state.md (do not delete any existing items):
        | 1 | {task_description} | pending |
        4. Move any existing Log section to ArchiveLog section

        ✅ WHEN COMPLETE:
        Call prompt: 'analyze_phase_guidance'
        Parameters: task_description="{task_description}"
"""

    @mcp.tool()
    def analyze_phase_guidance(
        task_description: str,
        ctx: Context,
        project_config_path: str = Field(
            default="project_config.md",
            description="Path to project configuration file",
        ),
    ) -> str:
        """Guide the agent through the ANALYZE phase with mandatory execution steps."""
        # Update session state
        client_id = ctx.client_id if ctx else "default"
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.ANALYZE,
            status=WorkflowStatus.RUNNING,
            current_item=task_description
        )
        
        return f"""📊 ANALYZE PHASE - NO CODING OR PLANNING YET

        Current task: {task_description}

        REQUIRED ACTIONS:
        1. Update workflow_state.md: Phase=ANALYZE, Status=RUNNING

        2. Read and understand {project_config_path}:
        - Note project structure
        - Identify test commands
        - Understand dependencies

        3. Read relevant existing code and documentation

        4. Write a clear requirements summary in ## Log section

        5. Update workflow_state.md: Status=READY

        ⚠️  IMPORTANT: NO code writing or planning in this phase!

        ✅ WHEN COMPLETE:
        Call prompt: 'blueprint_phase_guidance'
        Parameters: task_description="{task_description}", requirements_summary="<your analysis summary>"
"""

    @mcp.tool()
    def blueprint_phase_guidance(
        task_description: str,
        ctx: Context,
        requirements_summary: str = Field(
            description="Summary from the analysis phase"
        ),
    ) -> str:
        """Guide the agent through the BLUEPRINT phase with mandatory execution steps."""
        # Update session state
        client_id = ctx.client_id if ctx else "default"
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.BLUEPRINT,
            status=WorkflowStatus.RUNNING
        )
        
        return f"""📋 BLUEPRINT PHASE - PLANNING TIME

        Task: {task_description}
        Analysis: {requirements_summary}

        REQUIRED ACTIONS:
        1. Update workflow_state.md: Phase=BLUEPRINT, Status=RUNNING

        2. Decompose the task into ordered, atomic steps

        3. Write detailed plan in ## Plan section including:
        - File-by-file changes needed
        - Order of implementation
        - Test strategies
        - Risk mitigation

        4. Update workflow_state.md: Status=NEEDS_PLAN_APPROVAL

        5. Wait for user confirmation of the plan

        ✅ WHEN USER APPROVES PLAN:
        Call prompt: 'construct_phase_guidance'
        Parameters: task_description="{task_description}"

        ❌ IF USER REJECTS PLAN:
        Call prompt: 'revise_blueprint_guidance'
        Parameters: task_description="{task_description}", feedback="<user feedback>"
"""

    @mcp.tool()
    def construct_phase_guidance(task_description: str, ctx: Context) -> str:
        """Guide the agent through the CONSTRUCT phase with mandatory execution steps."""
        # Update session state
        client_id = ctx.client_id if ctx else "default"
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.CONSTRUCT,
            status=WorkflowStatus.RUNNING
        )
        
        return f"""🔨 CONSTRUCT PHASE - IMPLEMENTATION

        Task: {task_description}

        REQUIRED ACTIONS:
        1. Update workflow_state.md: Phase=CONSTRUCT, Status=RUNNING

        2. Follow the approved ## Plan exactly, step by step

        3. After EACH atomic change:
        a. Run test/linter commands from project_config.md
        b. Capture output in ## Log section
        c. Fix any issues before proceeding

        4. Log each step completion in ## Log

        5. When all plan steps complete: Update Status=READY

        ⚠️  CRITICAL: Follow the plan exactly - no deviations!

        ✅ WHEN ALL STEPS COMPLETE:
        Call prompt: 'validate_phase_guidance'
        Parameters: task_description="{task_description}"

        🚨 IF TESTS FAIL OR ERRORS OCCUR:
        Call prompt: 'error_recovery_guidance'
        Parameters: task_description="{task_description}", error_details="<error description>"
"""

    @mcp.tool()
    def validate_phase_guidance(task_description: str, ctx: Context) -> str:
        """Guide the agent through the VALIDATE phase with mandatory execution steps."""
        # Update session state
        client_id = ctx.client_id if ctx else "default"
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.VALIDATE,
            status=WorkflowStatus.RUNNING
        )
        
        return f"""✅ VALIDATE PHASE - FINAL VERIFICATION

        Task: {task_description}

        REQUIRED ACTIONS:
        1. Update workflow_state.md: Phase=VALIDATE, Status=RUNNING

        2. Run full test suite and E2E checks

        3. Verify all acceptance criteria are met

        4. Check code quality and documentation

        5. Log all validation results in ## Log

        ✅ IF ALL TESTS PASS:
        Call prompt: 'complete_workflow_guidance'
        Parameters: task_description="{task_description}"

        ❌ IF VALIDATION FAILS:
        Call prompt: 'fix_validation_issues_guidance'
        Parameters: task_description="{task_description}", issues="<validation issues>"
        """

    @mcp.tool()
    def revise_blueprint_guidance(
        task_description: str,
        ctx: Context,
        feedback: str = Field(description="User feedback on the rejected plan"),
    ) -> str:
        """Guide the agent to revise the blueprint with mandatory execution steps."""
        # Add feedback to session log
        client_id = ctx.client_id if ctx else "default"
        add_log_to_session(client_id, f"Plan revision requested: {feedback}")
        
        return f"""🔄 REVISING BLUEPRINT

        Task: {task_description}
        User Feedback: {feedback}

        REQUIRED ACTIONS:
        1. Update workflow_state.md: Phase=BLUEPRINT, Status=RUNNING

        2. Review user feedback carefully

        3. Revise the ## Plan section addressing all concerns:
        - Incorporate user suggestions
        - Fix identified issues
        - Improve clarity and detail

        4. Update workflow_state.md: Status=NEEDS_PLAN_APPROVAL

        5. Wait for user confirmation of revised plan

        ✅ WHEN USER APPROVES REVISED PLAN:
        Call prompt: 'construct_phase_guidance'
        Parameters: task_description="{task_description}"

        ❌ IF USER REJECTS REVISED PLAN:
        Call prompt: 'revise_blueprint_guidance'
        Parameters: task_description="{task_description}", feedback="<new user feedback>"
        """
