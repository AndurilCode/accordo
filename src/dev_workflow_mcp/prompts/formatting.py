"""Formatting and error handling functions for workflow operations.

This module provides formatting for error messages, node status displays,
and other user-facing output.
"""

from typing import Any

from ..models.yaml_workflow import WorkflowDefinition, WorkflowNode
from ..utils.placeholder_processor import replace_placeholders
from ..utils.schema_analyzer import (
    analyze_node_from_schema,
    get_available_transitions,
)
from ..utils.session_manager import export_session_to_markdown


def format_yaml_error_guidance(
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
    
    # Apply placeholder replacement to the goal and acceptance criteria
    session_inputs = getattr(session, 'inputs', {}) or {}
    
    # Process the goal with placeholder replacement
    processed_goal = replace_placeholders(analysis["goal"], session_inputs)
    analysis["goal"] = processed_goal
    
    # Process acceptance criteria with placeholder replacement
    if analysis["acceptance_criteria"]:
        processed_criteria = {}
        for key, value in analysis["acceptance_criteria"].items():
            processed_criteria[key] = replace_placeholders(value, session_inputs)
        analysis["acceptance_criteria"] = processed_criteria
    
    # Process transition goals with placeholder replacement
    processed_transitions = []
    for transition in transitions:
        processed_transition = transition.copy()
        processed_transition["goal"] = replace_placeholders(transition["goal"], session_inputs)
        processed_transitions.append(processed_transition)
    transitions = processed_transitions

    # Format acceptance criteria with enhanced detail
    criteria_text = ""
    if analysis["acceptance_criteria"]:
        criteria_items = []
        for key, value in analysis["acceptance_criteria"].items():
            criteria_items.append(f"   ✅ **{key}**: {value}")
        criteria_text = "\n".join(criteria_items)
    else:
        criteria_text = "   • No specific criteria defined"

    # Format next options with approval enforcement checking
    options_text = ""
    if transitions:
        # Check if any target nodes require approval
        approval_required_transitions = [
            t for t in transitions if t.get("needs_approval", False)
        ]

        if approval_required_transitions:
            # At least one target node requires approval - show prominent enforcement message
            options_text = "🚨 **APPROVAL REQUIRED FOR NEXT TRANSITIONS** 🚨\n\n"
            options_text += "One or more available next steps require explicit user approval before proceeding.\n\n"

        options_text += "**🎯 Available Next Steps:**\n"
        for transition in transitions:
            if transition.get("needs_approval", False):
                # Mark approval-required transitions clearly
                options_text += f"   • **{transition['name']}** ⚠️ **(REQUIRES APPROVAL)**: {transition['goal']}\n"
            else:
                options_text += f"   • **{transition['name']}**: {transition['goal']}\n"

        if approval_required_transitions:
            # Special approval guidance for nodes that require approval
            options_text += "\n⚠️ **MANDATORY APPROVAL PROCESS:**\n"
            options_text += "To proceed to nodes marked **(REQUIRES APPROVAL)**, you must provide explicit approval:\n"
            options_text += '📋 **Required Format:** Include "user_approval": true in your context\n'
            options_text += "🚨 **CRITICAL:** ALWAYS provide both approval AND criteria evidence when transitioning:\n"

            if len(approval_required_transitions) == 1:
                # Single approval-required option - provide specific example
                example_node = approval_required_transitions[0]["name"]
                options_text += f'**Example:** workflow_guidance(action="next", context=\'{{"choose": "{example_node}", "user_approval": true, "criteria_evidence": {{"criterion1": "detailed evidence"}}}}\')\n'
            else:
                # Multiple approval-required options - provide generic example
                options_text += '**Example:** workflow_guidance(action="next", context=\'{"choose": "node_name", "user_approval": true, "criteria_evidence": {"criterion1": "detailed evidence"}}\')\n'

            # Add guidance for non-approval transitions if any exist
            non_approval_transitions = [
                t for t in transitions if not t.get("needs_approval", False)
            ]
            if non_approval_transitions:
                options_text += "\n📋 **For non-approval transitions:** Standard format without user_approval:\n"
                example_node = non_approval_transitions[0]["name"]
                options_text += f'**Example:** workflow_guidance(action="next", context=\'{{"choose": "{example_node}", "criteria_evidence": {{"criterion1": "detailed evidence"}}}}\')'
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
"""


def generate_node_completion_outputs(
    node_name: str,
    node_def: WorkflowNode,
    session,
    criteria_evidence: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Generate outputs for node completion.

    Args:
        node_name: Name of the completed node
        node_def: Node definition from workflow
        session: Current session
        criteria_evidence: Evidence for acceptance criteria

    Returns:
        Dict containing completion outputs and session data
    """
    # Basic completion data
    outputs = {
        "node_name": node_name,
        "completion_time": session.created_at.isoformat() if hasattr(session, 'created_at') else None,
        "criteria_evidence": criteria_evidence or {},
    }
    
    # Handle completed_criteria - use evidence if provided, otherwise use acceptance criteria descriptions
    if criteria_evidence:
        outputs["completed_criteria"] = criteria_evidence
    else:
        # Fallback to acceptance criteria descriptions from node definition
        if hasattr(node_def, "acceptance_criteria") and node_def.acceptance_criteria:
            outputs["completed_criteria"] = node_def.acceptance_criteria
        else:
            outputs["completed_criteria"] = {}

    # Add node-specific outputs if defined
    if hasattr(node_def, "outputs") and node_def.outputs:
        for output_key, output_def in node_def.outputs.items():
            # Extract value based on output definition
            if isinstance(output_def, dict):
                if "from_criteria" in output_def:
                    # Extract from criteria evidence
                    criteria_key = output_def["from_criteria"]
                    if criteria_evidence and criteria_key in criteria_evidence:
                        outputs[output_key] = criteria_evidence[criteria_key]
                elif "default" in output_def:
                    # Use default value
                    outputs[output_key] = output_def["default"]
            else:
                # Simple string output
                outputs[output_key] = str(output_def)

    return outputs


def extract_acceptance_criteria_from_text(text: str) -> list[str]:
    """Extract acceptance criteria from text content.

    Args:
        text: Text content to analyze

    Returns:
        List of extracted criteria
    """
    criteria = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        # Look for patterns that indicate acceptance criteria
        if any(pattern in line.lower() for pattern in [
            'must', 'should', 'acceptance', 'criteria', 'requirement',
            'verify', 'ensure', 'check', 'validate'
        ]) and len(line) > 10:  # Filter out very short lines
            criteria.append(line)
    
    return criteria


def generate_temporal_insights(results: list) -> str:
    """Generate temporal insights from search results.

    Args:
        results: List of search results with temporal data

    Returns:
        Formatted temporal insights string
    """
    if not results:
        return "No temporal data available for analysis."
    
    # Analyze temporal patterns
    insights = []
    
    # Count results by time periods
    recent_count = len([r for r in results if getattr(r, 'is_recent', False)])
    older_count = len(results) - recent_count
    
    if recent_count > 0:
        insights.append(f"Found {recent_count} recent related context(s)")
    if older_count > 0:
        insights.append(f"Found {older_count} historical context(s)")
    
    # Add recommendation based on temporal distribution
    if recent_count > older_count:
        insights.append("Consider leveraging recent successful patterns")
    elif older_count > recent_count:
        insights.append("Consider reviewing historical approaches for insights")
    
    return " | ".join(insights) if insights else "Limited temporal insights available" 