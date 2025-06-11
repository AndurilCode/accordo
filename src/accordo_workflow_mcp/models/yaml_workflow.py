"""YAML workflow definition models."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class WorkflowInput(BaseModel):
    """Input definition for workflows."""

    type: str = Field(description="Input type (e.g., 'string', 'boolean')")
    description: str = Field(description="Input description")
    required: bool = Field(default=True, description="Whether input is required")
    default: Any | None = Field(default=None, description="Default value")


class WorkflowNode(BaseModel):
    """A single node in a workflow tree."""

    goal: str = Field(description="Goal description for this node")
    acceptance_criteria: dict[str, str] = Field(
        default_factory=dict,
        description="Criteria that must be met to complete this node",
    )
    next_allowed_nodes: list[str] = Field(
        default_factory=list,
        description="List of node names that can be reached from this node",
    )
    next_allowed_workflows: list[str] = Field(
        default_factory=list,
        description="List of external workflows that can be called from this node",
    )
    needs_approval: bool = Field(
        default=False,
        description="Whether this node requires explicit user approval before proceeding to next node execution. Ignored for terminal nodes.",
    )

    @property
    def is_leaf_node(self) -> bool:
        """Check if this is a leaf node (no children)."""
        return (
            len(self.next_allowed_nodes) == 0 and len(self.next_allowed_workflows) == 0
        )

    @property
    def is_decision_node(self) -> bool:
        """Check if this is a decision node (has children)."""
        return not self.is_leaf_node


class WorkflowTree(BaseModel):
    """Workflow tree structure with all nodes."""

    goal: str = Field(description="Overall goal of the workflow")
    root: str = Field(description="Root node name")
    tree: dict[str, WorkflowNode] = Field(description="All nodes in the workflow tree")

    @field_validator("tree")
    @classmethod
    def validate_tree_structure(
        cls, v: dict[str, WorkflowNode]
    ) -> dict[str, WorkflowNode]:
        """Validate the workflow tree structure."""
        if not v:
            raise ValueError("Workflow tree cannot be empty")

        # Get all node names
        node_names = set(v.keys())

        # Validate that all referenced nodes exist
        for node_name, node in v.items():
            for next_node in node.next_allowed_nodes:
                if next_node not in node_names:
                    raise ValueError(
                        f"Node '{node_name}' references non-existent node '{next_node}'"
                    )

        return v

    def get_node(self, node_name: str) -> WorkflowNode | None:
        """Get a node by name."""
        return self.tree.get(node_name)

    def get_root_node(self) -> WorkflowNode | None:
        """Get the root node."""
        return self.get_node(self.root)

    def get_next_nodes(self, current_node: str) -> list[str]:
        """Get the list of possible next nodes from current node."""
        node = self.get_node(current_node)
        if not node:
            return []
        return node.next_allowed_nodes

    def validate_transition(self, from_node: str, to_node: str) -> bool:
        """Validate if transition from one node to another is allowed."""
        node = self.get_node(from_node)
        if not node:
            return False
        return to_node in node.next_allowed_nodes


class WorkflowDefinition(BaseModel):
    """Complete workflow definition from YAML."""

    name: str = Field(description="Workflow name")
    description: str = Field(description="Workflow description")
    inputs: dict[str, WorkflowInput] = Field(
        default_factory=dict, description="Workflow input definitions"
    )
    workflow: WorkflowTree = Field(description="Workflow tree structure")

    @field_validator("workflow")
    @classmethod
    def validate_workflow_root(cls, v: WorkflowTree) -> WorkflowTree:
        """Validate that the root node exists in the tree."""
        if v.root not in v.tree:
            raise ValueError(f"Root node '{v.root}' not found in workflow tree")
        return v

    def get_input_value(self, input_name: str, provided_value: Any = None) -> Any:
        """Get input value, using provided value or default."""
        if input_name not in self.inputs:
            raise ValueError(f"Unknown input: {input_name}")

        input_def = self.inputs[input_name]

        if provided_value is not None:
            return provided_value

        if input_def.default is not None:
            return input_def.default

        if input_def.required:
            raise ValueError(f"Required input '{input_name}' not provided")

        return None

    def validate_inputs(self, provided_inputs: dict[str, Any]) -> dict[str, Any]:
        """Validate and process provided inputs."""
        result = {}

        # Check required inputs
        for input_name, input_def in self.inputs.items():
            if input_def.required and input_name not in provided_inputs:
                raise ValueError(f"Required input '{input_name}' not provided")

        # Process all inputs
        for input_name, _input_def in self.inputs.items():
            result[input_name] = self.get_input_value(
                input_name, provided_inputs.get(input_name)
            )

        return result
