"""Phase-specific workflow prompts with explicit next-prompt guidance."""

from fastmcp import Context, FastMCP
from pydantic import Field

from ..models.workflow_state import WorkflowPhase, WorkflowStatus
from ..utils.session_manager import (
    add_item_to_session,
    add_log_to_session,
    export_session_to_markdown,
    get_or_create_session,
    update_session_state,
)


def register_phase_prompts(mcp: FastMCP):
    """Register all phase-related prompts."""

    @mcp.tool()
    def init_workflow_guidance(task_description: str, ctx: Context) -> str:
        """Initialize a new development workflow with mandatory execution guidance."""
        # Get or create client session
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        session = get_or_create_session(client_id, task_description)
        
        # Add task to items if not already present
        if not any(item.description == task_description for item in session.items):
            add_item_to_session(client_id, task_description)
        
        # Update session to INIT state
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.INIT,
            status=WorkflowStatus.READY,
            current_item=task_description
        )
        add_log_to_session(client_id, f"🚀 WORKFLOW INITIALIZED: {task_description}")
        
        # Get updated state to return
        updated_state = export_session_to_markdown(client_id)

        return f"""🚀 WORKFLOW INITIALIZED

**Task:** {task_description}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → INIT
- Status → READY
- CurrentItem → {task_description}
- Task added to Items table
- Workflow initialized

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```

**📋 SETUP REQUIREMENTS:**
- Ensure project_config.md exists and is readable
- Verify project structure is accessible

**🔄 NEXT STEP:**
Call: `analyze_phase_guidance`
Parameters: task_description="{task_description}"

🎯 **Workflow initialized automatically - ready to begin analysis!**
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
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.ANALYZE,
            status=WorkflowStatus.RUNNING,
            current_item=task_description
        )
        add_log_to_session(client_id, f"📊 ANALYZE PHASE STARTED: {task_description}")
        
        # Get updated state to return
        updated_state = export_session_to_markdown(client_id)
        
        return f"""📊 ANALYZE PHASE - NO CODING OR PLANNING YET

**Task:** {task_description}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → ANALYZE
- Status → RUNNING
- Analysis phase initiated

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```

**📊 REQUIRED ACTIONS:**
1. Read and understand {project_config_path}:
   - Note project structure
   - Identify test commands  
   - Understand dependencies

2. Read relevant existing code and documentation

3. Write clear requirements summary in your analysis

4. Log findings as you discover them

**⚠️ IMPORTANT:** NO code writing or planning in this phase!

**🔄 WHEN ANALYSIS COMPLETE:**
Call: `blueprint_phase_guidance`
Parameters: task_description="{task_description}", requirements_summary="<your analysis summary>"

🎯 **Analysis phase started automatically - focus on understanding requirements!**
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
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.BLUEPRINT,
            status=WorkflowStatus.RUNNING
        )
        add_log_to_session(client_id, f"📋 BLUEPRINT PHASE STARTED: {task_description}")
        add_log_to_session(client_id, f"Analysis Summary: {requirements_summary}")
        
        # Get updated state to return
        updated_state = export_session_to_markdown(client_id)
        
        return f"""📋 BLUEPRINT PHASE - PLANNING TIME

**Task:** {task_description}
**Analysis:** {requirements_summary}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → BLUEPRINT
- Status → RUNNING
- Analysis summary logged

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```

**📋 REQUIRED ACTIONS:**
1. Decompose task into ordered, atomic steps

2. Write detailed implementation plan including:
   - File-by-file changes needed
   - Order of implementation
   - Test strategies
   - Risk mitigation

3. Create clear, actionable steps that can be executed systematically

**⚠️ PLAN APPROVAL REQUIRED:**
Once you complete the plan, update status to NEEDS_PLAN_APPROVAL and wait for user confirmation.

**✅ WHEN USER APPROVES PLAN:**
Call: `construct_phase_guidance`
Parameters: task_description="{task_description}"

**❌ IF USER REJECTS PLAN:**
Call: `revise_blueprint_guidance`
Parameters: task_description="{task_description}", feedback="<user feedback>"

🎯 **Blueprint phase started automatically - create detailed implementation plan!**
"""

    @mcp.tool()
    def construct_phase_guidance(task_description: str, ctx: Context) -> str:
        """Guide the agent through the CONSTRUCT phase with mandatory execution steps."""
        # Update session state
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.CONSTRUCT,
            status=WorkflowStatus.RUNNING
        )
        add_log_to_session(client_id, f"🔨 CONSTRUCT PHASE STARTED: {task_description}")
        
        # Get updated state to return
        updated_state = export_session_to_markdown(client_id)
        
        return f"""🔨 CONSTRUCT PHASE - IMPLEMENTATION

**Task:** {task_description}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → CONSTRUCT
- Status → RUNNING
- Implementation phase initiated

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```

**🔨 REQUIRED ACTIONS:**
1. Follow the approved plan exactly, step by step

2. **After EACH atomic change:**
   - Run test/linter commands from project_config.md
   - Capture output and log results
   - Fix any issues before proceeding

3. Log each step completion with detailed notes

4. Maintain quality and test coverage throughout

**⚠️ CRITICAL:** Follow the plan exactly - no deviations without replanning!

**✅ WHEN ALL STEPS COMPLETE:**
Call: `validate_phase_guidance`
Parameters: task_description="{task_description}"

**🚨 IF TESTS FAIL OR ERRORS OCCUR:**
Call: `error_recovery_guidance`
Parameters: task_description="{task_description}", error_details="<error description>"

🎯 **Construction phase started automatically - implement plan systematically!**
"""

    @mcp.tool()
    def validate_phase_guidance(task_description: str, ctx: Context) -> str:
        """Guide the agent through the VALIDATE phase with mandatory execution steps."""
        # Update session state
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.VALIDATE,
            status=WorkflowStatus.RUNNING
        )
        add_log_to_session(client_id, f"✅ VALIDATE PHASE STARTED: {task_description}")
        
        # Get updated state to return
        updated_state = export_session_to_markdown(client_id)
        
        return f"""✅ VALIDATE PHASE - FINAL VERIFICATION

**Task:** {task_description}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → VALIDATE
- Status → RUNNING
- Validation phase initiated

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```

**✅ REQUIRED ACTIONS:**
1. Run full test suite and E2E checks

2. Verify all acceptance criteria are met

3. Check code quality and documentation

4. Perform integration testing

5. Log all validation results with detailed findings

**✅ IF ALL TESTS PASS:**
Call: `complete_workflow_guidance`
Parameters: task_description="{task_description}"

**❌ IF VALIDATION FAILS:**
Call: `fix_validation_issues_guidance`
Parameters: task_description="{task_description}", issues="<validation issues>"

🎯 **Validation phase started automatically - verify implementation quality!**
"""

    @mcp.tool()
    def revise_blueprint_guidance(
        task_description: str,
        ctx: Context,
        feedback: str = Field(description="User feedback on the rejected plan"),
    ) -> str:
        """Guide the agent to revise the blueprint with mandatory execution steps."""
        # Update session state and add feedback to log
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"
        update_session_state(
            client_id=client_id,
            phase=WorkflowPhase.BLUEPRINT,
            status=WorkflowStatus.RUNNING
        )
        add_log_to_session(client_id, f"🔄 PLAN REVISION REQUESTED: {feedback}")
        
        # Get updated state to return
        updated_state = export_session_to_markdown(client_id)
        
        return f"""🔄 REVISING BLUEPRINT

**Task:** {task_description}
**User Feedback:** {feedback}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → BLUEPRINT
- Status → RUNNING  
- Revision feedback logged

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```

**🔄 REQUIRED ACTIONS:**
1. Review user feedback carefully

2. Revise the implementation plan addressing all concerns:
   - Incorporate user suggestions
   - Fix identified issues  
   - Improve clarity and detail
   - Address any missing requirements

3. Update plan with revised approach

**⚠️ PLAN APPROVAL REQUIRED:**
Once you complete the revised plan, update status to NEEDS_PLAN_APPROVAL and wait for user confirmation.

**✅ WHEN USER APPROVES REVISED PLAN:**
Call: `construct_phase_guidance`
Parameters: task_description="{task_description}"

**❌ IF USER REJECTS REVISED PLAN:**
Call: `revise_blueprint_guidance` 
Parameters: task_description="{task_description}", feedback="<new user feedback>"

🎯 **Plan revision initiated automatically - address feedback systematically!**
"""
