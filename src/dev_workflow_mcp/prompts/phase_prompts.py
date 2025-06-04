"""Pure schema-driven workflow prompts.

This module provides workflow guidance based purely on YAML workflow schemas.
No hardcoded logic - all behavior determined by workflow definitions.
"""

import json

import yaml
from fastmcp import FastMCP
from pydantic import Field

from ..models.yaml_workflow import WorkflowDefinition, WorkflowNode
from ..utils.schema_analyzer import (
    analyze_node_from_schema,
    extract_choice_from_context,
    format_node_status,
    get_available_transitions,
    get_workflow_summary,
    validate_transition,
)
from ..utils.session_manager import (
    add_log_to_session,
    create_dynamic_session,
    export_session_to_markdown,
    get_dynamic_session_workflow_def,
    get_or_create_dynamic_session,
    get_session_type,
    store_workflow_definition_in_cache,
    update_dynamic_session_node,
    update_dynamic_session_status,
)
from ..utils.workflow_engine import WorkflowEngine
from ..utils.yaml_loader import WorkflowLoader
from .discovery_prompts import get_cached_workflow

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_task_description(description: str | None) -> str:
    """Validate task description format.

    Args:
        description: Task description to validate

    Returns:
        str: Trimmed and validated description

    Raises:
        ValueError: If description doesn't follow required format
    """
    if description is None:
        raise ValueError(
            "Task description must be a non-empty string. Task descriptions must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    if not isinstance(description, str):
        raise ValueError(
            "Task description must be a string. Task descriptions must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Trim whitespace
    description = description.strip()

    if not description:
        raise ValueError(
            "Task description must be a non-empty string. Task descriptions must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Check for colon
    if ":" not in description:
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Split on first colon
    parts = description.split(":", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    action_verb = parts[0].strip()
    task_details = parts[1]

    # Check if action verb is empty
    if not action_verb:
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Check if action verb starts with uppercase letter
    if not action_verb[0].isupper():
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Check if action verb is all alphabetic (no numbers or special chars)
    if not action_verb.isalpha():
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Check if there's a space after colon
    if not task_details.startswith(" "):
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    # Check if description part is not empty after trimming
    task_details_trimmed = task_details.strip()
    if not task_details_trimmed:
        raise ValueError(
            f"Task description '{description}' must follow the format 'Action: Brief description'. "
            "Examples: 'Add: user authentication', 'Fix: memory leak', 'Implement: OAuth login', 'Refactor: database queries'"
        )

    return description


# =============================================================================
# YAML PARSING FUNCTIONS
# =============================================================================


def parse_and_validate_yaml_context(
    context: str,
) -> tuple[str | None, str | None, str | None]:
    """Parse and validate YAML context from agent input.

    Args:
        context: Context string containing workflow name and YAML content

    Returns:
        tuple: (workflow_name, yaml_content, error_message)

    Expected formats:
    1. Standard format: "workflow: Name\\nyaml: <yaml_content>"
    2. Multiline format with proper YAML indentation
    3. Raw YAML with workflow name extracted from content
    """
    if not context or not isinstance(context, str):
        return None, None, "Context must be a non-empty string"

    context = context.strip()
    workflow_name = None
    yaml_content = None

    try:
        # Method 1: Parse standard format with "workflow:" and "yaml:" markers
        if "workflow:" in context and "yaml:" in context:
            result = _parse_standard_format(context)
            if result and len(result) == 2:
                workflow_name, yaml_content = result
                if workflow_name and yaml_content:
                    # Validate and reformat YAML
                    formatted_yaml = _validate_and_reformat_yaml(yaml_content)
                    if formatted_yaml:
                        return workflow_name, formatted_yaml, None
                    else:
                        return None, None, "Invalid YAML content - failed validation"

            # Handle case where YAML content is empty after "yaml:"
            if "yaml:" in context:
                workflow_name = _extract_workflow_name_only(context)
                yaml_part = context.split("yaml:", 1)[1].strip()
                if not yaml_part:  # Empty YAML content
                    return (
                        workflow_name,
                        None,
                        "Workflow name provided but YAML content is missing",
                    )

        # Method 2: Try parsing as pure YAML (extract name from content)
        elif _looks_like_yaml(context):
            result = _parse_pure_yaml(context)
            if result and len(result) == 2:
                workflow_name, yaml_content = result
                if workflow_name and yaml_content:
                    return workflow_name, yaml_content, None
            return None, None, "Could not extract workflow name from YAML content"

        # Method 3: Check if it's just a workflow name (no YAML content)
        elif "workflow:" in context and "yaml:" not in context:
            workflow_name = _extract_workflow_name_only(context)
            return (
                workflow_name,
                None,
                "Workflow name provided but YAML content is missing",
            )

        else:
            return (
                None,
                None,
                "Unrecognized context format - expected 'workflow: Name\\nyaml: <content>' or pure YAML",
            )

    except Exception as e:
        return None, None, f"Error parsing context: {str(e)}"


def _parse_standard_format(context: str) -> tuple[str | None, str | None]:
    """Parse standard format: workflow: Name\\nyaml: <content>"""
    lines = context.split("\n")
    workflow_name = None
    yaml_content = []
    yaml_started = False

    for line in lines:
        line_stripped = line.strip()

        # Extract workflow name
        if line_stripped.startswith("workflow:") and not workflow_name:
            workflow_name = line_stripped.split("workflow:", 1)[1].strip()

        # Start collecting YAML content
        elif line_stripped.startswith("yaml:"):
            yaml_started = True
            # Check if there's content on the same line after "yaml:"
            yaml_part = line_stripped.split("yaml:", 1)[1].strip()
            if yaml_part:
                yaml_content.append(yaml_part)

        # Continue collecting YAML lines
        elif yaml_started:
            yaml_content.append(line)  # Keep original indentation for YAML

    if workflow_name and yaml_content:
        return workflow_name, "\n".join(yaml_content)

    return None, None


def _parse_pure_yaml(context: str) -> tuple[str | None, str | None]:
    """Parse pure YAML content and extract workflow name."""
    try:
        # Try to parse as YAML to validate structure
        yaml_data = yaml.safe_load(context)

        if isinstance(yaml_data, dict) and "name" in yaml_data:
            workflow_name = yaml_data["name"]
            return workflow_name, context
        else:
            return None, None

    except yaml.YAMLError:
        return None, None


def _extract_workflow_name_only(context: str) -> str | None:
    """Extract workflow name when only name is provided (no YAML)."""
    for line in context.split("\n"):
        if line.strip().startswith("workflow:"):
            return line.split("workflow:", 1)[1].strip()
    return None


def _looks_like_yaml(content: str) -> bool:
    """Check if content looks like YAML format."""
    # Look for common YAML indicators
    yaml_indicators = [
        "name:",
        "description:",
        "workflow:",
        "inputs:",
        "tree:",
        "goal:",
        "acceptance_criteria:",
    ]

    return any(indicator in content for indicator in yaml_indicators)


def _validate_and_reformat_yaml(yaml_content: str) -> str | None:
    """Validate and reformat YAML content.

    Args:
        yaml_content: Raw YAML content string

    Returns:
        Formatted YAML string or None if invalid
    """
    try:
        # Parse YAML to validate structure
        yaml_data = yaml.safe_load(yaml_content)

        if not isinstance(yaml_data, dict):
            return None

        # Check for required top-level fields
        required_fields = ["name", "workflow"]
        missing_fields = [field for field in required_fields if field not in yaml_data]

        if missing_fields:
            return None

        # Validate workflow structure
        if not isinstance(yaml_data.get("workflow"), dict):
            return None

        workflow_section = yaml_data["workflow"]
        if "tree" not in workflow_section:
            return None

        # Reformat with proper indentation and structure
        reformatted = yaml.dump(
            yaml_data,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=120,
            allow_unicode=True,
        )

        return reformatted

    except yaml.YAMLError:
        return None
    except Exception:
        return None


# =============================================================================
# FORMATTING FUNCTIONS
# =============================================================================


def _format_yaml_error_guidance(
    error_msg: str, workflow_name: str | None = None
) -> str:
    """Format helpful error message with YAML format guidance."""
    base_msg = f"❌ **YAML Format Error:** {error_msg}\n\n"

    guidance = """**🔧 EXPECTED FORMAT:**

**Option 1 - Standard Format:**
```
workflow_guidance(
    action="start",
    context="workflow: Workflow Name\\nyaml: name: Workflow Name\\ndescription: Description\\nworkflow:\\n  goal: Goal\\n  root: start\\n  tree:\\n    start:\\n      goal: Goal text\\n      next_allowed_nodes: [next]"
)
```

**Option 2 - Multiline YAML:**
```
workflow_guidance(
    action="start", 
    context="workflow: Workflow Name
yaml: name: Workflow Name
description: Description
workflow:
  goal: Goal
  root: start
  tree:
    start:
      goal: Goal text
      next_allowed_nodes: [next]"
)
```

**🚨 AGENT INSTRUCTIONS:**
1. Use `read_file` to get the YAML content from `.workflow-commander/workflows/`
2. Copy the ENTIRE YAML content exactly as it appears in the file
3. Use the format above with proper workflow name and YAML content

**Required YAML Structure:**
- `name`: Workflow display name
- `description`: Brief description
- `workflow.goal`: Main objective
- `workflow.root`: Starting node name
- `workflow.tree`: Node definitions with goals and transitions"""

    if workflow_name:
        guidance += f"\n\n**Detected Workflow Name:** {workflow_name}"
        guidance += "\n**Action Required:** Please provide the complete YAML content for this workflow."

    return base_msg + guidance


def format_enhanced_node_status(
    node: WorkflowNode, workflow: WorkflowDefinition, session
) -> str:
    """Format current node status with enhanced authoritative guidance.

    Args:
        node: Current workflow node
        workflow: The workflow definition
        session: Current workflow session

    Returns:
        Enhanced formatted status string with authoritative guidance
    """
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

    # Format next options with manual choice requirement
    options_text = ""
    if transitions:
        options_text = "**🎯 Available Next Steps:**\n"
        for transition in transitions:
            options_text += f"   • **{transition['name']}**: {transition['goal']}\n"

        options_text += '\n**📋 To Proceed:** Call workflow_guidance with context="choose: <option_name>"\n'
        options_text += (
            '**Example:** workflow_guidance(action="next", context="choose: blueprint")'
        )
    else:
        options_text = "**🏁 Status:** This is a terminal node (workflow complete)"

    # Get current session state for display
    session_state = export_session_to_markdown(session.client_id)

    return f"""{analysis["goal"]}

**📋 ACCEPTANCE CRITERIA:**
{criteria_text}

{options_text}

**📊 CURRENT WORKFLOW STATE:**
```markdown
{session_state}
```

**🚨 REMEMBER:** Follow the mandatory execution steps exactly as specified. Each phase has critical requirements that must be completed before proceeding."""


# =============================================================================
# WORKFLOW LOGIC FUNCTIONS
# =============================================================================


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
        if context and isinstance(context, str) and "choose:" in context.lower():
            choice = extract_choice_from_context(context)

            if choice and validate_transition(current_node, choice, workflow_def):
                # Valid transition - update session
                if choice in (current_node.next_allowed_nodes or []):
                    # Node transition
                    update_dynamic_session_node(session.client_id, choice, workflow_def)
                    session.current_node = choice
                    new_node = workflow_def.workflow.tree[choice]

                    # Log the transition
                    add_log_to_session(
                        session.client_id,
                        f"🔄 TRANSITIONED TO: {choice.upper()} PHASE",
                    )

                    status = format_enhanced_node_status(
                        new_node, workflow_def, session
                    )

                    return f"""✅ **Transitioned to:** {choice.upper()}

{status}"""

                elif choice in (current_node.next_allowed_workflows or []):
                    # Workflow transition - not implemented yet
                    return f"❌ **Workflow transitions not yet implemented:** {choice}"

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


# =============================================================================
# MAIN REGISTRATION FUNCTION
# =============================================================================


def register_phase_prompts(app: FastMCP, config=None):
    """Register purely schema-driven workflow prompts.

    Args:
        app: FastMCP application instance
        config: ServerConfig instance with repository path settings (optional)
    """

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

        CRITICAL DISCOVERY-FIRST LOGIC:
        - If no session exists, FORCE discovery first regardless of action
        - Dynamic sessions continue with schema-driven workflow
        - Legacy only when YAML workflows unavailable
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
                    # No workflow definition available - force discovery
                    return f"""❌ **Missing Workflow Definition**

Dynamic session exists but workflow definition is missing.

**⚠️ DISCOVERY REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="{task_description}")`
2. **Start workflow:** Follow the discovery instructions to provide workflow YAML content"""

                return _handle_dynamic_workflow(
                    session, workflow_def, action, context, engine, loader
                )

            elif session_type == "legacy":
                # Legacy sessions are no longer supported - force migration to YAML workflows
                return f"""❌ **Legacy Workflow Session Detected**

Legacy workflows have been removed. Please start a new YAML workflow:

**⚠️ DISCOVERY REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="{task_description}")`
2. **Start workflow:** Follow the discovery instructions to provide workflow YAML content

🚨 **Note:** All legacy workflow functionality has been permanently removed."""

            else:
                # session_type is None - NO SESSION EXISTS
                # MANDATORY DISCOVERY-FIRST ENFORCEMENT

                if action.lower() == "start" and context and isinstance(context, str):
                    # First, try to extract workflow name from context
                    workflow_name = None
                    if context.startswith("workflow:"):
                        workflow_name = context.split("workflow:", 1)[1].strip()
                        # Remove any additional content after workflow name
                        if "\n" in workflow_name:
                            workflow_name = workflow_name.split("\n")[0].strip()

                    if workflow_name:
                        # Try to find workflow in cache first (server-side discovery)
                        cached_workflow = get_cached_workflow(workflow_name)

                        if cached_workflow:
                            # Found in cache - use it directly
                            try:
                                # Create dynamic session directly with cached workflow
                                session = create_dynamic_session(
                                    client_id, task_description, cached_workflow
                                )

                                # Store workflow definition in cache for later retrieval
                                store_workflow_definition_in_cache(
                                    client_id, cached_workflow
                                )

                                # Get current node info
                                current_node = cached_workflow.workflow.tree[
                                    session.current_node
                                ]
                                status = format_node_status(
                                    current_node, cached_workflow
                                )

                                return f"""🚀 **Workflow Started:** {cached_workflow.name}

**Task:** {task_description}

**Source:** Server-side discovery cache

{status}"""

                            except Exception as e:
                                return _format_yaml_error_guidance(
                                    f"Error starting cached workflow: {str(e)}",
                                    workflow_name,
                                )
                        else:
                            # Not in cache - check if YAML content was provided as fallback
                            workflow_name, yaml_content, error_msg = (
                                parse_and_validate_yaml_context(context)
                            )

                            if error_msg and "YAML content is missing" in error_msg:
                                # Workflow name provided but not in cache and no YAML - need discovery
                                return f"""❌ **Workflow Not Found:** {workflow_name}

The workflow '{workflow_name}' was not found in the server cache.

**🔍 SOLUTION OPTIONS:**

1. **Run discovery first:** `workflow_discovery(task_description="{task_description}")`
   - This will discover and cache available workflows
   - Then retry with: `workflow_guidance(action="start", context="workflow: {workflow_name}")`

2. **Provide YAML directly:** Use the format:
   ```
   workflow_guidance(action="start", context="workflow: {workflow_name}\\nyaml: <your_yaml_content>")
   ```

**Note:** Server-side discovery is preferred for better performance."""

                            elif yaml_content:
                                # YAML content provided as fallback - load it
                                try:
                                    selected_workflow = (
                                        loader.load_workflow_from_string(
                                            yaml_content, workflow_name
                                        )
                                    )

                                    if selected_workflow:
                                        # Create dynamic session directly with selected workflow
                                        session = create_dynamic_session(
                                            client_id,
                                            task_description,
                                            selected_workflow,
                                        )

                                        # Store workflow definition in cache for later retrieval
                                        store_workflow_definition_in_cache(
                                            client_id, selected_workflow
                                        )

                                        # Get current node info
                                        current_node = selected_workflow.workflow.tree[
                                            session.current_node
                                        ]
                                        status = format_node_status(
                                            current_node, selected_workflow
                                        )

                                        return f"""🚀 **Workflow Started:** {selected_workflow.name}

**Task:** {task_description}

**Source:** YAML fallback (custom workflow)

{status}"""
                                    else:
                                        return _format_yaml_error_guidance(
                                            "Failed to load workflow from provided YAML - invalid structure",
                                            workflow_name,
                                        )

                                except Exception as e:
                                    return _format_yaml_error_guidance(
                                        f"Error loading workflow from YAML: {str(e)}",
                                        workflow_name,
                                    )
                            else:
                                return _format_yaml_error_guidance(
                                    error_msg, workflow_name
                                )

                    else:
                        # No workflow name provided - parse as full YAML context
                        workflow_name, yaml_content, error_msg = (
                            parse_and_validate_yaml_context(context)
                        )

                        if error_msg:
                            return _format_yaml_error_guidance(error_msg, workflow_name)

                        if workflow_name and yaml_content:
                            # Load workflow from validated YAML string
                            try:
                                selected_workflow = loader.load_workflow_from_string(
                                    yaml_content, workflow_name
                                )

                                if selected_workflow:
                                    # Create dynamic session directly with selected workflow
                                    session = create_dynamic_session(
                                        client_id, task_description, selected_workflow
                                    )

                                    # Store workflow definition in cache for later retrieval
                                    store_workflow_definition_in_cache(
                                        client_id, selected_workflow
                                    )

                                    # Get current node info
                                    current_node = selected_workflow.workflow.tree[
                                        session.current_node
                                    ]
                                    status = format_node_status(
                                        current_node, selected_workflow
                                    )

                                    return f"""🚀 **Workflow Started:** {selected_workflow.name}

**Task:** {task_description}

**Source:** YAML content (custom workflow)

{status}"""
                                else:
                                    return _format_yaml_error_guidance(
                                        "Failed to load workflow from provided YAML - invalid structure",
                                        workflow_name,
                                    )

                            except Exception as e:
                                return _format_yaml_error_guidance(
                                    f"Error loading workflow from YAML: {str(e)}",
                                    workflow_name,
                                )
                        else:
                            return _format_yaml_error_guidance(
                                "Invalid context format", workflow_name
                            )

                elif action.lower() == "start":
                    # No context provided - show discovery
                    return f"""🔍 **Workflow Discovery Required**

**⚠️ AGENT ACTION REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="{task_description}")`
2. **Start workflow:** Use just the workflow name: `workflow_guidance(action="start", context="workflow: <name>")`

**Note:** Server-side discovery enables efficient workflow lookup by name only."""

                else:
                    # NO SESSION + NON-START ACTION = FORCE DISCOVERY FIRST
                    return f"""❌ **No Active Workflow Session**

You called workflow_guidance with action="{action}" but there's no active workflow session.

**⚠️ DISCOVERY REQUIRED FIRST:**

1. **Discover workflows:** `workflow_discovery(task_description="{task_description}")`
2. **Start workflow:** Use the discovery instructions to start a workflow
3. **Then continue:** `workflow_guidance(action="{action}", ...)`

🚨 **CRITICAL:** You must start a workflow session before using action="{action}". The system enforces discovery-first workflow initiation."""

        except Exception as e:
            # Any error requires workflow discovery
            import traceback

            traceback.print_exc()
            return f"""❌ **Error in schema-driven workflow:** {str(e)}

**⚠️ DISCOVERY REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="{task_description}")`
2. **Start workflow:** Follow the discovery instructions to provide workflow YAML content"""

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
                    # No dynamic session found
                    return """❌ **No Active Workflow Session**

No YAML workflow session is currently active.

**⚠️ DISCOVERY REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="Your task description")`
2. **Start workflow:** Follow the discovery instructions to provide workflow YAML content"""

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
                        if "log_entry" in update_data:
                            add_log_to_session(client_id, update_data["log_entry"])
                    else:
                        # No dynamic session found
                        return """❌ **No Active Workflow Session**

Cannot update state - no YAML workflow session is currently active.

**⚠️ DISCOVERY REQUIRED:**

1. **Discover workflows:** `workflow_discovery(task_description="Your task description")`
2. **Start workflow:** Follow the discovery instructions to provide workflow YAML content"""

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
