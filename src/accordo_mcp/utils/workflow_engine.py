"""Dynamic workflow engine for executing YAML-defined workflows."""

from typing import Any

from ..models.workflow_state import DynamicWorkflowState
from ..models.yaml_workflow import WorkflowDefinition
from ..utils.yaml_loader import WorkflowLoader


class WorkflowEngineError(Exception):
    """Exception raised when workflow engine encounters an error."""

    pass


class WorkflowEngine:
    """Engine for executing dynamic YAML-defined workflows."""

    def __init__(self, workflows_dir: str = ".accordo/workflows"):
        """Initialize the workflow engine.

        Args:
            workflows_dir: Directory containing workflow YAML files
        """
        self.workflows_dir = workflows_dir
        self.loader = WorkflowLoader(workflows_dir)

    def initialize_workflow(
        self, client_id: str, task_description: str, workflow_name: str | None = None
    ) -> tuple[DynamicWorkflowState, WorkflowDefinition]:
        """Initialize a new workflow execution.

        Args:
            client_id: Client session identifier
            task_description: Description of the task to process
            workflow_name: Optional specific workflow name to use

        Returns:
            tuple[DynamicWorkflowState, WorkflowDefinition]: The initial state and workflow definition

        Raises:
            WorkflowEngineError: If no suitable workflow is found
        """
        # Find appropriate workflow
        if workflow_name:
            workflows = self.loader.discover_workflows()
            if workflow_name not in workflows:
                raise WorkflowEngineError(f"Workflow '{workflow_name}' not found")
            workflow_def = workflows[workflow_name]
        else:
            # Pure discovery system - cannot auto-select workflow without agent choice
            raise WorkflowEngineError(
                "Workflow name required - use pure discovery system for workflow selection"
            )

        # Validate and prepare inputs
        inputs = self._prepare_inputs(task_description, workflow_def)

        # Create initial state
        state = DynamicWorkflowState(
            client_id=client_id,
            workflow_name=workflow_def.name,
            current_node=workflow_def.workflow.root,
            status="READY",
            inputs=inputs,
            current_item=task_description,
        )

        # Add initialization log
        state.add_log_entry(f"🚀 WORKFLOW ENGINE INITIALIZED: {workflow_def.name}")
        state.add_log_entry(f"📍 Starting at root node: {workflow_def.workflow.root}")
        state.add_log_entry(f"🎯 Task: {task_description}")

        return state, workflow_def

    def initialize_workflow_from_definition(
        self, session: "DynamicWorkflowState", workflow_def: "WorkflowDefinition"
    ) -> bool:
        """Initialize a workflow session with a given workflow definition.

        Args:
            session: Existing dynamic workflow session to initialize
            workflow_def: The workflow definition to use

        Returns:
            bool: True if initialization was successful
        """
        try:
            # Update session with workflow information
            session.workflow_name = workflow_def.name
            session.current_node = workflow_def.workflow.root
            session.status = "READY"

            # Add initialization logs
            session.add_log_entry(f"🚀 WORKFLOW INITIALIZED: {workflow_def.name}")
            session.add_log_entry(
                f"📍 Starting at root node: {workflow_def.workflow.root}"
            )

            # Sync session after initialization updates
            if hasattr(session, "session_id"):
                from .session_id_utils import sync_session_after_modification

                sync_session_after_modification(session.session_id)

            return True

        except Exception:
            return False

    def get_current_node_info(
        self, state: DynamicWorkflowState, workflow_def: WorkflowDefinition
    ) -> dict[str, Any]:
        """Get information about the current node.

        Args:
            state: Current workflow state
            workflow_def: Workflow definition

        Returns:
            dict[str, Any]: Information about the current node
        """
        current_node = workflow_def.workflow.get_node(state.current_node)
        if not current_node:
            return {"error": f"Node '{state.current_node}' not found in workflow"}

        return {
            "node_name": state.current_node,
            "goal": current_node.goal,
            "acceptance_criteria": current_node.acceptance_criteria,
            "next_allowed_nodes": current_node.next_allowed_nodes,
            "next_allowed_workflows": current_node.next_allowed_workflows,
            "is_decision_node": bool(current_node.children),
            "children": list(current_node.children.keys())
            if current_node.children
            else [],
            "workflow_info": {
                "name": workflow_def.name,
                "description": workflow_def.description,
                "total_nodes": len(workflow_def.workflow.tree),
            },
        }

    def validate_transition(
        self,
        state: DynamicWorkflowState,
        workflow_def: WorkflowDefinition,
        target_node: str,
        user_approval: bool = False,
    ) -> tuple[bool, str]:
        """Validate if a transition to target node is allowed.

        Args:
            state: Current workflow state
            workflow_def: Workflow definition
            target_node: Node to transition to
            user_approval: Whether user has provided explicit approval

        Returns:
            tuple[bool, str]: (is_valid, reason)
        """
        current_node = workflow_def.workflow.get_node(state.current_node)
        if not current_node:
            return False, f"Current node '{state.current_node}' not found"

        # Check if target node exists
        target_node_def = workflow_def.workflow.get_node(target_node)
        if not target_node_def:
            return False, f"Target node '{target_node}' not found in workflow"

        # Check if transition is allowed
        if target_node not in current_node.next_allowed_nodes:
            allowed = ", ".join(current_node.next_allowed_nodes)
            return (
                False,
                f"Transition to '{target_node}' not allowed from '{state.current_node}'. Allowed: {allowed}",
            )

        # Check if current node requires approval for transition
        # Only check approval for non-terminal nodes (nodes with next_allowed_nodes)
        needs_approval = getattr(current_node, "needs_approval", False)
        if needs_approval and current_node.next_allowed_nodes and not user_approval:
            return (
                False,
                f"Node '{state.current_node}' requires explicit user approval before transition. "
                f"Provide 'user_approval': true in your context to proceed, ONLY WHEN THE USER HAS PROVIDED EXPLICIT APPROVAL.",
            )

        return True, "Transition is valid"

    def execute_transition(
        self,
        state: DynamicWorkflowState,
        workflow_def: WorkflowDefinition,
        target_node: str,
        outputs: dict[str, Any] | None = None,
        user_approval: bool = False,
    ) -> bool:
        """Execute a transition to a new node.

        Args:
            state: Current workflow state
            workflow_def: Workflow definition
            target_node: Node to transition to
            outputs: Optional outputs from the current node
            user_approval: Whether user has provided explicit approval

        Returns:
            bool: True if transition was successful
        """
        # Validate transition including approval check
        is_valid, reason = self.validate_transition(
            state, workflow_def, target_node, user_approval
        )
        if not is_valid:
            state.add_log_entry(f"❌ TRANSITION FAILED: {reason}")
            return False

        # Log approval if provided for a node that required it
        current_node = workflow_def.workflow.get_node(state.current_node)
        if (
            current_node
            and getattr(current_node, "needs_approval", False)
            and user_approval
        ):
            state.add_log_entry(
                f"✅ USER APPROVAL GRANTED for transition from '{state.current_node}'"
            )

        # Complete current node if outputs provided
        if outputs:
            state.complete_current_node(outputs)

        # Execute the transition
        success = state.transition_to_node(target_node, workflow_def)
        if success:
            # Update status based on new node
            target_node_def = workflow_def.workflow.get_node(target_node)
            if target_node_def:
                state.status = "RUNNING"
                state.add_log_entry(f"📝 CURRENT GOAL: {target_node_def.goal}")

        return success

    def get_available_transitions(
        self, state: DynamicWorkflowState, workflow_def: WorkflowDefinition
    ) -> list[dict[str, Any]]:
        """Get all available transitions from the current node.

        Args:
            state: Current workflow state
            workflow_def: Workflow definition

        Returns:
            list[dict[str, Any]]: List of available transitions with their details
        """
        current_node = workflow_def.workflow.get_node(state.current_node)
        if not current_node:
            return []

        transitions = []
        for next_node_name in current_node.next_allowed_nodes:
            next_node = workflow_def.workflow.get_node(next_node_name)
            if next_node:
                transitions.append(
                    {
                        "node_name": next_node_name,
                        "goal": next_node.goal,
                        "acceptance_criteria": next_node.acceptance_criteria,
                        "is_decision_node": bool(next_node.children),
                        "children_count": len(next_node.children)
                        if next_node.children
                        else 0,
                    }
                )

        return transitions

    def check_completion_criteria(
        self,
        state: DynamicWorkflowState,
        workflow_def: WorkflowDefinition,
        provided_evidence: dict[str, str] | None = None,
    ) -> tuple[bool, list[str]]:
        """Check if current node's completion criteria are met.

        Args:
            state: Current workflow state
            workflow_def: Workflow definition
            provided_evidence: Optional evidence that criteria are met

        Returns:
            tuple[bool, list[str]]: (all_met, missing_criteria)
        """
        current_node = workflow_def.workflow.get_node(state.current_node)
        if not current_node:
            return False, ["Current node not found"]

        if not current_node.acceptance_criteria:
            # No criteria means automatically met
            return True, []

        missing_criteria = []

        # For now, we'll do a simple check based on provided evidence
        # In a more sophisticated implementation, this could include automated checks
        for (
            criterion_name,
            criterion_description,
        ) in current_node.acceptance_criteria.items():
            if provided_evidence and criterion_name in provided_evidence:
                # Evidence provided for this criterion with truncation for readability
                evidence_text = provided_evidence[criterion_name].strip()
                log_evidence = evidence_text
                state.add_log_entry(
                    f"✅ CRITERION MET: {criterion_name} - {log_evidence}"
                )
            else:
                missing_criteria.append(f"{criterion_name}: {criterion_description}")

        all_met = len(missing_criteria) == 0

        if all_met:
            state.add_log_entry(
                f"🎉 ALL ACCEPTANCE CRITERIA MET for node: {state.current_node}"
            )
        else:
            state.add_log_entry(
                f"⏳ PENDING CRITERIA for node {state.current_node}: {len(missing_criteria)} remaining"
            )

        return all_met, missing_criteria

    def get_workflow_progress(
        self, state: DynamicWorkflowState, workflow_def: WorkflowDefinition
    ) -> dict[str, Any]:
        """Get progress information for the workflow.

        Args:
            state: Current workflow state
            workflow_def: Workflow definition

        Returns:
            dict[str, Any]: Progress information
        """
        total_nodes = len(workflow_def.workflow.tree)
        visited_nodes = len(set(state.node_history + [state.current_node]))

        # Calculate completion percentage (simplified)
        progress_percentage = (
            (visited_nodes / total_nodes) * 100 if total_nodes > 0 else 0
        )

        return {
            "current_node": state.current_node,
            "total_nodes": total_nodes,
            "visited_nodes": visited_nodes,
            "progress_percentage": round(progress_percentage, 1),
            "node_history": state.node_history,
            "workflow_name": workflow_def.name,
            "workflow_description": workflow_def.description,
            "status": state.status,
            "execution_context": state.execution_context,
        }

    def is_workflow_complete(
        self, state: DynamicWorkflowState, workflow_def: WorkflowDefinition
    ) -> bool:
        """Check if the workflow execution is complete.

        Args:
            state: Current workflow state
            workflow_def: Workflow definition

        Returns:
            bool: True if workflow is complete
        """
        current_node = workflow_def.workflow.get_node(state.current_node)
        if not current_node:
            return False

        # Workflow is complete if:
        # 1. Current node has no next allowed nodes (terminal node)
        # 2. Or status indicates completion
        is_terminal = len(current_node.next_allowed_nodes) == 0
        is_completed_status = state.status.upper() in [
            "COMPLETED",
            "FINISHED",
            "SUCCESS",
        ]

        return is_terminal or is_completed_status

    def _prepare_inputs(
        self, task_description: str, workflow_def: WorkflowDefinition
    ) -> dict[str, Any]:
        """Prepare and validate workflow inputs.

        Args:
            task_description: The task description
            workflow_def: Workflow definition

        Returns:
            dict[str, Any]: Prepared inputs
        """
        inputs = {}

        # Set basic inputs
        if "task_description" in workflow_def.inputs:
            inputs["task_description"] = task_description
        elif "task" in workflow_def.inputs:
            inputs["task"] = task_description
        else:
            # Add as generic input
            inputs["main_task"] = task_description

        # Set defaults for other required inputs
        for input_name, input_def in workflow_def.inputs.items():
            if input_name not in inputs:
                if input_def.default is not None:
                    inputs[input_name] = input_def.default
                elif input_def.required:
                    # For required inputs without defaults, use sensible defaults based on type
                    if input_def.type == "string":
                        inputs[input_name] = ""
                    elif input_def.type == "boolean":
                        inputs[input_name] = False
                    elif input_def.type == "number":
                        inputs[input_name] = 0
                    else:
                        inputs[input_name] = None

        return inputs
