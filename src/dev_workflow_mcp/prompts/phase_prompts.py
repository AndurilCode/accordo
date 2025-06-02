"""Pure schema-driven workflow prompts.

This module provides workflow guidance based purely on YAML workflow schemas.
No hardcoded logic - all behavior determined by workflow definitions.
"""

import json

from fastmcp import FastMCP
from pydantic import Field

from ..models.workflow_state import WorkflowPhase, WorkflowStatus
from ..models.yaml_workflow import WorkflowDefinition, WorkflowNode
from ..utils.schema_analyzer import (
    analyze_node_from_schema,
    extract_choice_from_context,
    extract_workflow_from_context,
    format_node_status,
    get_available_transitions,
    get_workflow_summary,
    validate_transition,
)
from ..utils.session_manager import (
    add_item_to_session,
    add_log_to_session,
    export_session_to_markdown,
    get_dynamic_session_workflow_def,
    get_or_create_dynamic_session,
    get_or_create_session,
    get_session_type,
    update_dynamic_session_node,
    update_dynamic_session_status,
    update_session_state,
)
from ..utils.state_manager import get_file_operation_instructions
from ..utils.workflow_engine import WorkflowEngine
from ..utils.yaml_loader import WorkflowLoader


def register_phase_prompts(app: FastMCP):
    """Register purely schema-driven workflow prompts."""

    @app.tool()
    def workflow_guidance(
        task_description: str = Field(
            description="Task description in format 'Action: Brief description'"
        ),
        action: str = Field(
            default="",
            description="Workflow action: 'start', 'plan', 'build', 'revise', 'next'",
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
        """Pure schema-driven workflow guidance.

        Provides guidance based entirely on workflow schema structure.
        No hardcoded behavior - everything driven by YAML definitions.
        """
        try:
            client_id = "default"  # In real implementation, extract from Context

            # Initialize workflow engine and loader
            engine = WorkflowEngine()
            loader = WorkflowLoader()

            # Check if we have a dynamic session already
            session_type = get_session_type(client_id)

            if session_type == "dynamic":
                # Continue with existing dynamic workflow
                session = get_or_create_dynamic_session(client_id, task_description)
                workflow_def = get_dynamic_session_workflow_def(client_id)

                if not workflow_def:
                    # Fallback if workflow missing
                    return _handle_legacy_fallback(
                        client_id, task_description, action, context, options
                    )

                return _handle_dynamic_workflow(
                    session, workflow_def, action, context, engine, loader
                )

            elif action.lower() == "start":
                # Try to discover and start a dynamic workflow
                try:
                    available_workflows = loader.discover_workflows()

                    if available_workflows:
                        # Present available workflows to agent for selection
                        workflow_list = "\n".join(
                            [
                                f"• **{name}**: {wf.description}"
                                for name, wf in available_workflows.items()
                            ]
                        )

                        return f"""🔍 **Available Workflows Found**

{workflow_list}

**To start a workflow:**
Call workflow_guidance with:
- action: "start"
- context: "workflow: <workflow_name>"

**Example:** context="workflow: Default Coding Workflow"

**Legacy Fallback:** If no workflow specified, will use hardcoded legacy workflow."""

                    else:
                        # No workflows found, use legacy fallback
                        return _handle_legacy_fallback(
                            client_id, task_description, action, context, options
                        )

                except Exception:
                    # Error loading workflows, use legacy fallback
                    return _handle_legacy_fallback(
                        client_id, task_description, action, context, options
                    )

            elif action.lower() == "start" and context:
                # User specified workflow
                workflow_name = extract_workflow_from_context(context)

                if workflow_name:
                    try:
                        # Try to start the specified workflow
                        available_workflows = loader.discover_workflows()

                        # Find matching workflow (case-insensitive)
                        selected_workflow = None
                        for name, wf in available_workflows.items():
                            if name.lower() == workflow_name.lower():
                                selected_workflow = wf
                                break

                        if selected_workflow:
                            # Initialize dynamic session with selected workflow
                            session = get_or_create_dynamic_session(
                                client_id, task_description
                            )
                            engine.initialize_workflow(session, selected_workflow)

                            # Get current node info
                            current_node = selected_workflow.workflow.tree[
                                session.current_node
                            ]
                            status = format_node_status(current_node, selected_workflow)

                            return f"""🚀 **Workflow Started:** {selected_workflow.name}

**Task:** {task_description}

{status}"""

                        else:
                            return f"""❌ **Workflow Not Found:** {workflow_name}

Available workflows:
{chr(10).join([f"• {name}" for name in available_workflows])}

Please use exact workflow name or use legacy fallback."""

                    except Exception as e:
                        return f"❌ **Error starting workflow:** {str(e)}\n\nFalling back to legacy workflow."

                else:
                    return _handle_legacy_fallback(
                        client_id, task_description, action, context, options
                    )

            else:
                # For all other actions, use legacy fallback
                return _handle_legacy_fallback(
                    client_id, task_description, action, context, options
                )

        except Exception as e:
            # Any error falls back to legacy
            return f"❌ **Error in schema-driven workflow:** {str(e)}\n\nFalling back to legacy workflow."

    def _handle_dynamic_workflow(
        session,
        workflow_def,
        action: str,
        context: str,
        engine: WorkflowEngine,
        loader: WorkflowLoader,
    ) -> str:
        """Handle dynamic workflow execution based purely on schema."""
        try:
            current_node = workflow_def.workflow.tree.get(session.current_node)

            if not current_node:
                return f"❌ **Invalid workflow state:** Node '{session.current_node}' not found in workflow."

            # Handle choice selection
            if context and "choose:" in context.lower():
                choice = extract_choice_from_context(context)

                if choice and validate_transition(current_node, choice, workflow_def):
                    # Valid transition - update session
                    if choice in (current_node.next_allowed_nodes or []):
                        # Node transition
                        update_dynamic_session_node(session.client_id, choice)
                        session.current_node = choice
                        new_node = workflow_def.workflow.tree[choice]
                        
                        # Log the transition
                        add_log_to_session(session.client_id, f"🔄 TRANSITIONED TO: {choice.upper()} PHASE")
                        
                        status = format_enhanced_node_status(new_node, workflow_def, session)

                        return f"""✅ **Transitioned to:** {choice.upper()}

{status}"""

                    elif choice in (current_node.next_allowed_workflows or []):
                        # Workflow transition
                        try:
                            available_workflows = loader.discover_workflows()
                            target_workflow = available_workflows.get(choice)

                            if target_workflow:
                                # Switch to new workflow
                                new_session = get_or_create_dynamic_session(
                                    session.client_id, f"Switched to: {choice}"
                                )
                                engine.initialize_workflow(new_session, target_workflow)

                                new_current_node = target_workflow.workflow.tree[
                                    new_session.current_node
                                ]
                                status = format_enhanced_node_status(
                                    new_current_node, target_workflow, new_session
                                )

                                return f"""🔄 **Switched to Workflow:** {choice}

{status}"""

                            else:
                                return f"❌ **Workflow not found:** {choice}"

                        except Exception as e:
                            return f"❌ **Error switching workflow:** {str(e)}"

                else:
                    # Invalid choice
                    transitions = get_available_transitions(current_node, workflow_def)
                    valid_options = [t["name"] for t in transitions]

                    return f"""❌ **Invalid choice:** {choice}

**Valid options:** {", ".join(valid_options)}

**Usage:** Use context="choose: <option_name>" with exact option name."""

            # Default: show current status with enhanced guidance
            status = format_enhanced_node_status(current_node, workflow_def, session)
            return status

        except Exception as e:
            return f"❌ **Dynamic workflow error:** {str(e)}"

    def _handle_legacy_fallback(
        client_id: str, task_description: str, action: str, context: str, options: str
    ) -> str:
        """Handle legacy workflow as fallback when no YAML workflows available."""
        # Legacy action handlers preserved for compatibility
        if action.lower() == "start":
            return _handle_start_action(client_id, task_description, options)
        elif action.lower() == "plan":
            return _handle_plan_action(client_id, task_description, context)
        elif action.lower() == "build":
            return _handle_build_action(client_id, task_description, context)
        elif action.lower() == "revise":
            return _handle_revise_action(client_id, task_description, context)
        elif action.lower() == "next":
            return _handle_next_action(client_id, task_description, context)
        else:
            return _handle_start_action(client_id, task_description, options)

    # ==================== LEGACY ACTION HANDLERS (PRESERVED) ====================

    def _handle_start_action(
        client_id: str, task_description: str, options: str
    ) -> str:
        """Legacy start action handler."""
        try:
            # Create session and initialize state
            get_or_create_session(client_id)

            # Parse options for project config path
            project_config_path = ".workflow-commander/project_config.md"
            if options:
                try:
                    opts = json.loads(options)
                    project_config_path = opts.get(
                        "project_config_path", project_config_path
                    )
                except (json.JSONDecodeError, TypeError):
                    pass

            # Add task to session items
            add_item_to_session(client_id, task_description)

            # Update session state to ANALYZE phase
            update_session_state(
                client_id, WorkflowPhase.ANALYZE, WorkflowStatus.RUNNING
            )

            # Add log entry
            add_log_to_session(
                client_id, f"🚀 WORKFLOW INITIALIZED: {task_description}"
            )
            add_log_to_session(
                client_id, f"📊 ANALYZE PHASE STARTED: {task_description}"
            )

            # Get file operations guidance
            file_ops = get_file_operation_instructions(project_config_path)

            return f"""🚀 **ANALYZE PHASE - REQUIREMENTS GATHERING**

**Task:** {task_description}

{file_ops}

**📋 CURRENT WORKFLOW STATE:**
```markdown
{export_session_to_markdown(client_id)}
```

**🎯 PHASE OBJECTIVE:** Gather comprehensive information about requirements, constraints, and codebase to understand what needs to be done.

**🔨 MANDATORY EXECUTION PROCESS - FOLLOW EXACTLY:**

**1. READ PROJECT CONFIGURATION** ⚠️ REQUIRED
   - MUST read `{project_config_path}` to understand project context
   - MUST understand coding standards, testing requirements, and project structure
   - MUST note any specific constraints or requirements

**2. CODEBASE ANALYSIS** ⚠️ REQUIRED
   - MUST perform semantic search to understand relevant code patterns
   - MUST identify existing implementations that relate to the task
   - MUST understand current architecture and design patterns
   - MUST identify potential integration points and dependencies

**3. REQUIREMENTS ANALYSIS** ⚠️ REQUIRED
   - MUST break down the task into clear, actionable requirements
   - MUST identify any ambiguities that need clarification
   - MUST determine scope boundaries and what's in/out of scope
   - MUST identify potential risks and complexity factors

**4. CONTEXT GATHERING** ⚠️ REQUIRED
   - MUST gather any additional context needed (documentation, examples, etc.)
   - MUST understand user expectations and success criteria
   - MUST identify any external dependencies or constraints

**🚨 ERROR RECOVERY:**
If ANY step fails, call: `workflow_guidance`
Parameters: action="next", task_description="{task_description}"

**✅ WHEN ANALYSIS IS COMPLETE:**
Call: `workflow_guidance`
Parameters: action="plan", task_description="{task_description}", context="<summary of analysis findings>"

🎯 **Analysis phase started - gather comprehensive information!**"""

        except Exception as e:
            return f"❌ **Error in start action:** {str(e)}"

    def _handle_plan_action(client_id: str, task_description: str, context: str) -> str:
        """Legacy plan action handler."""
        try:
            # Update session state to BLUEPRINT phase
            update_session_state(
                client_id, WorkflowPhase.BLUEPRINT, WorkflowStatus.RUNNING
            )
            add_log_to_session(
                client_id, f"📋 BLUEPRINT PHASE STARTED: {task_description}"
            )
            add_log_to_session(client_id, f"Analysis Summary: {context}")

            return f"""📋 **BLUEPRINT PHASE - IMPLEMENTATION PLANNING**

**Task:** {task_description}

**Analysis Summary:** {context}

**📋 CURRENT WORKFLOW STATE:**
```markdown
{export_session_to_markdown(client_id)}
```

**🎯 PHASE OBJECTIVE:** Create a detailed, step-by-step implementation plan based on the analysis.

**🔨 MANDATORY EXECUTION PROCESS - FOLLOW EXACTLY:**

**1. DECOMPOSE INTO ATOMIC STEPS** ⚠️ REQUIRED
   - MUST break down the task into precise, sequential steps
   - MUST ensure each step is small and verifiable
   - MUST identify dependencies between steps
   - MUST specify success criteria for each step

**2. DESIGN APPROACH** ⚠️ REQUIRED
   - MUST specify the overall technical approach
   - MUST identify files that need to be created/modified
   - MUST plan the implementation strategy
   - MUST consider error handling and edge cases

**3. TESTING STRATEGY** ⚠️ REQUIRED
   - MUST plan how each step will be tested/verified
   - MUST identify integration points that need validation
   - MUST specify acceptance criteria

**4. RISK ASSESSMENT** ⚠️ REQUIRED
   - MUST identify potential blocking issues
   - MUST plan mitigation strategies
   - MUST identify fallback approaches

**🚨 ERROR RECOVERY:**
If ANY step fails, call: `workflow_guidance`
Parameters: action="next", task_description="{task_description}"

**✅ WHEN PLANNING IS COMPLETE:**
Call: `workflow_guidance`
Parameters: action="build", task_description="{task_description}", context="<implementation plan>"

🎯 **Blueprint phase started - create detailed implementation plan!**"""

        except Exception as e:
            return f"❌ **Error in plan action:** {str(e)}"

    def _handle_build_action(
        client_id: str, task_description: str, context: str
    ) -> str:
        """Legacy build action handler."""
        try:
            # Update session state to CONSTRUCT phase
            update_session_state(
                client_id, WorkflowPhase.CONSTRUCT, WorkflowStatus.RUNNING
            )
            add_log_to_session(
                client_id, f"🔨 CONSTRUCT PHASE STARTED: {task_description}"
            )

            return f"""🔨 **CONSTRUCT PHASE - IMPLEMENTATION**

**Task:** {task_description}

**Implementation Plan:** {context}

**📋 CURRENT WORKFLOW STATE:**
```markdown
{export_session_to_markdown(client_id)}
```

**🎯 PHASE OBJECTIVE:** Execute the implementation plan step by step with validation.

**🔨 MANDATORY EXECUTION PROCESS - FOLLOW EXACTLY:**

**1. FOLLOW PLAN SEQUENTIALLY** ⚠️ REQUIRED
   - MUST implement each step in the exact order planned
   - MUST complete each step fully before moving to next
   - MUST verify success criteria for each step
   - MUST NOT skip or combine steps

**2. VALIDATE EACH STEP** ⚠️ REQUIRED
   - MUST test each change immediately after implementation
   - MUST run linting/formatting checks
   - MUST verify functionality works as expected
   - MUST capture validation results

**3. ERROR HANDLING** ⚠️ REQUIRED
   - MUST fix any errors before proceeding
   - MUST ensure code quality standards are met
   - MUST not introduce new bugs or regressions

**4. PROGRESS TRACKING** ⚠️ REQUIRED
   - MUST log progress after each major step
   - MUST update implementation status
   - MUST note any deviations from plan

**🚨 ERROR RECOVERY:**
If ANY step fails, call: `workflow_guidance`
Parameters: action="revise", task_description="{task_description}", context="<error details>"

**✅ WHEN CONSTRUCTION IS COMPLETE:**
Call: `workflow_guidance`
Parameters: action="next", task_description="{task_description}"

🎯 **Construction phase started - implement systematically!**"""

        except Exception as e:
            return f"❌ **Error in build action:** {str(e)}"

    def _handle_revise_action(
        client_id: str, task_description: str, context: str
    ) -> str:
        """Legacy revise action handler."""
        try:
            add_log_to_session(client_id, f"🔄 REVISION REQUESTED: {context}")

            return f"""🔄 **REVISION MODE - ERROR RECOVERY**

**Task:** {task_description}

**Issue:** {context}

**📋 CURRENT WORKFLOW STATE:**
```markdown
{export_session_to_markdown(client_id)}
```

**🎯 PHASE OBJECTIVE:** Address the issue and get back on track.

**🔨 MANDATORY EXECUTION PROCESS - FOLLOW EXACTLY:**

**1. DIAGNOSE THE PROBLEM** ⚠️ REQUIRED
   - MUST understand exactly what went wrong
   - MUST identify root cause of the issue
   - MUST determine impact on overall plan

**2. DEVELOP SOLUTION** ⚠️ REQUIRED
   - MUST create specific steps to fix the issue
   - MUST ensure solution addresses root cause
   - MUST verify solution won't create new problems

**3. IMPLEMENT FIX** ⚠️ REQUIRED
   - MUST apply the solution systematically
   - MUST test the fix thoroughly
   - MUST verify issue is fully resolved

**4. RESUME WORKFLOW** ⚠️ REQUIRED
   - MUST determine where to continue in workflow
   - MUST update plans if necessary
   - MUST proceed with remaining steps

**🚨 ERROR RECOVERY:**
If revision fails, call: `workflow_guidance`
Parameters: action="revise", task_description="{task_description}", context="<new error details>"

**✅ WHEN REVISION IS COMPLETE:**
Call: `workflow_guidance`
Parameters: action="next", task_description="{task_description}"

🎯 **Revision mode - fix the issue and resume!**"""

        except Exception as e:
            return f"❌ **Error in revise action:** {str(e)}"

    def _handle_next_action(client_id: str, task_description: str, context: str) -> str:
        """Legacy next action handler."""
        try:
            session = get_or_create_session(client_id)

            # Determine next phase based on current phase
            if session.state.phase == WorkflowPhase.ANALYZE:
                # Move from ANALYZE to BLUEPRINT
                return _handle_plan_action(client_id, task_description, context)

            elif session.state.phase == WorkflowPhase.BLUEPRINT:
                # Move from BLUEPRINT to CONSTRUCT
                return _handle_build_action(client_id, task_description, context)

            elif session.state.phase == WorkflowPhase.CONSTRUCT:
                # Move from CONSTRUCT to VALIDATE
                update_session_state(
                    client_id, WorkflowPhase.VALIDATE, WorkflowStatus.RUNNING
                )
                add_log_to_session(
                    client_id, f"✅ VALIDATE PHASE STARTED: {task_description}"
                )

                return f"""✅ **VALIDATE PHASE - FINAL VERIFICATION**

**Task:** {task_description}

**📋 CURRENT WORKFLOW STATE:**
```markdown
{export_session_to_markdown(client_id)}
```

**🎯 PHASE OBJECTIVE:** Thoroughly validate the implementation meets all requirements.

**🔨 MANDATORY EXECUTION PROCESS - FOLLOW EXACTLY:**

**1. COMPREHENSIVE TESTING** ⚠️ REQUIRED
   - MUST run full test suite
   - MUST verify all functionality works as expected
   - MUST test edge cases and error conditions
   - MUST ensure no regressions introduced

**2. CODE QUALITY VALIDATION** ⚠️ REQUIRED
   - MUST verify code follows project standards
   - MUST ensure proper documentation
   - MUST check for security issues
   - MUST validate performance is acceptable

**3. REQUIREMENT VERIFICATION** ⚠️ REQUIRED
   - MUST verify all original requirements are met
   - MUST ensure task objectives are achieved
   - MUST validate acceptance criteria are satisfied

**4. FINAL DOCUMENTATION** ⚠️ REQUIRED
   - MUST update relevant documentation
   - MUST add changelog entries if required
   - MUST ensure future maintainability

**🚨 ERROR RECOVERY:**
If validation fails, call: `workflow_guidance`
Parameters: action="revise", task_description="{task_description}", context="<validation issues>"

**✅ WHEN VALIDATION IS COMPLETE:**
Update session status to COMPLETED

🎯 **Validation phase started - ensure quality and completeness!**"""

            elif session.state.phase == WorkflowPhase.VALIDATE:
                # Complete the workflow
                update_session_state(
                    client_id, WorkflowPhase.VALIDATE, WorkflowStatus.COMPLETED
                )
                add_log_to_session(
                    client_id, f"🎉 WORKFLOW COMPLETED: {task_description}"
                )

                return f"""🎉 **WORKFLOW COMPLETED**

**Task:** {task_description}

**📋 FINAL WORKFLOW STATE:**
```markdown
{export_session_to_markdown(client_id)}
```

**✅ STATUS:** Task successfully completed and validated.

**📊 WORKFLOW SUMMARY:**
- Analysis ✅
- Planning ✅
- Implementation ✅
- Validation ✅

**🎯 All phases completed successfully!**"""

            else:
                return f"❌ **Unknown phase:** {session.state.phase}"

        except Exception as e:
            return f"❌ **Error in next action:** {str(e)}"

    @app.tool()
    def workflow_state(
        operation: str = Field(
            description="State operation: 'get' (current status), 'update' (modify state), 'reset' (clear state)"
        ),
        updates: str = Field(
            default="",
            description='JSON string with state updates for \'update\' operation. Example: \'{"phase": "CONSTRUCT", "status": "RUNNING"}\'',
        ),
    ) -> str:
        """Get or update workflow state."""
        try:
            client_id = "default"  # In real implementation, extract from Context

            if operation == "get":
                # Check session type first
                session_type = get_session_type(client_id)

                if session_type == "dynamic":
                    session = get_or_create_dynamic_session(client_id, "")
                    workflow_def = get_dynamic_session_workflow_def(client_id)

                    if workflow_def:
                        current_node = workflow_def.workflow.tree.get(
                            session.current_node
                        )
                        summary = get_workflow_summary(workflow_def)

                        return f"""📊 **DYNAMIC WORKFLOW STATE**

**Workflow:** {summary["name"]}
**Current Node:** {session.current_node}
**Status:** {session.status}

**Current Goal:** {current_node.goal if current_node else "Unknown"}

**Progress:** {session.current_node} (Node {list(summary["all_nodes"]).index(session.current_node) + 1} of {summary["total_nodes"]})

**Workflow Structure:**
- **Root:** {summary["root_node"]}
- **Total Nodes:** {summary["total_nodes"]}
- **Decision Points:** {", ".join(summary["decision_nodes"]) if summary["decision_nodes"] else "None"}
- **Terminal Nodes:** {", ".join(summary["terminal_nodes"]) if summary["terminal_nodes"] else "None"}

**Session State:**
```markdown
{export_session_to_markdown(client_id)}
```"""
                    else:
                        return (
                            "❌ **Error:** Dynamic session has no workflow definition."
                        )

                else:
                    # Legacy session
                    session = get_or_create_session(client_id)
                    return f"""📊 **LEGACY WORKFLOW STATE**

**Phase:** {session.state.phase.value}
**Status:** {session.state.status.value}

**Session State:**
```markdown
{export_session_to_markdown(client_id)}
```"""

            elif operation == "update":
                if not updates:
                    return "❌ **Error:** No updates provided."

                try:
                    update_data = json.loads(updates)

                    # Update based on session type
                    session_type = get_session_type(client_id)

                    if session_type == "dynamic":
                        # Update dynamic session
                        if "node" in update_data:
                            update_dynamic_session_node(client_id, update_data["node"])
                        if "status" in update_data:
                            update_dynamic_session_status(
                                client_id, update_data["status"]
                            )
                    else:
                        # Update legacy session
                        phase = update_data.get("phase")
                        status = update_data.get("status")

                        if phase and status:
                            try:
                                phase_enum = WorkflowPhase(phase)
                                status_enum = WorkflowStatus(status)
                                update_session_state(client_id, phase_enum, status_enum)
                            except ValueError as e:
                                return f"❌ **Invalid phase/status:** {str(e)}"

                    return "✅ **State updated successfully.**"

                except json.JSONDecodeError:
                    return "❌ **Error:** Invalid JSON in updates parameter."

            elif operation == "reset":
                # Reset session (implementation depends on session manager)
                return "✅ **State reset - ready for new workflow.**"

            else:
                return f"❌ **Invalid operation:** {operation}. Use 'get', 'update', or 'reset'."

        except Exception as e:
            return f"❌ **Error in workflow_state:** {str(e)}"

def format_enhanced_node_status(node: WorkflowNode, workflow: WorkflowDefinition, session) -> str:
    """Format current node status with enhanced authoritative guidance.
    
    Args:
        node: Current workflow node
        workflow: The workflow definition  
        session: Current workflow session
        
    Returns:
        Enhanced formatted status string with authoritative guidance
    """
    from ..utils.session_manager import export_session_to_markdown
    
    analysis = analyze_node_from_schema(node, workflow)
    transitions = get_available_transitions(node, workflow)

    # Format acceptance criteria with enhanced detail
    criteria_text = ""
    if analysis["acceptance_criteria"]:
        criteria_items = []
        for key, value in analysis["acceptance_criteria"].items():
            criteria_items.append(f"   ✅ **{key}**: {value}")
        criteria_text = "\n".join(criteria_items)
    else:
        criteria_text = "   • No specific criteria defined"

    # Format next options with enhanced guidance
    options_text = ""
    if transitions:
        options_text = "**🎯 Available Next Steps:**\n"
        for transition in transitions:
            options_text += f"   • **{transition['name']}**: {transition['goal']}\n"
        options_text += '\n**📋 To Proceed:** Call workflow_guidance with context="choose: <option_name>"\n'
        options_text += '**Example:** workflow_guidance(action="next", context="choose: blueprint")'
    else:
        options_text = "**🏁 Status:** This is a terminal node (workflow complete)"

    # Add special instructions for construct phase
    construct_instructions = ""
    if session.current_node == "construct":
        construct_instructions = """

**⚠️ CRITICAL CONSTRUCT PHASE REQUIREMENTS:**

**MANDATORY PROGRESS LOGGING - FOLLOW EXACTLY:**
After EVERY major implementation step, you MUST call:
```
workflow_state(operation="update", updates='{"log_entry": "Step X: [description] - [status/result]"}')
```

**Example Progress Log Calls:**
```
workflow_state(operation="update", updates='{"log_entry": "Step 1: Created new component file - SUCCESS"}')
workflow_state(operation="update", updates='{"log_entry": "Step 2: Added validation logic - SUCCESS, tests passing"}')
workflow_state(operation="update", updates='{"log_entry": "Step 3: Updated integration points - SUCCESS, linting clean"}')
```

**DO NOT PROCEED** to the next major step until you have logged the current step's completion and verification results."""

    # Get current session state for display
    session_state = export_session_to_markdown(session.client_id)

    return f"""{analysis["goal"]}

**📋 ACCEPTANCE CRITERIA:**
{criteria_text}

{options_text}{construct_instructions}

**📊 CURRENT WORKFLOW STATE:**
```markdown
{session_state}
```

**🚨 REMEMBER:** Follow the mandatory execution steps exactly as specified. Each phase has critical requirements that must be completed before proceeding."""
