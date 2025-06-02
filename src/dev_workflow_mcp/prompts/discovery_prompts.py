"""Workflow discovery prompts for finding and selecting appropriate workflows."""

from pathlib import Path

from fastmcp import FastMCP

from ..utils.yaml_loader import WorkflowLoader, WorkflowLoadError


def register_discovery_prompts(mcp: FastMCP) -> None:
    """Register workflow discovery prompts with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """

    @mcp.tool()
    def workflow_discovery(
        task_description: str,
        workflows_dir: str = ".workflow-commander/workflows",
        max_suggestions: int = 3,
        min_score: float = 0.1,
    ) -> dict:
        """Discover and select the best workflow for a given task description.

        Args:
            task_description: Description of the task to find a workflow for
            workflows_dir: Directory containing workflow YAML files
            max_suggestions: Maximum number of workflow suggestions to return
            min_score: Minimum score threshold for workflow suggestions

        Returns:
            dict: Contains the best workflow selection and alternative suggestions
        """
        try:
            loader = WorkflowLoader(workflows_dir)

            # Check if workflows directory exists
            workflows_path = Path(workflows_dir)
            if not workflows_path.exists():
                return {
                    "status": "error",
                    "message": f"Workflows directory not found: {workflows_dir}",
                    "best_workflow": None,
                    "suggestions": [],
                    "available_workflows": [],
                }

            # Discover available workflows
            workflow_files = loader.discover_workflows()
            if not workflow_files:
                return {
                    "status": "no_workflows",
                    "message": f"No workflow files found in {workflows_dir}",
                    "best_workflow": None,
                    "suggestions": [],
                    "available_workflows": [],
                }

            # Load all workflows
            try:
                workflows = loader.load_all_workflows()
            except WorkflowLoadError as e:
                return {
                    "status": "error",
                    "message": f"Error loading workflows: {e}",
                    "best_workflow": None,
                    "suggestions": [],
                    "available_workflows": [str(f) for f in workflow_files],
                }

            # Get workflow suggestions
            suggestions = loader.get_workflow_suggestions(
                task_description, max_suggestions
            )

            # Find best workflow
            best_workflow = loader.find_best_workflow(task_description, min_score)

            # Prepare response
            result = {
                "status": "success",
                "task_description": task_description,
                "available_workflows": list(workflows.keys()),
                "suggestions": [
                    {
                        "workflow_name": suggestion.workflow_name,
                        "score": suggestion.score,
                        "reasons": suggestion.reasons,
                    }
                    for suggestion in suggestions
                ],
                "best_workflow": None,
            }

            if best_workflow:
                result["best_workflow"] = {
                    "name": best_workflow.name,
                    "description": best_workflow.description,
                    "root_node": best_workflow.workflow.root,
                    "total_nodes": len(best_workflow.workflow.tree),
                    "inputs": {
                        name: {
                            "type": input_def.type,
                            "description": input_def.description,
                            "required": input_def.required,
                            "default": input_def.default,
                        }
                        for name, input_def in best_workflow.inputs.items()
                    },
                }
            else:
                result["message"] = f"No workflows found with score >= {min_score}"

            return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error during workflow discovery: {e}",
                "best_workflow": None,
                "suggestions": [],
                "available_workflows": [],
            }

    @mcp.tool()
    def list_available_workflows(
        workflows_dir: str = ".workflow-commander/workflows",
    ) -> dict:
        """List all available workflows in the workflows directory.

        Args:
            workflows_dir: Directory containing workflow YAML files

        Returns:
            dict: Information about all available workflows
        """
        try:
            loader = WorkflowLoader(workflows_dir)

            # Check if workflows directory exists
            workflows_path = Path(workflows_dir)
            if not workflows_path.exists():
                return {
                    "status": "error",
                    "message": f"Workflows directory not found: {workflows_dir}",
                    "workflows": [],
                }

            # Discover workflow files
            workflow_files = loader.discover_workflows()
            if not workflow_files:
                return {
                    "status": "no_workflows",
                    "message": f"No workflow files found in {workflows_dir}",
                    "workflows": [],
                }

            # Load and list all workflows
            workflows_info = []
            for workflow_path in workflow_files:
                try:
                    workflow = loader.load_workflow(workflow_path)
                    workflows_info.append(
                        {
                            "file": str(workflow_path),
                            "name": workflow.name,
                            "description": workflow.description,
                            "root_node": workflow.workflow.root,
                            "total_nodes": len(workflow.workflow.tree),
                            "node_names": list(workflow.workflow.tree.keys()),
                            "inputs": list(workflow.inputs.keys()),
                            "valid": True,
                            "error": None,
                        }
                    )
                except WorkflowLoadError as e:
                    workflows_info.append(
                        {
                            "file": str(workflow_path),
                            "name": None,
                            "description": None,
                            "root_node": None,
                            "total_nodes": 0,
                            "node_names": [],
                            "inputs": [],
                            "valid": False,
                            "error": str(e),
                        }
                    )

            return {
                "status": "success",
                "workflows_directory": workflows_dir,
                "total_files": len(workflow_files),
                "valid_workflows": len([w for w in workflows_info if w["valid"]]),
                "invalid_workflows": len([w for w in workflows_info if not w["valid"]]),
                "workflows": workflows_info,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error listing workflows: {e}",
                "workflows": [],
            }

    @mcp.tool()
    def validate_workflow_file(workflow_path: str) -> dict:
        """Validate a specific workflow file.

        Args:
            workflow_path: Path to the workflow YAML file to validate

        Returns:
            dict: Validation result with details about the workflow
        """
        try:
            file_path = Path(workflow_path)

            if not file_path.exists():
                return {
                    "status": "error",
                    "message": f"Workflow file not found: {workflow_path}",
                    "valid": False,
                }

            loader = WorkflowLoader()
            is_valid, error_message = loader.validate_workflow_file(file_path)

            if is_valid:
                # Load the workflow to get details
                workflow = loader.load_workflow(file_path)
                return {
                    "status": "success",
                    "valid": True,
                    "workflow": {
                        "name": workflow.name,
                        "description": workflow.description,
                        "root_node": workflow.workflow.root,
                        "total_nodes": len(workflow.workflow.tree),
                        "node_names": list(workflow.workflow.tree.keys()),
                        "inputs": {
                            name: {
                                "type": input_def.type,
                                "description": input_def.description,
                                "required": input_def.required,
                                "default": input_def.default,
                            }
                            for name, input_def in workflow.inputs.items()
                        },
                    },
                    "message": "Workflow file is valid",
                }
            else:
                return {
                    "status": "validation_error",
                    "valid": False,
                    "message": error_message,
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error validating workflow: {e}",
                "valid": False,
            }
