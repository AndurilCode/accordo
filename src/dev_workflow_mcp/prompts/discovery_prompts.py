"""Discovery prompts for workflow selection.

Updated for pure discovery system - no hardcoded scoring, agents make decisions.
"""

from pathlib import Path

from fastmcp import FastMCP

from ..utils.yaml_loader import WorkflowLoader, WorkflowLoadError


def register_discovery_prompts(mcp: FastMCP) -> None:
    """Register discovery prompt tools for workflow selection."""

    @mcp.tool()
    def workflow_discovery(
        task_description: str,
        workflows_dir: str = ".workflow-commander/workflows",
    ) -> dict:
        """Discover available workflows for agent selection.

        Pure discovery without scoring - presents workflows for agent choice.

        Args:
            task_description: Description of the task to be performed
            workflows_dir: Directory containing workflow YAML files

        Returns:
            dict: Available workflows for agent selection
        """
        try:
            loader = WorkflowLoader(workflows_dir)

            # Check if workflows directory exists
            workflows_path = Path(workflows_dir)
            if not workflows_path.exists():
                return {
                    "status": "error",
                    "message": f"Workflows directory not found: {workflows_dir}",
                    "task_description": task_description,
                    "available_workflows": [],
                }

            # Load all workflows
            try:
                workflows = loader.discover_workflows()
            except WorkflowLoadError as e:
                return {
                    "status": "error",
                    "message": f"Error loading workflows: {e}",
                    "task_description": task_description,
                    "available_workflows": [],
                }

            if not workflows:
                return {
                    "status": "no_workflows",
                    "message": f"No valid workflows found in {workflows_dir}",
                    "task_description": task_description,
                    "available_workflows": [],
                }

            # Prepare response with all available workflows for agent selection
            workflow_list = []
            for name, workflow_def in workflows.items():
                workflow_info = {
                    "name": workflow_def.name,
                    "description": workflow_def.description,
                    "root_node": workflow_def.workflow.root,
                    "total_nodes": len(workflow_def.workflow.tree),
                    "goal": workflow_def.workflow.goal,
                    "inputs": {
                        input_name: {
                            "type": input_def.type,
                            "description": input_def.description,
                            "required": input_def.required,
                            "default": input_def.default,
                        }
                        for input_name, input_def in (workflow_def.inputs or {}).items()
                    },
                }
                workflow_list.append(workflow_info)

            return {
                "status": "success",
                "task_description": task_description,
                "total_workflows": len(workflows),
                "available_workflows": workflow_list,
                "message": "Agent should select appropriate workflow based on task requirements",
                "selection_guidance": {
                    "instruction": "Choose workflow based on task type and requirements",
                    "method": "Use workflow_guidance tool with context='workflow: <workflow_name>'",
                    "example": "workflow_guidance(action='start', context='workflow: Default Coding Workflow')"
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error during workflow discovery: {e}",
                "task_description": task_description,
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

            # Discover workflows
            try:
                workflows = loader.discover_workflows()
            except WorkflowLoadError as e:
                return {
                    "status": "error",
                    "message": f"Error loading workflows: {e}",
                    "workflows": [],
                }

            if not workflows:
                return {
                    "status": "no_workflows",
                    "message": f"No workflow files found in {workflows_dir}",
                    "workflows": [],
                }

            # Load and list all workflows
            workflows_info = []
            for name, workflow_def in workflows.items():
                try:
                    workflows_info.append(
                        {
                            "name": workflow_def.name,
                            "description": workflow_def.description,
                            "root_node": workflow_def.workflow.root,
                            "total_nodes": len(workflow_def.workflow.tree),
                            "node_names": list(workflow_def.workflow.tree.keys()),
                            "inputs": list((workflow_def.inputs or {}).keys()),
                            "goal": workflow_def.workflow.goal,
                            "valid": True,
                            "error": None,
                        }
                    )
                except Exception as e:
                    workflows_info.append(
                        {
                            "name": name,
                            "description": "Failed to load workflow details",
                            "root_node": None,
                            "total_nodes": 0,
                            "node_names": [],
                            "inputs": [],
                            "goal": None,
                            "valid": False,
                            "error": str(e),
                        }
                    )

            return {
                "status": "success",
                "workflows_directory": workflows_dir,
                "total_workflows": len(workflows),
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
            validation_result = loader.validate_workflow_file(str(file_path))

            if validation_result["valid"]:
                # Load the workflow to get details
                workflow = loader.load_workflow(str(file_path))
                if workflow:
                    return {
                        "status": "success",
                        "valid": True,
                        "workflow": {
                            "name": workflow.name,
                            "description": workflow.description,
                            "root_node": workflow.workflow.root,
                            "total_nodes": len(workflow.workflow.tree),
                            "node_names": list(workflow.workflow.tree.keys()),
                            "goal": workflow.workflow.goal,
                            "inputs": {
                                name: {
                                    "type": input_def.type,
                                    "description": input_def.description,
                                    "required": input_def.required,
                                    "default": input_def.default,
                                }
                                for name, input_def in (workflow.inputs or {}).items()
                            },
                        },
                        "message": "Workflow file is valid",
                    }
                else:
                    return {
                        "status": "error",
                        "valid": False,
                        "message": "Workflow validation passed but failed to load workflow details",
                    }
            else:
                return {
                    "status": "error",
                    "valid": False,
                    "message": f"Workflow validation failed: {validation_result.get('error', 'Unknown error')}",
                    "errors": validation_result.get("errors", []),
                }

        except Exception as e:
            return {
                "status": "error",
                "valid": False,
                "message": f"Exception during validation: {e}",
            }
