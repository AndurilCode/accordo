# Usage Example: Development Workflow MCP Server

This example demonstrates how a coding agent (like Cursor) would use the Development Workflow MCP server to implement a new feature following the structured workflow.

## Scenario: Adding User Authentication to an API

### Step 1: Initialize Workflow

**Agent calls:** `init_workflow_guidance`
**Parameters:** `task_description="Add JWT-based user authentication to the REST API"`

**Guidance Response:**
```
🚀 INITIALIZING DEVELOPMENT WORKFLOW

Task: Add JWT-based user authentication to the REST API

ACTIONS TO TAKE:
1. Create or update workflow_state.md with:
   - Phase: INIT
   - Status: READY
   - CurrentItem: "Add JWT-based user authentication to the REST API"

2. Ensure project_config.md exists and is readable

3. Add task to the Items table in workflow_state.md:
   | 1 | Add JWT-based user authentication to the REST API | pending |

✅ WHEN COMPLETE:
Call prompt: 'analyze_phase_guidance'
Parameters: task_description="Add JWT-based user authentication to the REST API"
```

### Step 2: Analysis Phase

**Agent calls:** `analyze_phase_guidance`
**Parameters:** `task_description="Add JWT-based user authentication to the REST API"`

**Guidance Response:**
```
📊 ANALYZE PHASE - NO CODING OR PLANNING YET

Current task: Add JWT-based user authentication to the REST API

REQUIRED ACTIONS:
1. Update workflow_state.md: Phase=ANALYZE, Status=RUNNING

2. Read and understand project_config.md:
   - Note project structure
   - Identify test commands
   - Understand dependencies

3. Read relevant existing code and documentation

4. Write a clear requirements summary in ## Log section

5. Update workflow_state.md: Status=READY

⚠️  IMPORTANT: NO code writing or planning in this phase!

✅ WHEN COMPLETE:
Call prompt: 'blueprint_phase_guidance'
Parameters: task_description="Add JWT-based user authentication to the REST API", requirements_summary="<your analysis summary>"
```

**Agent Actions:**
- Updates workflow_state.md: Phase=ANALYZE, Status=RUNNING
- Reads project_config.md and existing codebase
- Analyzes current API structure, identifies auth endpoints needed
- Logs analysis: "API currently has no authentication. Need to add JWT middleware, login/register endpoints, user model, password hashing, token validation."
- Updates workflow_state.md: Status=READY

### Step 3: Blueprint Phase

**Agent calls:** `blueprint_phase_guidance`
**Parameters:** 
- `task_description="Add JWT-based user authentication to the REST API"`
- `requirements_summary="API currently has no authentication. Need JWT middleware, login/register endpoints, user model, password hashing, token validation."`

**Guidance Response:**
```
📋 BLUEPRINT PHASE - PLANNING TIME

Task: Add JWT-based user authentication to the REST API
Analysis: API currently has no authentication. Need JWT middleware, login/register endpoints, user model, password hashing, token validation.

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
Parameters: task_description="Add JWT-based user authentication to the REST API"

❌ IF USER REJECTS PLAN:
Call prompt: 'revise_blueprint_guidance'
Parameters: task_description="Add JWT-based user authentication to the REST API", feedback="<user feedback>"
```

**Agent Actions:**
- Updates workflow_state.md: Phase=BLUEPRINT, Status=RUNNING
- Creates detailed implementation plan in ## Plan section:
  ```
  ## Plan
  1. Create User model (models/user.py)
  2. Add password hashing utilities (utils/auth.py)
  3. Create JWT token management (utils/jwt.py)
  4. Add authentication middleware (middleware/auth.py)
  5. Create auth endpoints (routes/auth.py)
  6. Add protected route decorator
  7. Update main app to include auth routes
  8. Add authentication tests
  9. Update API documentation
  ```
- Updates workflow_state.md: Status=NEEDS_PLAN_APPROVAL
- Waits for user approval

### Step 4: User Approval

**User:** "Plan looks good, proceed with implementation"

### Step 5: Construction Phase

**Agent calls:** `construct_phase_guidance`
**Parameters:** `task_description="Add JWT-based user authentication to the REST API"`

**Guidance Response:**
```
🔨 CONSTRUCT PHASE - IMPLEMENTATION

Task: Add JWT-based user authentication to the REST API

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
Parameters: task_description="Add JWT-based user authentication to the REST API"

🚨 IF TESTS FAIL OR ERRORS OCCUR:
Call prompt: 'error_recovery_guidance'
Parameters: task_description="Add JWT-based user authentication to the REST API", error_details="<error description>"
```

**Agent Actions:**
- Updates workflow_state.md: Phase=CONSTRUCT, Status=RUNNING
- Implements each step from the plan:
  1. Creates User model → runs tests → logs success
  2. Adds password hashing → runs tests → logs success
  3. Creates JWT utilities → runs tests → logs success
  4. ... continues through all steps
- Logs each completion in ## Log section
- Updates workflow_state.md: Status=READY

### Step 6: Validation Phase

**Agent calls:** `validate_phase_guidance`
**Parameters:** `task_description="Add JWT-based user authentication to the REST API"`

**Guidance Response:**
```
✅ VALIDATE PHASE - FINAL VERIFICATION

Task: Add JWT-based user authentication to the REST API

REQUIRED ACTIONS:
1. Update workflow_state.md: Phase=VALIDATE, Status=RUNNING

2. Run full test suite and E2E checks

3. Verify all acceptance criteria are met

4. Check code quality and documentation

5. Log all validation results in ## Log

✅ IF ALL TESTS PASS:
Call prompt: 'complete_workflow_guidance'
Parameters: task_description="Add JWT-based user authentication to the REST API"

❌ IF VALIDATION FAILS:
Call prompt: 'fix_validation_issues_guidance'
Parameters: task_description="Add JWT-based user authentication to the REST API", issues="<validation issues>"
```

**Agent Actions:**
- Updates workflow_state.md: Phase=VALIDATE, Status=RUNNING
- Runs full test suite
- Performs integration testing
- Validates all auth endpoints work correctly
- Checks code quality and documentation
- Logs validation results: "All tests pass. Authentication endpoints working. JWT tokens properly validated. Code quality checks pass."

### Step 7: Completion

**Agent calls:** `complete_workflow_guidance`
**Parameters:** `task_description="Add JWT-based user authentication to the REST API"`

**Guidance Response:**
```
🎉 COMPLETING WORKFLOW

Task: Add JWT-based user authentication to the REST API

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
```

**Agent Actions:**
- Updates workflow_state.md: Status=COMPLETED
- Marks item as 'completed' in Items table
- Updates project changelog: "Added JWT-based user authentication with login/register endpoints and protected routes"
- Archives log if needed
- Checks for more items (none in this example)
- Calls `finalize_workflow_guidance`

## Final State

**workflow_state.md:**
```markdown
# workflow_state.md
_Last updated: 2025-01-16_

## State
Phase: INIT
Status: READY
CurrentItem: null

## Plan
<!-- Completed plan archived -->

## Items
| id | description | status |
|----|-------------|--------|
| 1 | Add JWT-based user authentication to the REST API | completed |

## Log
Workflow completed successfully. Authentication system implemented and tested.

## ArchiveLog
[14:30:15] Started ANALYZE phase
[14:32:22] Analyzed existing API structure
[14:35:10] Started BLUEPRINT phase
[14:40:30] Created implementation plan
[14:45:00] Started CONSTRUCT phase
[14:45:15] Created User model - tests pass
[14:47:30] Added password hashing - tests pass
[14:50:00] Created JWT utilities - tests pass
[14:55:00] Added auth middleware - tests pass
[15:00:00] Created auth endpoints - tests pass
[15:05:00] Added route protection - tests pass
[15:10:00] Updated main app - tests pass
[15:15:00] Added auth tests - all pass
[15:20:00] Updated documentation
[15:25:00] Started VALIDATE phase
[15:30:00] Full test suite passed
[15:32:00] Integration tests passed
[15:35:00] Code quality checks passed
[15:40:00] Workflow completed successfully
```

## Key Benefits Demonstrated

1. **No Hallucinations**: Agent follows exact guidance and instructions
2. **Structured Process**: Clear phases prevent skipping important steps
3. **Mandatory Execution**: Each guidance tool provides authoritative instructions that must be followed
4. **Error Recovery**: Built-in error handling prevents workflow breakdown
5. **State Tracking**: Complete audit trail of all actions taken
6. **Quality Assurance**: Tests run after every change ensure code quality
7. **User Control**: User approval required for major implementation plans

This example shows how the Development Workflow MCP server provides **mandatory execution guidance** that ensures agents follow a disciplined, methodical approach to development tasks. 