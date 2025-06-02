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

    def __init__(self, workflows_dir: str = ".workflow-commander/workflows"):
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
            workflow = self.load_workflow(file_path)

            if workflow is None:
                return {
                    "valid": False,
                    "error": "Failed to load workflow - invalid YAML or schema",
                }

            # Basic validation checks
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
            if workflow.workflow and workflow.workflow.root:
                if workflow.workflow.root not in workflow.workflow.tree:
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
            return {"valid": False, "error": f"Exception during validation: {str(e)}"}


# Convenience functions for common operations


def load_workflow_by_name(
    name: str, workflows_dir: str = ".workflow-commander/workflows"
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
    workflows_dir: str = ".workflow-commander/workflows",
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
