"""Phase-specific workflow prompts with explicit next-prompt guidance."""

import re

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
from ..utils.state_manager import get_file_operation_instructions


def validate_task_description(value: str) -> str:
    """
    Validate task_description parameter format.

    Expected format: "Action: Brief description"
    Where Action is a verb (Add, Fix, Implement, Refactor, Update, Create, Remove, etc.)

    Args:
        value: The task description to validate

    Returns:
        The validated task description

    Raises:
        ValueError: If the format is invalid
    """
    if not value or not isinstance(value, str):
        raise ValueError("task_description must be a non-empty string")

    # Check for the "Action: Description" pattern
    pattern = r"^[A-Z][a-zA-Z]+:\s+.+"
    if not re.match(pattern, value.strip()):
        raise ValueError(
            "task_description must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', "
            "'Implement: OAuth login', 'Refactor: database queries'. "
            f"Received: '{value}'"
        )

    return value.strip()


def register_phase_prompts(mcp: FastMCP):
    """Register all phase-related prompts."""

    # ==================== CONSOLIDATED SMART TOOLS (PROPOSAL 4) ====================

    @mcp.tool()
    def workflow_guidance(
        ctx: Context,
        action: str = Field(
            description="Workflow action: 'start' (init+analyze), 'plan' (blueprint), 'build' (construct+validate), 'revise', 'next' (auto-determine)"
        ),
        task_description: str = Field(
            description="Task description in format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', "
            "'Implement: OAuth login', 'Refactor: database queries'",
        ),
        context: str = Field(
            default="",
            description="Additional context for actions like 'plan' (requirements summary) or 'revise' (user feedback)",
        ),
        options: str = Field(
            default="",
            description="Optional parameters like project_config_path for specific actions",
        ),
    ) -> str:
        """Consolidated smart workflow guidance tool with mandatory execution steps for all phase operations."""
        # Validate task description format
        task_description = validate_task_description(task_description)

        # Get client session
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"

        # Route to appropriate action handler
        if action.lower() == "start":
            return _handle_start_action(client_id, task_description, options)
        elif action.lower() == "plan":
            return _handle_plan_action(client_id, task_description, context)
        elif action.lower() == "build":
            return _handle_build_action(client_id, task_description)
        elif action.lower() == "revise":
            return _handle_revise_action(client_id, task_description, context)
        elif action.lower() == "next":
            return _handle_next_action(client_id, task_description)
        else:
            raise ValueError(
                f"Unknown action: {action}. Valid actions: start, plan, build, revise, next"
            )

    @mcp.tool()
    def workflow_state(
        ctx: Context,
        operation: str = Field(
            description="State operation: 'get' (current status), 'update' (modify state), 'reset' (clear state)"
        ),
        updates: str = Field(
            default="",
            description='JSON string with state updates for \'update\' operation. Example: \'{"phase": "CONSTRUCT", "status": "RUNNING"}\'',
        ),
    ) -> str:
        """Smart workflow state management tool with guided operations."""
        client_id = ctx.client_id if ctx and ctx.client_id is not None else "default"

        if operation.lower() == "get":
            return _handle_get_state(client_id)
        elif operation.lower() == "update":
            return _handle_update_state(client_id, updates)
        elif operation.lower() == "reset":
            return _handle_reset_state(client_id)
        else:
            raise ValueError(
                f"Unknown operation: {operation}. Valid operations: get, update, reset"
            )


# ==================== ACTION HANDLERS ====================


def _handle_start_action(client_id: str, task_description: str, options: str) -> str:
    """Handle 'start' action - combines init and analyze phases."""
    # Initialize workflow
    session = get_or_create_session(client_id, task_description)

    # Add task to items if not already present
    if not any(item.description == task_description for item in session.items):
        add_item_to_session(client_id, task_description)

    # Update to INIT state
    update_session_state(
        client_id=client_id,
        phase=WorkflowPhase.INIT,
        status=WorkflowStatus.READY,
        current_item=task_description,
    )
    add_log_to_session(client_id, f"🚀 WORKFLOW INITIALIZED: {task_description}")

    # Transition to ANALYZE phase
    update_session_state(
        client_id=client_id,
        phase=WorkflowPhase.ANALYZE,
        status=WorkflowStatus.RUNNING,
        current_item=task_description,
    )
    add_log_to_session(client_id, f"📊 ANALYZE PHASE STARTED: {task_description}")

    # Get project config path from options or use default
    project_config_path = ".workflow-commander/project_config.md"
    if options and isinstance(options, str) and "project_config_path=" in options:
        project_config_path = (
            options.split("project_config_path=")[1].split(",")[0].strip()
        )

    # Get updated state and file operations
    updated_state = export_session_to_markdown(client_id)
    file_operations = get_file_operation_instructions(client_id)

    return f"""🚀 WORKFLOW STARTED - ANALYZE PHASE

**Task:** {task_description}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → ANALYZE 
- Status → RUNNING
- Workflow initialized and analysis started

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```{file_operations}

**🎯 PHASE OBJECTIVE:** Thoroughly understand requirements and existing codebase WITHOUT any coding or planning.

**📊 MANDATORY ACTIONS - EXECUTE IN ORDER:**

**1. PROJECT CONFIGURATION ANALYSIS** ⚠️ REQUIRED
   - MUST read and parse {project_config_path} completely
   - MUST identify all test commands and dependencies
   - MUST understand project structure and conventions
   - MUST note any existing quality gates or validation requirements

**2. CODEBASE EXPLORATION** ⚠️ REQUIRED
   - MUST read relevant existing code files
   - MUST understand current architecture and patterns
   - MUST identify integration points and dependencies
   - MUST note any existing documentation or comments

**3. REQUIREMENTS ANALYSIS** ⚠️ REQUIRED
   - MUST break down the task into clear, specific requirements
   - MUST identify affected components and systems
   - MUST understand scope and boundaries
   - MUST identify potential risks or complexities

**4. DOCUMENTATION REVIEW** ⚠️ REQUIRED
   - MUST read any relevant README, docs, or comments
   - MUST understand existing patterns and conventions
   - MUST identify any constraints or limitations

**🔍 COMPLETION VALIDATION CHECKLIST:**
Before proceeding, you MUST verify ALL of the following:

✅ **Understanding Criteria:**
- [ ] Can explain the task requirements in your own words
- [ ] Can identify all files and components that will be affected
- [ ] Can describe the current system architecture relevant to the task
- [ ] Can list all dependencies and integration points
- [ ] Can identify potential risks or edge cases

**🔄 WHEN ANALYSIS COMPLETE:**
Call: `workflow_guidance`
Parameters: action="plan", task_description="{task_description}", context="<comprehensive requirements summary>"

🎯 **Combined init+analyze started - understand requirements thoroughly!**
"""


def _handle_plan_action(client_id: str, task_description: str, context: str) -> str:
    """Handle 'plan' action - blueprint phase."""
    if not context:
        raise ValueError(
            "'plan' action requires context parameter with requirements summary from analysis"
        )

    # Update to BLUEPRINT phase
    update_session_state(
        client_id=client_id,
        phase=WorkflowPhase.BLUEPRINT,
        status=WorkflowStatus.RUNNING,
    )
    add_log_to_session(client_id, f"📋 BLUEPRINT PHASE STARTED: {task_description}")
    add_log_to_session(client_id, f"Analysis Summary: {context}")

    # Get updated state and file operations
    updated_state = export_session_to_markdown(client_id)
    file_operations = get_file_operation_instructions(client_id)

    return f"""📋 BLUEPRINT PHASE - DETAILED IMPLEMENTATION PLANNING

**Task:** {task_description}

**Analysis Summary:**
{context}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → BLUEPRINT
- Status → RUNNING
- Planning phase initiated

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```{file_operations}

**🎯 PHASE OBJECTIVE:** Create a comprehensive, step-by-step implementation plan.

**📋 MANDATORY PLANNING PROCESS - EXECUTE IN ORDER:**

**1. SOLUTION ARCHITECTURE** ⚠️ REQUIRED
   - MUST define overall approach and strategy
   - MUST identify all components to be created/modified
   - MUST specify integration points and dependencies
   - MUST consider scalability and maintainability
   - MUST align with existing architecture patterns

**2. DETAILED STEP BREAKDOWN** ⚠️ REQUIRED
   - MUST create atomic, ordered implementation steps
   - MUST specify files to create/modify for each step
   - MUST include verification commands for each step
   - MUST estimate complexity and potential risks
   - MUST plan rollback procedures for each step

**3. QUALITY ASSURANCE PLAN** ⚠️ REQUIRED
   - MUST specify testing strategy and test cases
   - MUST define acceptance criteria for each component
   - MUST plan integration testing approach
   - MUST specify validation and verification steps

**4. IMPLEMENTATION PLAN DOCUMENTATION** ⚠️ REQUIRED
   - MUST write comprehensive plan under **## Plan** section
   - MUST include pseudocode or high-level diff outlines
   - MUST specify success criteria and rollback procedures
   - MUST document assumptions and constraints

**⚠️ PLAN APPROVAL REQUIRED:**
After completing your plan, you MUST:
1. Set status to NEEDS_PLAN_APPROVAL
2. Wait for user confirmation before proceeding

**✅ WHEN USER APPROVES PLAN:**
Call: `workflow_guidance`
Parameters: action="build", task_description="{task_description}"

**❌ IF USER REJECTS PLAN:**
Call: `workflow_guidance`
Parameters: action="revise", task_description="{task_description}", context="<user feedback>"

🎯 **Blueprint phase started - create comprehensive implementation plan!**
"""


def _handle_build_action(client_id: str, task_description: str) -> str:
    """Handle 'build' action - construct and validate phases."""
    # Update to CONSTRUCT phase
    update_session_state(
        client_id=client_id,
        phase=WorkflowPhase.CONSTRUCT,
        status=WorkflowStatus.RUNNING,
    )
    add_log_to_session(client_id, f"🔨 CONSTRUCT PHASE STARTED: {task_description}")

    # Get updated state and file operations
    updated_state = export_session_to_markdown(client_id)
    file_operations = get_file_operation_instructions(client_id)

    return f"""🔨 BUILD PHASE - SYSTEMATIC IMPLEMENTATION

**Task:** {task_description}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → CONSTRUCT
- Status → RUNNING
- Implementation phase initiated

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```{file_operations}

**🎯 PHASE OBJECTIVE:** Execute the approved plan exactly with mandatory verification after each atomic change.

**🔨 MANDATORY EXECUTION PROCESS - FOLLOW EXACTLY:**

**FOR EACH STEP IN YOUR PLAN:**

**1. PRE-STEP VERIFICATION** ⚠️ REQUIRED
   - MUST confirm all prerequisites are met
   - MUST verify current state matches step expectations
   - MUST check that previous steps completed successfully
   - MUST ensure all required files/dependencies exist

**2. ATOMIC IMPLEMENTATION** ⚠️ REQUIRED
   - MUST implement ONLY the current step (no ahead-jumping)
   - MUST make changes exactly as specified in plan
   - MUST follow existing code patterns and conventions
   - MUST maintain backwards compatibility unless specified otherwise

**3. MANDATORY VERIFICATION** ⚠️ REQUIRED
   - MUST run the verification command specified in step
   - MUST capture and log complete command output
   - MUST run project linting: `ruff check .`
   - MUST run project formatting check: `ruff format --check .`
   - MUST verify success criteria from plan are met

**4. QUALITY VALIDATION** ⚠️ REQUIRED
   - MUST check that code follows project standards
   - MUST verify no new linting errors introduced
   - MUST ensure all imports resolve correctly
   - MUST confirm no circular dependencies created

**🚨 ERROR RECOVERY:**
If ANY step fails, call: `workflow_guidance`
Parameters: action="next", task_description="{task_description}"

**✅ WHEN ALL STEPS COMPLETE:**
Automatically transition to validation phase

🎯 **Build phase started - implement systematically with verification!**
"""


def _handle_revise_action(client_id: str, task_description: str, context: str) -> str:
    """Handle 'revise' action - revise blueprint based on feedback."""
    if not context:
        raise ValueError(
            "'revise' action requires context parameter with user feedback"
        )

    # Update session state and add feedback to log
    update_session_state(
        client_id=client_id,
        phase=WorkflowPhase.BLUEPRINT,
        status=WorkflowStatus.RUNNING,
    )
    add_log_to_session(client_id, f"🔄 PLAN REVISION REQUESTED: {context}")

    # Get updated state and file operations
    updated_state = export_session_to_markdown(client_id)
    file_operations = get_file_operation_instructions(client_id)

    return f"""🔄 REVISING BLUEPRINT

**Task:** {task_description}
**User Feedback:** {context}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → BLUEPRINT
- Status → RUNNING  
- Revision feedback logged

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```{file_operations}

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
Call: `workflow_guidance`
Parameters: action="build", task_description="{task_description}"

🎯 **Plan revision initiated - address feedback systematically!**
"""


def _handle_next_action(client_id: str, task_description: str) -> str:
    """Handle 'next' action - auto-determine next step based on current state."""
    session = get_or_create_session(client_id, task_description)
    current_phase = session.phase
    current_status = session.status

    # Determine next action based on current state
    if current_phase == WorkflowPhase.INIT or current_phase == WorkflowPhase.ANALYZE:
        return _handle_start_action(client_id, task_description, "")
    elif (
        current_phase == WorkflowPhase.BLUEPRINT
        and current_status == WorkflowStatus.RUNNING
    ):
        return f"""📋 BLUEPRINT IN PROGRESS

**Current State:** {current_phase} - {current_status}

Continue working on your implementation plan. When complete:

**✅ FOR PLAN APPROVAL:**
Call: `workflow_guidance`
Parameters: action="build", task_description="{task_description}"

**❌ IF PLAN NEEDS REVISION:**
Call: `workflow_guidance`
Parameters: action="revise", task_description="{task_description}", context="<user feedback>"
"""
    elif current_phase == WorkflowPhase.CONSTRUCT:
        return _handle_build_action(client_id, task_description)
    elif current_phase == WorkflowPhase.VALIDATE:
        return _handle_validate_action(client_id, task_description)
    else:
        # Get current state for context
        updated_state = export_session_to_markdown(client_id)
        return f"""🔍 CURRENT WORKFLOW STATE

**Task:** {task_description}

**📋 CURRENT STATE:**
```markdown
{updated_state}
```

**🔄 AVAILABLE ACTIONS:**
- `action="start"` - Initialize and start analysis
- `action="plan"` - Create implementation blueprint  
- `action="build"` - Execute construction and validation
- `action="revise"` - Revise plan based on feedback

Please specify the appropriate action based on your current needs.
"""


def _handle_validate_action(client_id: str, task_description: str) -> str:
    """Handle validation phase."""
    # Update to VALIDATE phase
    update_session_state(
        client_id=client_id,
        phase=WorkflowPhase.VALIDATE,
        status=WorkflowStatus.RUNNING,
    )
    add_log_to_session(client_id, f"✅ VALIDATE PHASE STARTED: {task_description}")

    # Get updated state and file operations
    updated_state = export_session_to_markdown(client_id)
    file_operations = get_file_operation_instructions(client_id)

    return f"""✅ VALIDATE PHASE - COMPREHENSIVE QUALITY VERIFICATION

**Task:** {task_description}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → VALIDATE
- Status → RUNNING
- Validation phase initiated

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```{file_operations}

**🎯 PHASE OBJECTIVE:** Verify implementation quality, functionality, and requirements compliance.

**✅ MANDATORY VALIDATION PROCESS - EXECUTE IN ORDER:**

**1. FUNCTIONAL TESTING** ⚠️ REQUIRED
   - MUST run complete test suite
   - MUST verify all new functionality works correctly
   - MUST test edge cases and error conditions
   - MUST ensure no regression in existing functionality

**2. QUALITY VERIFICATION** ⚠️ REQUIRED
   - MUST run linting checks: `ruff check .`
   - MUST verify formatting: `ruff format --check .`
   - MUST check type annotations (if applicable)
   - MUST verify code follows project standards

**3. INTEGRATION TESTING** ⚠️ REQUIRED
   - MUST verify backwards compatibility
   - MUST test integration with existing systems
   - MUST ensure no circular dependencies
   - MUST validate all imports resolve correctly

**4. REQUIREMENTS VERIFICATION** ⚠️ REQUIRED
   - MUST verify all original requirements implemented
   - MUST check success criteria are met
   - MUST validate acceptance criteria satisfied
   - MUST ensure user expectations met

**5. DOCUMENTATION VALIDATION** ⚠️ REQUIRED
   - MUST verify code is properly documented
   - MUST check API documentation complete
   - MUST ensure usage examples provided (if needed)
   - MUST validate project documentation updated

**✅ IF ALL VALIDATIONS PASS:**
Call: `complete_workflow_guidance`
Parameters: task_description="{task_description}"

**❌ IF VALIDATION FAILS:**
Call: `fix_validation_issues_guidance`
Parameters: task_description="{task_description}", issues="<comprehensive failure report>"

🎯 **Validation phase started - verify comprehensive implementation quality!**
"""


# ==================== STATE MANAGEMENT HANDLERS ====================


def _handle_get_state(client_id: str) -> str:
    """Get current workflow state."""
    updated_state = export_session_to_markdown(client_id)
    return f"""📋 CURRENT WORKFLOW STATE

```markdown
{updated_state}
```

**🔄 REQUIRED ACTIONS:**
- `workflow_guidance(action="start", ...)` - Initialize and analyze
- `workflow_guidance(action="plan", ...)` - Create implementation plan
- `workflow_guidance(action="build", ...)` - Execute construction
- `workflow_guidance(action="revise", ...)` - Revise plan with feedback
- `workflow_guidance(action="next", ...)` - Auto-determine next step

**📞 Call:** Use `workflow_guidance` with appropriate action to proceed with workflow.
"""


def _handle_update_state(client_id: str, updates: str) -> str:
    """Update workflow state with provided changes."""
    import json

    try:
        update_data = json.loads(updates) if updates else {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in updates parameter: {updates}") from e

    # Apply updates to session
    phase = WorkflowPhase(update_data["phase"]) if "phase" in update_data else None
    status = WorkflowStatus(update_data["status"]) if "status" in update_data else None

    current_item = update_data.get("current_item")

    if phase or status or current_item:
        update_session_state(
            client_id=client_id,
            phase=phase,
            status=status,
            current_item=current_item,
        )

    # Add log entry if provided
    if "log_entry" in update_data:
        add_log_to_session(client_id, update_data["log_entry"])

    # Return updated state
    updated_state = export_session_to_markdown(client_id)
    return f"""✅ STATE UPDATED

**Updates Applied:** {update_data}

**📋 UPDATED WORKFLOW STATE:**
```markdown
{updated_state}
```
"""


def _handle_reset_state(client_id: str) -> str:
    """Reset workflow state to initial state."""
    # This would need to be implemented based on session manager capabilities
    # For now, return information about manual reset
    return """🔄 WORKFLOW RESET

**Manual Reset Required:**
To reset the workflow state, you can:

1. **Soft Reset**: Call `workflow_guidance(action="start", ...)` with a new task
2. **Hard Reset**: Delete session data (implementation dependent)

**Current State Access:**
Call: `workflow_state(operation="get")` to view current state before reset.
"""
