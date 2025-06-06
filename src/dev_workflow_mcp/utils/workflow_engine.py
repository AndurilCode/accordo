"""Dynamic workflow engine for executing YAML-defined workflows."""

from typing import Any

from ..models.workflow_state import DynamicWorkflowState
from ..models.yaml_workflow import WorkflowDefinition
from ..utils.yaml_loader import WorkflowLoader, WorkflowLoadError
from ..utils.session_id_utils import generate_session_id


class WorkflowEngineError(Exception):
    """Exception raised when workflow engine encounters an error."""

    pass


class WorkflowEngine:
    """Engine for executing dynamic YAML-defined workflows."""

    def __init__(self, workflows_dir: str = ".workflow-commander/workflows"):
        """Initialize the workflow engine.

        Args:
            workflows_dir: Directory containing workflow YAML files
        """
        self.workflows_dir = workflows_dir
        self.loader = WorkflowLoader(workflows_dir)

    def create_composed_workflow_definition(
        self, workflow_def: WorkflowDefinition
    ) -> WorkflowDefinition:
        """Create a composed workflow definition that integrates all external workflow nodes.
        
        This method expands any workflow composition nodes by integrating the referenced
        external workflow nodes directly into the main workflow tree, creating a single
        unified workflow definition.
        
        Args:
            workflow_def: Original workflow definition that may contain composition nodes
            
        Returns:
            WorkflowDefinition: New workflow definition with all external nodes integrated
        """
        try:
            from copy import deepcopy
            
            # Create a deep copy to avoid modifying the original
            composed_def = deepcopy(workflow_def)
            new_tree = {}
            processed_workflows = set()  # Prevent circular dependencies
            
            # Track node mappings for updating references
            node_mappings = {}  # original_node -> new_node_name
            
            # Process all nodes in the original workflow
            for node_name, node in workflow_def.workflow.tree.items():
                if node.is_workflow_node:
                    # This is a composition node - integrate the external workflow
                    try:
                        external_workflow = self.loader.load_external_workflow(
                            node.workflow, None
                        )
                        
                        if not external_workflow:
                            # If external workflow can't be loaded, keep the original node
                            new_tree[node_name] = node
                            continue
                            
                        workflow_key = f"{external_workflow.name}_{node.workflow}"
                        if workflow_key in processed_workflows:
                            # Prevent circular dependencies - keep original node
                            new_tree[node_name] = node
                            continue
                            
                        processed_workflows.add(workflow_key)
                        
                        # Integrate external workflow nodes with prefixed names
                        external_nodes = {}
                        prefix = f"{node_name}_"
                        
                        # Add all external nodes with prefixed names
                        for ext_node_name, ext_node in external_workflow.workflow.tree.items():
                            prefixed_name = f"{prefix}{ext_node_name}"
                            
                            # Create a copy of the external node
                            integrated_node = deepcopy(ext_node)
                            
                            # Update references to other nodes within the external workflow
                            updated_next_nodes = []
                            for next_node in integrated_node.next_allowed_nodes:
                                if next_node in external_workflow.workflow.tree:
                                    updated_next_nodes.append(f"{prefix}{next_node}")
                                else:
                                    updated_next_nodes.append(next_node)
                            integrated_node.next_allowed_nodes = updated_next_nodes
                            
                            external_nodes[prefixed_name] = integrated_node
                            
                            # Track the mapping for the root node
                            if ext_node_name == external_workflow.workflow.root:
                                node_mappings[node_name] = prefixed_name
                        
                        # Add all external nodes to the new tree
                        new_tree.update(external_nodes)
                        
                        # Update the terminal nodes of the external workflow to point to 
                        # the original composition node's next_allowed_nodes
                        if node.next_allowed_nodes:
                            for ext_node_name, ext_node in external_nodes.items():
                                # If this external node has no next nodes (terminal), 
                                # connect it to the composition node's next nodes
                                if not ext_node.next_allowed_nodes:
                                    ext_node.next_allowed_nodes = node.next_allowed_nodes.copy()
                        
                    except Exception as e:
                        # If integration fails, keep the original node
                        new_tree[node_name] = node
                        continue
                        
                else:
                    # Regular node - keep as is
                    new_tree[node_name] = deepcopy(node)
            
            # Update all node references to account for integrated workflows
            for node_name, node in new_tree.items():
                updated_next_nodes = []
                for next_node in node.next_allowed_nodes:
                    if next_node in node_mappings:
                        updated_next_nodes.append(node_mappings[next_node])
                    else:
                        updated_next_nodes.append(next_node)
                node.next_allowed_nodes = updated_next_nodes
            
            # Update the workflow tree
            composed_def.workflow.tree = new_tree
            
            # Update root if it was a composition node
            if composed_def.workflow.root in node_mappings:
                composed_def.workflow.root = node_mappings[composed_def.workflow.root]
            
            # Update workflow name and description to indicate composition
            composed_def.name = f"{workflow_def.name} (Composed)"
            composed_def.description = f"{workflow_def.description} - Integrated with external workflows"
            
            return composed_def
            
        except Exception as e:
            # If composition fails, return the original workflow
            return workflow_def

    def initialize_workflow(
        self, client_id: str, task_description: str, workflow_name: str | None = None
    ) -> tuple[DynamicWorkflowState, WorkflowDefinition]:
        """Initialize a new workflow session with composed workflow definition.

        Args:
            client_id: Client identifier
            task_description: Description of the task
            workflow_name: Optional specific workflow name

        Returns:
            tuple[DynamicWorkflowState, WorkflowDefinition]: Initialized state and composed workflow definition
        """
        # Get workflow definition
        if workflow_name:
            workflow_def = self.loader.get_workflow_by_name(workflow_name)
            if not workflow_def:
                available_workflows = self.loader.list_workflow_names()
                raise WorkflowEngineError(
                    f"Workflow '{workflow_name}' not found. Available workflows: {available_workflows}"
                )
        else:
            workflows = self.loader.discover_workflows()
            if not workflows:
                raise WorkflowEngineError("No workflows found")
            workflow_def = next(iter(workflows.values()))

        # Create composed workflow definition with integrated external workflows
        composed_workflow_def = self.create_composed_workflow_definition(workflow_def)

        # Initialize inputs based on workflow definition
        inputs = {}
        if composed_workflow_def.inputs:
            for input_name, input_def in composed_workflow_def.inputs.items():
                if input_name == "task_description":
                    inputs[input_name] = task_description
                elif input_def.default is not None:
                    inputs[input_name] = input_def.default
                # Required inputs without defaults would need to be provided by caller

        state = DynamicWorkflowState(
            session_id=generate_session_id(),
            client_id=client_id,
            workflow_name=composed_workflow_def.name,
            current_node=composed_workflow_def.workflow.root,
            status="READY",
            inputs=inputs,
            current_item=task_description,
        )

        # Add initialization log
        state.add_log_entry(f"🚀 WORKFLOW ENGINE INITIALIZED: {composed_workflow_def.name}")
        state.add_log_entry(f"📍 Starting at root node: {composed_workflow_def.workflow.root}")
        state.add_log_entry(f"🎯 Task: {task_description}")
        state.add_log_entry(f"🔗 Composed workflow with {len(composed_workflow_def.workflow.tree)} total nodes")

        return state, composed_workflow_def

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
            if hasattr(session, 'session_id'):
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
            "is_workflow_node": current_node.is_workflow_node,
            "workflow_path": current_node.workflow if current_node.is_workflow_node else None,
            "is_decision_node": current_node.is_decision_node,
            "children": current_node.next_allowed_nodes,
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
        needs_approval = getattr(current_node, 'needs_approval', False)
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
        is_valid, reason = self.validate_transition(state, workflow_def, target_node, user_approval)
        if not is_valid:
            state.add_log_entry(f"❌ TRANSITION FAILED: {reason}")
            return False

        # Log approval if provided for a node that required it
        current_node = workflow_def.workflow.get_node(state.current_node)
        if current_node and getattr(current_node, 'needs_approval', False) and user_approval:
            state.add_log_entry(f"✅ USER APPROVAL GRANTED for transition from '{state.current_node}'")

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
                        "is_decision_node": next_node.is_decision_node,
                        "children_count": len(next_node.next_allowed_nodes),
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
                log_evidence = (
                    evidence_text
                    if len(evidence_text) <= 100
                    else evidence_text[:100] + "..."
                )
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
                        inputs[input_name] = False  # type: ignore
                    elif input_def.type == "number":
                        inputs[input_name] = 0  # type: ignore
                    else:
                        inputs[input_name] = ""  # Use empty string instead of None

        return inputs

    def execute_workflow_transition(
        self,
        state: DynamicWorkflowState,
        current_workflow_def: WorkflowDefinition,
        target_workflow_path: str,
        outputs: dict[str, Any] | None = None,
    ) -> tuple[bool, WorkflowDefinition | None, str]:
        """Execute a transition to an external workflow.

        Args:
            state: Current workflow state
            current_workflow_def: Current workflow definition
            target_workflow_path: Path to the target external workflow
            outputs: Optional outputs from current node

        Returns:
            tuple[bool, WorkflowDefinition | None, str]: (success, new_workflow_def, message)
        """
        try:
            # Get current workflow file path for relative resolution
            current_workflow_path = None
            if hasattr(state, 'workflow_file_path'):
                current_workflow_path = state.workflow_file_path
            
            # Load the external workflow
            external_workflow = self.loader.load_external_workflow(
                target_workflow_path, 
                current_workflow_path
            )
            
            if not external_workflow:
                return False, None, f"Failed to load external workflow: {target_workflow_path}"
            
            # Store previous workflow context for return
            previous_context = {
                "workflow_name": state.workflow_name,
                "current_node": state.current_node,
                "workflow_def": current_workflow_def,
                "node_outputs": outputs or {},
            }
            
            # Add to workflow stack for nested execution tracking
            state.workflow_stack.append(previous_context)
            
            # Transfer state to new workflow
            state.workflow_name = external_workflow.name
            state.current_node = external_workflow.workflow.root
            state.status = "RUNNING"
            
            # Merge inputs from current workflow to external workflow
            external_inputs = self._merge_workflow_inputs(
                state.inputs, 
                external_workflow, 
                outputs or {}
            )
            state.inputs.update(external_inputs)
            
            # Add transition logs
            state.add_log_entry(f"🔀 WORKFLOW TRANSITION: {current_workflow_def.name} → {external_workflow.name}")
            state.add_log_entry(f"📁 External workflow path: {target_workflow_path}")
            state.add_log_entry(f"📍 Starting at root node: {external_workflow.workflow.root}")
            
            return True, external_workflow, f"Successfully transitioned to workflow: {external_workflow.name}"
            
        except WorkflowLoadError as e:
            error_msg = f"Failed to load external workflow '{target_workflow_path}': {str(e)}"
            state.add_log_entry(f"❌ WORKFLOW TRANSITION FAILED: {error_msg}")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error during workflow transition: {str(e)}"
            state.add_log_entry(f"❌ WORKFLOW TRANSITION ERROR: {error_msg}")
            return False, None, error_msg

    def return_from_workflow(
        self,
        state: DynamicWorkflowState,
        completed_workflow_outputs: dict[str, Any] | None = None,
    ) -> tuple[bool, WorkflowDefinition | None, str]:
        """Return from a completed external workflow to the calling workflow.

        Args:
            state: Current workflow state
            completed_workflow_outputs: Outputs from the completed external workflow

        Returns:
            tuple[bool, WorkflowDefinition | None, str]: (success, parent_workflow_def, message)
        """
        try:
            if not state.workflow_stack:
                return False, None, "No parent workflow to return to"
            
            # Pop the previous workflow context
            previous_context = state.workflow_stack.pop()
            
            # Restore previous workflow state
            previous_workflow_name = previous_context["workflow_name"]
            previous_node = previous_context["current_node"]
            previous_workflow_def = previous_context["workflow_def"]
            
            # Store the completed workflow outputs
            if completed_workflow_outputs:
                state.workflow_outputs[state.workflow_name] = completed_workflow_outputs
            
            # Restore state
            state.workflow_name = previous_workflow_name
            state.current_node = previous_node
            state.status = "RUNNING"
            
            # Add return logs
            state.add_log_entry(f"↩️ WORKFLOW RETURN: Returned to {previous_workflow_name}")
            state.add_log_entry(f"📍 Resumed at node: {previous_node}")
            
            if completed_workflow_outputs:
                state.add_log_entry(f"📊 Workflow outputs captured: {list(completed_workflow_outputs.keys())}")
            
            return True, previous_workflow_def, f"Successfully returned to workflow: {previous_workflow_name}"
            
        except Exception as e:
            error_msg = f"Error returning from workflow: {str(e)}"
            state.add_log_entry(f"❌ WORKFLOW RETURN ERROR: {error_msg}")
            return False, None, error_msg

    def _merge_workflow_inputs(
        self,
        current_inputs: dict[str, Any],
        target_workflow: WorkflowDefinition,
        node_outputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge inputs for workflow transition.

        Args:
            current_inputs: Current workflow inputs
            target_workflow: Target workflow definition
            node_outputs: Outputs from the transitioning node

        Returns:
            dict[str, Any]: Merged inputs for target workflow
        """
        merged_inputs = {}
        
        # Start with current inputs as base
        merged_inputs.update(current_inputs)
        
        # Add node outputs as potential inputs
        merged_inputs.update(node_outputs)
        
        # Ensure required inputs for target workflow are satisfied
        for input_name, input_def in target_workflow.inputs.items():
            if input_name not in merged_inputs:
                if input_def.default is not None:
                    merged_inputs[input_name] = input_def.default
                elif input_def.required:
                    # Use sensible defaults based on type - all stored as Any in dict
                    if input_def.type == "string":
                        merged_inputs[input_name] = str(current_inputs.get("task_description", ""))
                    elif input_def.type == "boolean":
                        merged_inputs[input_name] = False
                    elif input_def.type == "number":
                        merged_inputs[input_name] = 0
                    else:
                        merged_inputs[input_name] = ""
        
        return merged_inputs
