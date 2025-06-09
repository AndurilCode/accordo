"""Pure schema analysis utilities for workflow nodes.

This module analyzes workflow schema structure without any hardcoded logic.
All node behavior is determined purely from the schema elements.
"""

from typing import Any

from ..models.yaml_workflow import WorkflowDefinition, WorkflowNode


def analyze_node_from_schema(
    node: WorkflowNode, workflow: WorkflowDefinition
) -> dict[str, Any]:
    """Analyze node characteristics purely from schema structure.

    Args:
        node: The workflow node to analyze
        workflow: The containing workflow definition

    Returns:
        Dict containing node analysis results
    """
    next_nodes = node.next_allowed_nodes or []
    next_workflows = node.next_allowed_workflows or []

    return {
        "node_name": getattr(node, "name", "unknown"),
        "goal": node.goal,
        "acceptance_criteria": node.acceptance_criteria or {},
        "has_multiple_options": len(next_nodes) > 1,
        "has_workflow_transitions": len(next_workflows) > 0,
        "is_terminal": len(next_nodes) == 0 and len(next_workflows) == 0,
        "next_nodes": next_nodes,
        "next_workflows": next_workflows,
        "total_options": len(next_nodes) + len(next_workflows),
    }


def get_available_transitions(
    node: WorkflowNode, workflow: WorkflowDefinition
) -> list[dict[str, Any]]:
    """Get available transitions from current node with approval requirements.

    Args:
        node: Current workflow node
        workflow: The workflow definition

    Returns:
        List of available transitions with their details including approval requirements
    """
    transitions = []

    # Add node transitions
    for next_node_name in node.next_allowed_nodes or []:
        next_node = workflow.workflow.get_node(next_node_name)
        if next_node:
            # Check if the target node requires approval
            needs_approval = getattr(next_node, "needs_approval", False)

            transitions.append(
                {
                    "type": "node",
                    "name": next_node_name,
                    "goal": next_node.goal,
                    "description": f"Continue to: {next_node.goal}",
                    "needs_approval": needs_approval,
                }
            )

    # Add workflow transitions
    for next_workflow_name in node.next_allowed_workflows or []:
        transitions.append(
            {
                "type": "workflow",
                "name": next_workflow_name,
                "goal": f"Switch to workflow: {next_workflow_name}",
                "description": f"Transition to: {next_workflow_name}",
                "needs_approval": False,  # Workflow transitions don't have approval requirements
            }
        )

    return transitions


def format_node_status(node: WorkflowNode, workflow: WorkflowDefinition) -> str:
    """Format current node status for display.

    Args:
        node: Current workflow node
        workflow: The workflow definition

    Returns:
        Formatted status string
    """
    analysis = analyze_node_from_schema(node, workflow)
    transitions = get_available_transitions(node, workflow)

    # Format acceptance criteria
    criteria_text = ""
    if analysis["acceptance_criteria"]:
        criteria_items = []
        for key, value in analysis["acceptance_criteria"].items():
            criteria_items.append(f"• **{key}**: {value}")
        criteria_text = "\n".join(criteria_items)
    else:
        criteria_text = "• No specific criteria defined"

    # Format next options
    options_text = ""
    if transitions:
        # Check if this node requires approval before proceeding
        needs_approval = getattr(node, "needs_approval", False)

        if needs_approval:
            options_text = "🚨 **APPROVAL REQUIRED BEFORE PROCEEDING** 🚨\n\n"
            options_text += "This node requires explicit user approval before transitioning to the next step.\n\n"

        options_text += "**Available Next Steps:**\n"
        for transition in transitions:
            options_text += f"• **{transition['name']}**: {transition['goal']}\n"

        if needs_approval:
            # Special approval guidance
            options_text += "\n⚠️ **MANDATORY APPROVAL PROCESS:**\n"
            options_text += (
                "To proceed, you must provide explicit approval in your context:\n"
            )
            options_text += '📋 **Required Format:** Call workflow_guidance with context including "user_approval": true\n'
            options_text += "🚨 **CRITICAL:** ALWAYS provide both approval AND criteria evidence when transitioning:\n"

            if len(transitions) == 1:
                # Single option - provide specific example
                example_node = transitions[0]["name"]
                options_text += f'**Example:** workflow_guidance(action="next", context=\'{{"choose": "{example_node}", "user_approval": true, "criteria_evidence": {{"criterion1": "detailed evidence"}}}}\')'
            else:
                # Multiple options - provide generic example
                options_text += '**Example:** workflow_guidance(action="next", context=\'{"choose": "node_name", "user_approval": true, "criteria_evidence": {"criterion1": "detailed evidence"}}\')'
        else:
            # Standard guidance without approval requirement
            options_text += '\n📋 **To Proceed:** Call workflow_guidance with context="choose: <option_name>"\n'
            options_text += "🚨 **CRITICAL:** ALWAYS provide criteria evidence when transitioning:\n"

            if len(transitions) == 1:
                # Single option - provide specific example
                example_node = transitions[0]["name"]
                options_text += f'**Example:** workflow_guidance(action="next", context=\'{{"choose": "{example_node}", "criteria_evidence": {{"criterion1": "detailed evidence"}}}}\')'
            else:
                # Multiple options - provide generic example
                options_text += '**Example:** workflow_guidance(action="next", context=\'{"choose": "node_name", "criteria_evidence": {"criterion1": "detailed evidence"}}\')'
    else:
        options_text = "**Status:** This is a terminal node (workflow complete)"

    return f"""🎯 **Current Goal:** {analysis["goal"]}

**Acceptance Criteria:**
{criteria_text}

{options_text}"""


def extract_choice_from_context(context: str) -> str | None:
    """Extract chosen option from context string.

    Args:
        context: Context string from user input

    Returns:
        Extracted choice or None if not found
    """
    if not context:
        return None

    context_lower = context.lower().strip()

    # Look for "choose: option_name" pattern
    if isinstance(context_lower, str) and "choose:" in context_lower:
        parts = context_lower.split("choose:", 1)
        if len(parts) > 1:
            choice = parts[1].strip()
            return choice

    return None


def extract_workflow_from_context(context: str) -> str | None:
    """Extract workflow name from context string.

    Args:
        context: Context string from user input

    Returns:
        Extracted workflow name or None if not found
    """
    if not context:
        return None

    context_lower = context.lower().strip()

    # Look for "workflow: workflow_name" pattern
    if isinstance(context_lower, str) and "workflow:" in context_lower:
        parts = context_lower.split("workflow:", 1)
        if len(parts) > 1:
            workflow_name = parts[1].strip()
            return workflow_name

    return None


def validate_transition(
    current_node: WorkflowNode, target: str, workflow: WorkflowDefinition
) -> bool:
    """Validate if transition to target is allowed by schema.

    Args:
        current_node: Current workflow node
        target: Target node or workflow name
        workflow: The workflow definition

    Returns:
        True if transition is allowed by schema
    """
    next_nodes = current_node.next_allowed_nodes or []
    next_workflows = current_node.next_allowed_workflows or []

    return target in next_nodes or target in next_workflows


def get_workflow_summary(workflow: WorkflowDefinition) -> dict[str, Any]:
    """Get summary of workflow structure.

    Args:
        workflow: The workflow definition

    Returns:
        Dictionary with workflow summary
    """
    nodes = list(workflow.workflow.tree.keys())
    root_node = workflow.workflow.root

    # Analyze workflow structure
    terminal_nodes = []
    decision_nodes = []

    for node_name, node in workflow.workflow.tree.items():
        next_options = len(
            (node.next_allowed_nodes or []) + (node.next_allowed_workflows or [])
        )

        if next_options == 0:
            terminal_nodes.append(node_name)
        elif next_options > 1:
            decision_nodes.append(node_name)

    return {
        "name": workflow.name,
        "description": workflow.description,
        "total_nodes": len(nodes),
        "root_node": root_node,
        "terminal_nodes": terminal_nodes,
        "decision_nodes": decision_nodes,
        "all_nodes": nodes,
    }
