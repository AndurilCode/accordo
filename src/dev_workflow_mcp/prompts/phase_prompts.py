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
        
        return f"""📊 ANALYZE PHASE - REQUIREMENTS UNDERSTANDING ONLY

**Task:** {task_description}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → ANALYZE
- Status → RUNNING
- Analysis phase initiated

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```

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

✅ **Documentation Criteria:**
- [ ] Have read project_config.md and understand test commands
- [ ] Have examined relevant source code files
- [ ] Have reviewed any existing documentation
- [ ] Have identified coding standards and conventions
- [ ] Have noted any existing patterns to follow

✅ **Quality Criteria:**
- [ ] Can articulate what "done" looks like for this task
- [ ] Can identify how to validate the final implementation
- [ ] Can explain the impact on existing functionality
- [ ] Can describe any backwards compatibility considerations

**🚫 STRICTLY FORBIDDEN - NEVER DO THESE:**
- ❌ Writing any code whatsoever
- ❌ Creating implementation plans or solutions
- ❌ Making file changes or edits
- ❌ Running commands or tools
- ❌ Making architectural decisions
- ❌ Designing interfaces or APIs
- ❌ Creating pseudocode or algorithms

**📝 ANALYSIS OUTPUT REQUIREMENTS:**
Your analysis summary MUST include:
1. **Clear Requirements Statement** - What exactly needs to be built/changed
2. **Affected Components** - List of all files/systems that will be modified
3. **Current State Description** - How the relevant parts work now
4. **Dependencies & Constraints** - External factors that affect implementation
5. **Success Criteria** - How we'll know the task is complete
6. **Risk Assessment** - Potential complications or edge cases

**⏱️ TIME EXPECTATION:** 5-15 minutes for simple tasks, 15-30 minutes for complex tasks

**💡 GOOD ANALYSIS EXAMPLE:**
"Task requires adding user authentication to the web API. Current system has no auth (analyzed routes.py). Will need to: add auth middleware, create user models, add login/logout endpoints. Dependencies: requires new auth library. Success: users can register/login/access protected routes. Risks: session management, password security."

**❌ POOR ANALYSIS ANTI-PATTERN:**
"Need to add authentication. Will use JWT tokens and create login page."

**🚨 ESCALATION TRIGGERS:**
Call `escalate_to_user_guidance` if:
- Requirements are unclear or contradictory
- Multiple valid approaches exist and clarification needed
- Task scope seems too large for single workflow
- Critical information is missing from codebase

**🔄 WHEN ANALYSIS COMPLETE:**
MUST call: `blueprint_phase_guidance`
Parameters: task_description="{task_description}", requirements_summary="<your detailed analysis>"

🎯 **Analysis phase started automatically - focus ONLY on understanding requirements!**
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
        
        return f"""📋 BLUEPRINT PHASE - DETAILED IMPLEMENTATION PLANNING

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

**🎯 PHASE OBJECTIVE:** Create a detailed, step-by-step implementation plan that can be executed without further planning decisions.

**📋 MANDATORY PLAN SECTIONS - ALL REQUIRED:**

**1. IMPLEMENTATION STEPS** ⚠️ REQUIRED
   - MUST break task into atomic, ordered steps (max 10 steps)
   - MUST specify exact files to be modified in each step
   - MUST include verification command after each step
   - MUST define clear inputs/outputs for each step
   - MUST specify rollback procedure for each step

**2. FILE-LEVEL CHANGES** ⚠️ REQUIRED
   - MUST list every file that will be created/modified/deleted
   - MUST specify the type of change for each file (create/modify/delete)
   - MUST indicate dependencies between file changes
   - MUST include configuration file updates if needed

**3. TESTING STRATEGY** ⚠️ REQUIRED
   - MUST specify which tests to run after each step
   - MUST include new test requirements (if any)
   - MUST define acceptance criteria for each test phase
   - MUST include performance/quality validation steps

**4. RISK MITIGATION** ⚠️ REQUIRED
   - MUST identify potential failure points
   - MUST specify backup/rollback procedures
   - MUST include dependency conflict resolution
   - MUST define error recovery strategies

**5. QUALITY GATES** ⚠️ REQUIRED
   - MUST define code quality requirements
   - MUST specify linting/formatting requirements
   - MUST include type checking requirements (if applicable)
   - MUST define documentation requirements

**🔍 PLAN QUALITY VALIDATION CHECKLIST:**
Before submitting plan, verify ALL of the following:

✅ **Completeness Criteria:**
- [ ] Every step is actionable without additional decision-making
- [ ] All file changes are explicitly listed
- [ ] All dependencies and prerequisites are identified
- [ ] All testing requirements are clearly defined
- [ ] All quality requirements are specified

✅ **Clarity Criteria:**
- [ ] Each step has clear start/end conditions
- [ ] Each step includes verification commands
- [ ] Order of execution is unambiguous
- [ ] Rollback procedures are clearly defined
- [ ] Error conditions are anticipated and addressed

✅ **Feasibility Criteria:**
- [ ] Plan can be completed in reasonable time
- [ ] All required tools/dependencies are available
- [ ] No circular dependencies exist
- [ ] Each step builds logically on previous steps
- [ ] Plan aligns with project standards and conventions

**🚫 STRICTLY FORBIDDEN - NEVER DO THESE:**
- ❌ Creating vague or ambiguous steps
- ❌ Leaving implementation decisions for later
- ❌ Skipping error handling or rollback procedures
- ❌ Ignoring existing code patterns or conventions
- ❌ Creating steps that require architectural decisions
- ❌ Making plans that skip testing or quality validation
- ❌ Creating interdependent steps without clear ordering

**📝 PLAN FORMAT REQUIREMENTS:**
Your implementation plan MUST follow this structure:

```
## Implementation Plan

### Step 1: [Clear step title]
- **Action**: Exactly what to do
- **Files**: List of files to modify
- **Command**: Verification command to run
- **Success Criteria**: How to know step succeeded
- **Rollback**: How to undo if step fails

### Step 2: [Next step]
[Same format as Step 1]

### Testing Strategy
- Unit tests: [specific test commands]
- Integration tests: [specific test commands]  
- Quality checks: [linting, formatting, type checking]

### Risk Mitigation
- Risk: [potential issue]
  Solution: [how to prevent/handle]
```

**⏱️ TIME EXPECTATION:** 10-30 minutes for simple plans, 30-60 minutes for complex plans

**💡 GOOD PLAN EXAMPLE:**
```
## Implementation Plan

### Step 1: Add User Model
- **Action**: Create user.py with User class and database fields
- **Files**: models/user.py (create), __init__.py (modify)
- **Command**: python -m pytest tests/test_models.py::test_user_model
- **Success Criteria**: User model instantiates and validates correctly
- **Rollback**: Delete models/user.py, revert __init__.py

### Step 2: Add Authentication Middleware
- **Action**: Create auth middleware to validate JWT tokens
- **Files**: middleware/auth.py (create), app.py (modify)
- **Command**: python -m pytest tests/test_auth.py
- **Success Criteria**: Middleware blocks unauthenticated requests
- **Rollback**: Remove middleware import from app.py, delete middleware/auth.py
```

**❌ POOR PLAN ANTI-PATTERN:**
```
## Implementation Plan
1. Add authentication
2. Create login page
3. Test everything
```

**🚨 ESCALATION TRIGGERS:**
Call `escalate_to_user_guidance` if:
- Requirements are insufficient for detailed planning
- Multiple architectural approaches are viable and need user choice
- Plan would require >10 steps (consider breaking into sub-tasks)
- Significant refactoring would be needed beyond scope

**⚠️ PLAN APPROVAL REQUIRED:**
Once you complete the plan, MUST call `update_workflow_state_guidance` with:
- phase="BLUEPRINT" 
- status="NEEDS_PLAN_APPROVAL"
- log_entry="Plan completed and ready for user review"

**✅ WHEN USER APPROVES PLAN:**
Call: `construct_phase_guidance`
Parameters: task_description="{task_description}"

**❌ IF USER REJECTS PLAN:**
Call: `revise_blueprint_guidance`
Parameters: task_description="{task_description}", feedback="<user feedback>"

🎯 **Blueprint phase started automatically - create comprehensive implementation plan!**
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
        
        return f"""🔨 CONSTRUCT PHASE - SYSTEMATIC IMPLEMENTATION

**Task:** {task_description}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → CONSTRUCT
- Status → RUNNING
- Implementation phase initiated

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```

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

**5. PROGRESS LOGGING** ⚠️ REQUIRED
   - MUST log step completion with timestamp
   - MUST record verification command results
   - MUST note any deviations or issues encountered
   - MUST update workflow state with current step status

**🔍 STEP VERIFICATION CHECKLIST:**
Before proceeding to next step, verify ALL of the following:

✅ **Implementation Criteria:**
- [ ] Step implemented exactly as planned
- [ ] All specified files modified correctly
- [ ] No unplanned changes made
- [ ] Existing functionality not broken

✅ **Quality Criteria:**
- [ ] Verification command passed successfully
- [ ] Linting passes without new errors
- [ ] Formatting is consistent
- [ ] No syntax or import errors

✅ **Progress Criteria:**
- [ ] Step completion logged with details
- [ ] Any issues documented and resolved
- [ ] Ready to proceed to next step
- [ ] Rollback procedure understood if needed

**🚫 STRICTLY FORBIDDEN - NEVER DO THESE:**
- ❌ Implementing multiple steps simultaneously
- ❌ Making changes not specified in the approved plan
- ❌ Skipping verification commands or quality checks
- ❌ Proceeding with failing tests or linting errors
- ❌ Making architectural decisions not in the plan
- ❌ Introducing new dependencies without plan approval
- ❌ Ignoring existing code patterns or conventions

**📝 REQUIRED LOGGING FORMAT:**
For each step completion, MUST log:

```
🔨 STEP [N] COMPLETED: [Step Title]
- Files Modified: [list of files]
- Verification Command: [command run]
- Command Output: [actual output]
- Success Criteria: [✅ Met / ❌ Failed]
- Issues Found: [any problems encountered]
- Resolution: [how issues were fixed]
- Next Step: [what comes next]
```

**⏱️ TIME EXPECTATION:** 2-10 minutes per step, depending on complexity

**💡 GOOD IMPLEMENTATION EXAMPLE:**
```
🔨 STEP 1 COMPLETED: Add User Model
- Files Modified: models/user.py (created), models/__init__.py (updated)
- Verification Command: python -m pytest tests/test_models.py::test_user_model
- Command Output: ====== 1 passed in 0.12s ======
- Success Criteria: ✅ Met - User model instantiates correctly
- Issues Found: None
- Resolution: N/A
- Next Step: Step 2 - Add Authentication Middleware
```

**❌ POOR IMPLEMENTATION ANTI-PATTERN:**
```
Added user model and auth middleware. Tests pass.
```

**🚨 ERROR RECOVERY PROCEDURE:**
If ANY step fails:
1. IMMEDIATELY stop implementation
2. Document the exact error and context
3. Attempt step rollback using plan's rollback procedure
4. Call `error_recovery_guidance` with detailed error info
5. DO NOT proceed to next step until error resolved

**🚨 ESCALATION TRIGGERS:**
Call `error_recovery_guidance` if:
- Verification command fails repeatedly
- Linting/formatting introduces errors that can't be quickly fixed
- Step requirements don't match actual codebase state
- Unexpected dependencies or conflicts discovered
- More than 3 attempts needed to complete any single step

**⚠️ CRITICAL RULES:**
- Follow the plan EXACTLY - no creative interpretations
- Verify EVERY step before proceeding
- Log ALL outputs and decisions
- Maintain quality standards throughout
- Stop immediately on any failures

**✅ WHEN ALL STEPS COMPLETE:**
Call: `validate_phase_guidance`
Parameters: task_description="{task_description}"

**🚨 IF TESTS FAIL OR ERRORS OCCUR:**
Call: `error_recovery_guidance`
Parameters: task_description="{task_description}", error_details="<detailed error description with context>"

🎯 **Construction phase started automatically - implement systematically with mandatory verification!**
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
        
        return f"""✅ VALIDATE PHASE - COMPREHENSIVE QUALITY VERIFICATION

**Task:** {task_description}

**✅ STATE UPDATED AUTOMATICALLY:**
- Phase → VALIDATE
- Status → RUNNING
- Validation phase initiated

**📋 CURRENT WORKFLOW STATE:**
```markdown
{updated_state}
```

**🎯 PHASE OBJECTIVE:** Comprehensively verify implementation quality, functionality, and compliance with all requirements.

**✅ MANDATORY VALIDATION SEQUENCE - EXECUTE IN ORDER:**

**1. FUNCTIONAL TESTING** ⚠️ REQUIRED
   - MUST run complete test suite: `python -m pytest`
   - MUST verify all existing tests still pass
   - MUST test all new functionality added
   - MUST capture and log complete test output
   - MUST achieve same or better test coverage

**2. QUALITY GATE VALIDATION** ⚠️ REQUIRED
   - MUST run linting: `ruff check .`
   - MUST verify formatting: `ruff format --check .`
   - MUST run type checking: `mypy src/` (if applicable)
   - MUST ensure no quality regressions
   - MUST verify all quality checks pass

**3. INTEGRATION VERIFICATION** ⚠️ REQUIRED
   - MUST verify integration with existing systems
   - MUST test all modified interfaces and APIs
   - MUST confirm backwards compatibility maintained
   - MUST verify no breaking changes introduced
   - MUST test common usage scenarios

**4. REQUIREMENTS COMPLIANCE** ⚠️ REQUIRED
   - MUST verify all original requirements met
   - MUST check acceptance criteria from analysis phase
   - MUST confirm success criteria achieved
   - MUST validate edge cases handled correctly
   - MUST ensure error conditions properly managed

**5. DOCUMENTATION VALIDATION** ⚠️ REQUIRED
   - MUST verify code is properly documented
   - MUST check that public APIs have docstrings
   - MUST ensure complex logic is commented
   - MUST validate README/docs updated if needed
   - MUST confirm examples work correctly

**🔍 COMPREHENSIVE VALIDATION CHECKLIST:**
Before marking complete, verify ALL of the following:

✅ **Functional Criteria:**
- [ ] All tests pass without failures or errors
- [ ] New functionality works as specified
- [ ] Existing functionality remains unbroken
- [ ] Edge cases and error conditions handled
- [ ] Performance requirements met (if applicable)

✅ **Quality Criteria:**
- [ ] Linting passes with zero violations
- [ ] Code formatting is consistent
- [ ] Type checking passes (if applicable)
- [ ] No code smells or anti-patterns introduced
- [ ] Follows project coding standards

✅ **Integration Criteria:**
- [ ] Integrates properly with existing codebase
- [ ] No circular dependencies created
- [ ] All imports resolve correctly
- [ ] Backwards compatibility maintained
- [ ] No breaking changes to public APIs

✅ **Requirements Criteria:**
- [ ] All original requirements fully implemented
- [ ] Success criteria from analysis phase met
- [ ] Acceptance criteria satisfied
- [ ] Risk mitigation measures effective
- [ ] User expectations met

✅ **Documentation Criteria:**
- [ ] Code is properly documented
- [ ] Public APIs have complete docstrings
- [ ] Complex algorithms explained
- [ ] Usage examples provided (if needed)
- [ ] Project documentation updated

**🚫 VALIDATION FAILURES - NEVER PROCEED IF:**
- ❌ Any tests fail or error
- ❌ Linting or formatting violations exist
- ❌ Type checking failures (if applicable)
- ❌ Integration issues detected
- ❌ Requirements not fully met
- ❌ Backwards compatibility broken
- ❌ Documentation incomplete or missing

**📝 REQUIRED VALIDATION REPORT:**
MUST document results in this format:

```
✅ VALIDATION REPORT: [Task Title]

🧪 FUNCTIONAL TESTING:
- Test Command: [command run]
- Test Results: [✅ PASS / ❌ FAIL]
- Coverage: [percentage or N/A]
- Issues Found: [list any failures]

🔍 QUALITY VALIDATION:
- Linting: [✅ PASS / ❌ FAIL - details]
- Formatting: [✅ PASS / ❌ FAIL - details]
- Type Checking: [✅ PASS / ❌ FAIL / N/A - details]

🔗 INTEGRATION TESTING:
- Backwards Compatibility: [✅ MAINTAINED / ❌ BROKEN]
- API Compatibility: [✅ MAINTAINED / ❌ BROKEN]
- Dependencies: [✅ RESOLVED / ❌ CONFLICTS]

📋 REQUIREMENTS VERIFICATION:
- Original Requirements: [✅ MET / ❌ INCOMPLETE]
- Success Criteria: [✅ ACHIEVED / ❌ NOT MET]
- Acceptance Criteria: [✅ SATISFIED / ❌ FAILED]

📖 DOCUMENTATION STATUS:
- Code Documentation: [✅ COMPLETE / ❌ MISSING]
- API Documentation: [✅ COMPLETE / ❌ MISSING]
- Usage Examples: [✅ PROVIDED / ❌ MISSING / N/A]

🎯 OVERALL VALIDATION: [✅ PASS / ❌ FAIL]
```

**⏱️ TIME EXPECTATION:** 5-20 minutes depending on project complexity

**💡 GOOD VALIDATION EXAMPLE:**
```
✅ VALIDATION REPORT: Enhanced Authentication System

🧪 FUNCTIONAL TESTING:
- Test Command: python -m pytest tests/
- Test Results: ✅ PASS (47 passed, 0 failed)
- Coverage: 98% (maintained)
- Issues Found: None

🔍 QUALITY VALIDATION:
- Linting: ✅ PASS (0 violations)
- Formatting: ✅ PASS (consistent style)
- Type Checking: ✅ PASS (no type errors)

🔗 INTEGRATION TESTING:
- Backwards Compatibility: ✅ MAINTAINED
- API Compatibility: ✅ MAINTAINED
- Dependencies: ✅ RESOLVED

📋 REQUIREMENTS VERIFICATION:
- Original Requirements: ✅ MET (user auth implemented)
- Success Criteria: ✅ ACHIEVED (users can login/logout)
- Acceptance Criteria: ✅ SATISFIED (secure password handling)

📖 DOCUMENTATION STATUS:
- Code Documentation: ✅ COMPLETE
- API Documentation: ✅ COMPLETE
- Usage Examples: ✅ PROVIDED

🎯 OVERALL VALIDATION: ✅ PASS
```

**❌ POOR VALIDATION ANTI-PATTERN:**
```
Tests pass. Everything looks good.
```

**🚨 VALIDATION FAILURE PROCEDURE:**
If ANY validation step fails:
1. IMMEDIATELY document the specific failure
2. Analyze root cause and impact
3. Determine if issue can be quickly fixed
4. Call `fix_validation_issues_guidance` with detailed failure report
5. DO NOT proceed to completion until ALL issues resolved

**🚨 ESCALATION TRIGGERS:**
Call `fix_validation_issues_guidance` if:
- Any tests fail or produce errors
- Quality checks fail and can't be quickly resolved
- Integration issues discovered
- Requirements not fully met
- Documentation significantly incomplete

**✅ IF ALL VALIDATIONS PASS:**
Call: `complete_workflow_guidance`
Parameters: task_description="{task_description}"

**❌ IF VALIDATION FAILS:**
Call: `fix_validation_issues_guidance`
Parameters: task_description="{task_description}", issues="<comprehensive failure report>"

🎯 **Validation phase started automatically - verify comprehensive implementation quality!**
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
