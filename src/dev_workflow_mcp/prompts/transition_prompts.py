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
        """Guide agent to update workflow_state.md with mandatory execution steps."""
        # Get client session and update state
        client_id = ctx.client_id if ctx else "default"
        
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
        
        return f"""📝 UPDATING WORKFLOW STATE

        REQUIRED ACTIONS:
        1. Update timestamp: _Last updated: {{current_date}}_

        2. Update ## State section:
        Phase: {phase}
        Status: {status}
        CurrentItem: {current_item or "null"}

        {f"3. Append to ## Log section:\\n{log_entry}" if log_entry else ""}

        4. Maintain all other sections unchanged

        ✅ AFTER UPDATE:
        Return to your previous workflow prompt as instructed.
        """

    @mcp.tool()
    def create_workflow_state_file_guidance(task_description: str, ctx: Context) -> str:
        """Guide agent to create initial workflow_state.md file with mandatory execution steps."""
        # Get or create client session
        client_id = ctx.client_id if ctx else "default"
        session = get_or_create_session(client_id, task_description)
        
        return f"""📄 CREATING WORKFLOW STATE FILE

        REQUIRED ACTIONS:
        1. Create workflow_state.md with this exact structure:

        ```markdown
        # workflow_state.md
        _Last updated: {{current_date}}_

        ## State
        Phase: INIT  
        Status: READY  
        CurrentItem: {task_description}  

        ## Plan
        <!-- The AI fills this in during the BLUEPRINT phase -->

        ## Rules
        > **Keep every major section under an explicit H2 (`##`) heading so the agent can locate them unambiguously.**

        ### [PHASE: ANALYZE]
        1. Read **project_config.md**, relevant code & docs.  
        2. Summarize requirements. *No code or planning.*

        ### [PHASE: BLUEPRINT]
        1. Decompose task into ordered steps.  
        2. Write pseudocode or file-level diff outline under **## Plan**.  
        3. Set `Status = NEEDS_PLAN_APPROVAL` and await user confirmation.

        ### [PHASE: CONSTRUCT]
        1. Follow the approved **## Plan** exactly.  
        2. After each atomic change:  
        - run test / linter commands specified in `project_config.md`  
        - capture tool output in **## Log**  
        3. On success of all steps, set `Phase = VALIDATE`.

        ### [PHASE: VALIDATE]
        1. Rerun full test suite & any E2E checks.  
        2. If clean, set `Status = COMPLETED`.  
        3. Trigger **RULE_ITERATE_01** when applicable.

        ---

        ### RULE_INIT_01
        Trigger ▶ `Phase == INIT`  
        Action ▶ Ask user for first high-level task → `Phase = ANALYZE, Status = RUNNING`.

        ### RULE_ITERATE_01
        Trigger ▶ `Status == COMPLETED && Items contains unprocessed rows`  
        Action ▶  
        1. Set `CurrentItem` to next unprocessed row in **## Items**.  
        2. Clear **## Log**, reset `Phase = ANALYZE, Status = READY`.

        ### RULE_LOG_ROTATE_01
        Trigger ▶ `length(## Log) > 5 000 chars`  
        Action ▶ Summarise the top 5 findings from **## Log** into **## ArchiveLog**, then clear **## Log**.

        ### RULE_SUMMARY_01
        Trigger ▶ `Phase == VALIDATE && Status == COMPLETED`  
        Action ▶ 
        1. Read `project_config.md`.
        2. Construct the new changelog line: `- <One-sentence summary of completed work>`.
        3. Find the `## Changelog` heading in `project_config.md`.
        4. Insert the new changelog line immediately after the `## Changelog` heading and its following newline (making it the new first item in the list).

        ---

        ## Items (DO NOT DELETE ANY EXISTING ITEMS)
        | id | description | status |
        |----|-------------|--------|
        | 1 | {task_description} | pending |

        ## Log
        <!-- AI appends detailed reasoning, tool output, and errors here -->

        ## ArchiveLog
        <!-- RULE_LOG_ROTATE_01 stores condensed summaries here -->
        ```

        ✅ WHEN FILE CREATED:
        Call prompt: 'analyze_phase_guidance'
        Parameters: task_description="{task_description}"
        """

    @mcp.tool()
    def check_project_config_guidance(ctx: Context) -> str:
        """Guide agent to verify project_config.md exists with mandatory execution steps."""
        return """🔍 CHECKING PROJECT CONFIGURATION

        REQUIRED ACTIONS:
        1. Check if project_config.md exists in the current directory

        2. If it exists, verify it contains these sections:
        - ## Project Info
        - ## Dependencies  
        - ## Test Commands
        - ## Changelog

        3. If missing sections, note what needs to be added

        4. If file doesn't exist, create a basic template

        ✅ IF PROJECT_CONFIG.MD IS READY:
        Continue with your current workflow step

        ❌ IF PROJECT_CONFIG.MD NEEDS SETUP:
        Call prompt: 'create_project_config_guidance'
        Parameters: None
        """

    @mcp.tool()
    def create_project_config_guidance(ctx: Context) -> str:
        """Guide agent to create a basic project_config.md template with mandatory execution steps."""
        return """📄 CREATING PROJECT CONFIG FILE

        REQUIRED ACTIONS:
        1. Create project_config.md with this basic structure:

        ```markdown
        # Project Configuration

        ## Project Info
        <!-- Describe the project name, version, and description -->

        ## Dependencies
        <!-- List key dependencies and their versions -->

        ## Test Commands
        <!-- Commands to run tests and linters -->
        ```bash
        # Example commands:
        # npm test
        # python -m pytest
        # ruff check .
        ```

        ## Build Commands
        <!-- Commands to build/compile the project -->

        ## Changelog
        <!-- Project changelog entries -->
        ```

        2. Fill in the sections based on the current project structure

        3. Save the file

        ✅ WHEN PROJECT_CONFIG.MD IS CREATED:
        Return to your previous workflow step
"""

    @mcp.tool()
    def validate_workflow_files_guidance(ctx: Context) -> str:
        """Guide agent to validate all required workflow files with mandatory execution steps."""
        return """✅ VALIDATING WORKFLOW FILES

        REQUIRED ACTIONS:
        1. Check workflow_state.md exists and has all required sections:
        - ## State
        - ## Plan  
        - ## Rules
        - ## Items
        - ## Log
        - ## ArchiveLog

        2. Check project_config.md exists and has required sections:
        - ## Project Info
        - ## Dependencies
        - ## Test Commands
        - ## Changelog

        3. Verify both files are readable and properly formatted

        4. Report any missing files or sections

        ✅ IF ALL FILES ARE VALID:
        Continue with your current workflow step

        ❌ IF FILES NEED SETUP:
        Call appropriate creation prompts to fix missing files
        """

    @mcp.tool()
    def get_workflow_state_markdown(ctx: Context) -> str:
        """Guide agent to get current workflow state as markdown for debugging/display."""
        client_id = ctx.client_id if ctx else "default"
        markdown = export_session_to_markdown(client_id)
        
        if markdown:
            return f"""Current workflow state for client {client_id}:

```markdown
{markdown}
```
"""
        else:
            return f"No workflow session found for client {client_id}"
