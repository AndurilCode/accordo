"""Pure YAML workflow loader without hardcoded logic.

This module loads YAML workflow definitions and presents them to agents for selection.
No hardcoded scoring or matching logic - just pure discovery and loading.
"""

from pathlib import Path

import yaml

from ..models.yaml_workflow import WorkflowDefinition


class WorkflowLoadError(Exception):
    """Exception raised when workflow loading fails."""

    def __init__(self, message: str, file_path: str | None = None):
        """Initialize WorkflowLoadError.

        Args:
            message: Error message
            file_path: Path to the workflow file that failed to load
        """
        super().__init__(message)
        self.file_path = file_path


class WorkflowLoader:
    """Pure workflow loader without hardcoded selection logic."""

    def __init__(self, workflows_dir: str = ".accordo/workflows"):
        """Initialize loader with workflows directory.

        Args:
            workflows_dir: Directory containing YAML workflow files
        """
        self.workflows_dir = Path(workflows_dir)

    def discover_workflows(self) -> dict[str, WorkflowDefinition]:
        """Discover all available workflow files.

        Returns:
            Dictionary mapping workflow names to WorkflowDefinition objects
        """
        workflows = {}

        if not self.workflows_dir.exists():
            return workflows

        # Scan for YAML files
        for yaml_file in self.workflows_dir.glob("*.yaml"):
            try:
                workflow = self.load_workflow(str(yaml_file))
                if workflow:
                    workflows[workflow.name] = workflow
            except Exception:
                # Skip invalid workflow files silently
                continue

        return workflows

    def load_workflow(self, file_path: str) -> WorkflowDefinition | None:
        """Load a single workflow from YAML file.

        Args:
            file_path: Path to YAML workflow file

        Returns:
            WorkflowDefinition object or None if loading fails
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            # Validate and create workflow definition
            workflow = WorkflowDefinition(**yaml_data)
            return workflow

        except Exception:
            return None

    def load_workflow_from_string(
        self, yaml_content: str, workflow_name: str = None
    ) -> WorkflowDefinition | None:
        """Load a workflow from YAML string content.

        Args:
            yaml_content: YAML content as string
            workflow_name: Optional name override for the workflow

        Returns:
            WorkflowDefinition object or None if loading fails
        """
        try:
            yaml_data = yaml.safe_load(yaml_content)

            # Override name if provided
            if workflow_name:
                yaml_data["name"] = workflow_name

            # Validate and create workflow definition
            workflow = WorkflowDefinition(**yaml_data)
            return workflow

        except Exception:
            return None

    def load_all_workflows(self) -> dict[str, WorkflowDefinition]:
        """Load all workflows from the workflows directory.

        Returns:
            Dictionary mapping workflow names to WorkflowDefinition objects
        """
        return self.discover_workflows()

    def list_workflow_names(self) -> list[str]:
        """Get list of available workflow names.

        Returns:
            List of workflow names
        """
        workflows = self.discover_workflows()
        return list(workflows.keys())

    def get_workflow_by_name(self, name: str) -> WorkflowDefinition | None:
        """Get workflow by exact name match.

        Args:
            name: Exact workflow name

        Returns:
            WorkflowDefinition or None if not found
        """
        workflows = self.discover_workflows()
        return workflows.get(name)

    def validate_workflow_file(self, file_path: str) -> dict[str, any]:
        """Validate a workflow YAML file.

        Args:
            file_path: Path to YAML file to validate

        Returns:
            Validation result with success status and any errors
        """
        try:
            # First try to load and parse the YAML
            with open(file_path, encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            # First do basic field validation before Pydantic validation
            errors = []

            # Check for empty or missing required fields
            if not yaml_data.get("name") or yaml_data.get("name") == "":
                errors.append("Workflow name is required")
            if not yaml_data.get("description") or yaml_data.get("description") == "":
                errors.append("Workflow description is required")

            workflow_data = yaml_data.get("workflow", {})
            if not workflow_data:
                errors.append("Workflow structure is required")
            else:
                if not workflow_data.get("root"):
                    errors.append("Workflow must have a root node defined")
                if not workflow_data.get("tree"):
                    errors.append("Workflow must have tree nodes defined")
                elif len(workflow_data.get("tree", {})) == 0:
                    errors.append("Workflow tree cannot be empty")
                else:
                    # Check if root exists in tree
                    root = workflow_data.get("root")
                    tree = workflow_data.get("tree", {})
                    if root and root not in tree:
                        errors.append(f"Root node '{root}' not found in workflow tree")

                    # Check node references
                    for node_name, node in tree.items():
                        next_nodes = (
                            node.get("next_allowed_nodes", [])
                            if isinstance(node, dict)
                            else []
                        )
                        for next_node in next_nodes:
                            if next_node not in tree:
                                errors.append(
                                    f"Node '{node_name}' references non-existent node '{next_node}'"
                                )

            # If we found validation errors, return them without trying Pydantic validation
            if errors:
                return {
                    "valid": False,
                    "errors": errors,
                    "error": errors[0],
                }

            # Try to create workflow definition to catch any remaining Pydantic validation errors
            try:
                workflow = WorkflowDefinition(**yaml_data)
            except Exception as pydantic_error:
                # Parse Pydantic validation errors for more specific messages
                error_msg = str(pydantic_error)
                errors = []

                if "references non-existent node" in error_msg:
                    errors.append(error_msg)
                if "Root node" in error_msg and "not found" in error_msg:
                    errors.append(error_msg)

                # If no specific errors found, use generic message
                if not errors:
                    errors = [
                        f"Failed to load workflow - invalid YAML or schema: {error_msg}"
                    ]

                return {
                    "valid": False,
                    "errors": errors,
                    "error": errors[0]
                    if errors
                    else f"Failed to load workflow - invalid YAML or schema: {error_msg}",
                }

            # Basic validation checks for loaded workflow
            errors = []

            # Check required fields
            if not workflow.name:
                errors.append("Workflow name is required")

            if not workflow.description:
                errors.append("Workflow description is required")

            if not workflow.workflow or not workflow.workflow.root:
                errors.append("Workflow must have a root node defined")

            if not workflow.workflow or not workflow.workflow.tree:
                errors.append("Workflow must have tree nodes defined")

            # Check that root node exists in tree
            if (
                workflow.workflow
                and workflow.workflow.root
                and workflow.workflow.root not in workflow.workflow.tree
            ):
                errors.append(
                    f"Root node '{workflow.workflow.root}' not found in workflow tree"
                )

            # Check node references
            if workflow.workflow and workflow.workflow.tree:
                for node_name, node in workflow.workflow.tree.items():
                    # Validate next_allowed_nodes references
                    if node.next_allowed_nodes:
                        for next_node in node.next_allowed_nodes:
                            if next_node not in workflow.workflow.tree:
                                errors.append(
                                    f"Node '{node_name}' references non-existent node '{next_node}'"
                                )

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "workflow_name": workflow.name if workflow else None,
                "node_count": len(workflow.workflow.tree)
                if workflow and workflow.workflow
                else 0,
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Exception during validation: {str(e)}"],
                "error": f"Exception during validation: {str(e)}",
            }


# Convenience functions for common operations


def load_workflow_by_name(
    name: str, workflows_dir: str = ".accordo/workflows"
) -> WorkflowDefinition | None:
    """Load workflow by name using default loader.

    Args:
        name: Workflow name to load
        workflows_dir: Directory containing workflows

    Returns:
        WorkflowDefinition or None if not found
    """
    loader = WorkflowLoader(workflows_dir)
    return loader.get_workflow_by_name(name)


def get_available_workflows(
    workflows_dir: str = ".accordo/workflows",
) -> list[str]:
    """Get list of available workflow names.

    Args:
        workflows_dir: Directory containing workflows

    Returns:
        List of workflow names
    """
    loader = WorkflowLoader(workflows_dir)
    return loader.list_workflow_names()


def validate_workflow(file_path: str) -> dict[str, any]:
    """Validate a workflow file.

    Args:
        file_path: Path to workflow YAML file

    Returns:
        Validation result dictionary
    """
    loader = WorkflowLoader()
    return loader.validate_workflow_file(file_path)
