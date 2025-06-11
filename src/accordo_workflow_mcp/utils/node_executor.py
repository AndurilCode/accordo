"""Node executor for handling specific workflow node execution logic."""

from typing import Any

from ..models.workflow_state import DynamicWorkflowState
from ..models.yaml_workflow import WorkflowDefinition, WorkflowNode


class NodeExecutionResult:
    """Result of a node execution."""

    def __init__(
        self,
        success: bool,
        outputs: dict[str, Any] | None = None,
        message: str = "",
        next_node_suggestion: str | None = None,
    ):
        """Initialize execution result.

        Args:
            success: Whether the execution was successful
            outputs: Outputs produced by the node
            message: Human-readable message about the execution
            next_node_suggestion: Suggested next node to transition to
        """
        self.success = success
        self.outputs = outputs or {}
        self.message = message
        self.next_node_suggestion = next_node_suggestion


class NodeExecutor:
    """Executor for handling node-specific execution logic."""

    def execute_node(
        self,
        node: WorkflowNode,
        state: DynamicWorkflowState,
        workflow_def: WorkflowDefinition,
        user_input: dict[str, Any] | None = None,
    ) -> NodeExecutionResult:
        """Execute a workflow node.

        Args:
            node: The workflow node to execute
            state: Current workflow state
            workflow_def: Workflow definition
            user_input: Optional user input/parameters

        Returns:
            NodeExecutionResult: Result of the execution
        """
        # Log node execution start
        state.add_log_entry(f"🎯 EXECUTING NODE: {state.current_node}")
        state.add_log_entry(f"📋 GOAL: {node.goal}")

        # Check if this is a decision node
        if node.children:
            return self._execute_decision_node(node, state, workflow_def, user_input)
        else:
            return self._execute_action_node(node, state, workflow_def, user_input)

    def _execute_decision_node(
        self,
        node: WorkflowNode,
        state: DynamicWorkflowState,
        workflow_def: WorkflowDefinition,
        user_input: dict[str, Any] | None = None,
    ) -> NodeExecutionResult:
        """Execute a decision node that has children.

        Args:
            node: The decision node to execute
            state: Current workflow state
            workflow_def: Workflow definition
            user_input: Optional user input for decision making

        Returns:
            NodeExecutionResult: Result with decision outcome
        """
        state.add_log_entry(f"🔀 DECISION NODE: {len(node.children)} options available")

        # For decision nodes, we need to determine which child to follow
        # This could be based on user input, automated logic, or criteria evaluation

        if user_input and "decision" in user_input:
            # User provided explicit decision
            chosen_child = user_input["decision"]
            if chosen_child in node.children:
                state.add_log_entry(f"👤 USER DECISION: {chosen_child}")
                return NodeExecutionResult(
                    success=True,
                    outputs={"decision": chosen_child, "decision_type": "user_choice"},
                    message=f"User chose: {chosen_child}",
                    next_node_suggestion=chosen_child,
                )
            else:
                available = ", ".join(node.children.keys())
                return NodeExecutionResult(
                    success=False,
                    message=f"Invalid decision '{chosen_child}'. Available: {available}",
                )

        # Auto-decision based on node goal and current context
        suggested_child = self._auto_decide_child(node, state, workflow_def)
        if suggested_child:
            state.add_log_entry(f"🤖 AUTO DECISION: {suggested_child}")
            return NodeExecutionResult(
                success=True,
                outputs={"decision": suggested_child, "decision_type": "auto_choice"},
                message=f"Automatically chose: {suggested_child}",
                next_node_suggestion=suggested_child,
            )

        # If no automatic decision can be made, return options for user choice
        children_info = {}
        for child_name, child_node in node.children.items():
            children_info[child_name] = {
                "goal": child_node.goal,
                "acceptance_criteria": child_node.acceptance_criteria,
            }

        return NodeExecutionResult(
            success=False,
            outputs={"available_choices": children_info},
            message=f"Decision required. Available options: {', '.join(node.children.keys())}",
        )

    def _execute_action_node(
        self,
        node: WorkflowNode,
        state: DynamicWorkflowState,
        workflow_def: WorkflowDefinition,
        user_input: dict[str, Any] | None = None,
    ) -> NodeExecutionResult:
        """Execute an action node (leaf node).

        Args:
            node: The action node to execute
            state: Current workflow state
            workflow_def: Workflow definition
            user_input: Optional user input/parameters

        Returns:
            NodeExecutionResult: Result of the action execution
        """
        state.add_log_entry("⚡ ACTION NODE: Executing goal")

        # For action nodes, we focus on the goal and acceptance criteria
        # The actual execution would typically involve:
        # 1. Setting up context for the goal
        # 2. Providing guidance to achieve the goal
        # 3. Checking acceptance criteria

        # Set execution context
        execution_context = {
            "current_goal": node.goal,
            "acceptance_criteria": node.acceptance_criteria,
            "node_name": state.current_node,
            "workflow_inputs": state.inputs,
            "user_input": user_input or {},
        }

        # Update state execution context
        state.execution_context.update(execution_context)

        # Sync session after execution context update
        if hasattr(state, "session_id"):
            from .session_id_utils import sync_session_after_modification

            sync_session_after_modification(state.session_id)

        # Log acceptance criteria for user awareness
        if node.acceptance_criteria:
            state.add_log_entry("📋 ACCEPTANCE CRITERIA:")
            for criterion, description in node.acceptance_criteria.items():
                state.add_log_entry(f"  • {criterion}: {description}")

        # Check if criteria are already met (from user input)
        if user_input and "criteria_evidence" in user_input:
            evidence = user_input["criteria_evidence"]
            all_met = True
            met_criteria = {}

            for criterion in node.acceptance_criteria:
                if criterion in evidence:
                    met_criteria[criterion] = evidence[criterion]
                    state.add_log_entry(f"✅ {criterion}: {evidence[criterion]}")
                else:
                    all_met = False

            if all_met:
                # Suggest next node if available
                next_suggestion = None
                if node.next_allowed_nodes:
                    next_suggestion = node.next_allowed_nodes[0]  # Take first available

                return NodeExecutionResult(
                    success=True,
                    outputs={"completed_criteria": met_criteria, "goal_achieved": True},
                    message="All acceptance criteria met. Node execution complete.",
                    next_node_suggestion=next_suggestion,
                )

        # Node is ready for execution - provide guidance
        guidance_message = self._generate_execution_guidance(node, state, workflow_def)

        return NodeExecutionResult(
            success=True,
            outputs={"execution_guidance": guidance_message, "ready_for_work": True},
            message="Node ready for execution. Follow the guidance to complete the goal.",
        )

    def _auto_decide_child(
        self,
        node: WorkflowNode,
        state: DynamicWorkflowState,
        workflow_def: WorkflowDefinition,
    ) -> str | None:
        """Automatically decide which child node to follow.

        Args:
            node: The decision node
            state: Current workflow state
            workflow_def: Workflow definition

        Returns:
            str | None: Name of chosen child or None if can't decide
        """
        # This is a simplified auto-decision logic
        # In a real implementation, this could be much more sophisticated

        # Example: If the task mentions specific keywords, choose accordingly
        task = state.current_item or ""
        task_lower = task.lower()

        # Simple keyword-based decision
        if not node.children:
            return None

        for child_name, child_node in node.children.items():
            child_goal_lower = child_node.goal.lower()

            # Check for keyword matches
            keywords = {
                "code": ["code", "implement", "develop", "program", "function"],
                "document": ["document", "doc", "readme", "guide", "explain"],
                "test": ["test", "verify", "validate", "check"],
                "debug": ["debug", "fix", "error", "bug", "issue"],
                "plan": ["plan", "design", "architect", "blueprint"],
                "clarify": ["clarify", "question", "unclear", "ambiguous"],
            }

            for category, words in keywords.items():
                if any(word in task_lower for word in words) and (
                    category in child_name.lower()
                    or any(word in child_goal_lower for word in words)
                ):
                    return child_name

        # If no keyword match, try to match by node name similarity
        for child_name in node.children:
            if any(word in child_name.lower() for word in task_lower.split()):
                return child_name

        # No automatic decision possible
        return None

    def _generate_execution_guidance(
        self,
        node: WorkflowNode,
        state: DynamicWorkflowState,
        workflow_def: WorkflowDefinition,
    ) -> str:
        """Generate execution guidance for a node.

        Args:
            node: The node to generate guidance for
            state: Current workflow state
            workflow_def: Workflow definition

        Returns:
            str: Execution guidance text
        """
        guidance_parts = [
            f"## Current Task: {node.goal}",
            "",
            "### Instructions:",
            f"You are currently executing the '{state.current_node}' node in the '{workflow_def.name}' workflow.",
            "",
            f"**Primary Goal:** {node.goal}",
            "",
        ]

        if node.acceptance_criteria:
            guidance_parts.extend(
                [
                    "### Success Criteria:",
                    "Complete the following criteria to finish this node:",
                    "",
                ]
            )
            for criterion, description in node.acceptance_criteria.items():
                guidance_parts.append(f"- **{criterion}:** {description}")
            guidance_parts.append("")

        if node.next_allowed_nodes:
            guidance_parts.extend(
                [
                    "### Next Steps:",
                    "After completing this node, you can proceed to:",
                    "",
                ]
            )
            for next_node in node.next_allowed_nodes:
                next_node_def = workflow_def.workflow.get_node(next_node)
                if next_node_def:
                    guidance_parts.append(f"- **{next_node}:** {next_node_def.goal}")
            guidance_parts.append("")

        # Add workflow context
        if state.inputs:
            guidance_parts.extend(["### Workflow Context:", ""])
            for key, value in state.inputs.items():
                guidance_parts.append(f"- **{key}:** {value}")
            guidance_parts.append("")

        return "\n".join(guidance_parts)

    def check_node_completion(
        self,
        node: WorkflowNode,
        state: DynamicWorkflowState,
        evidence: dict[str, str] | None = None,
    ) -> tuple[bool, list[str], dict[str, str]]:
        """Check if a node's completion criteria are met.

        Args:
            node: The node to check
            state: Current workflow state
            evidence: Evidence that criteria are met

        Returns:
            tuple[bool, list[str], dict[str, str]]: (is_complete, missing_criteria, validated_evidence)
        """
        if not node.acceptance_criteria:
            # No criteria means automatically complete
            return True, [], {}

        evidence = evidence or {}
        missing_criteria = []
        validated_evidence = {}

        for criterion, description in node.acceptance_criteria.items():
            if criterion in evidence and evidence[criterion].strip():
                # Mark as satisfied with detailed evidence
                evidence_text = evidence[criterion].strip()
                validated_evidence[criterion] = evidence_text
                # Always show full evidence without truncation per user requirement
                state.add_log_entry(
                    f"✅ CRITERION SATISFIED: {criterion} - {evidence_text}"
                )
            else:
                missing_criteria.append(f"{criterion}: {description}")

        is_complete = len(missing_criteria) == 0

        if is_complete:
            state.add_log_entry(
                f"🎉 NODE COMPLETION: All criteria met for {state.current_node}"
            )
        else:
            state.add_log_entry(
                f"⏳ PENDING: {len(missing_criteria)} criteria remaining"
            )

        return is_complete, missing_criteria, validated_evidence
