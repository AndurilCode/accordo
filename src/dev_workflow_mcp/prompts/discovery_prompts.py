"""Discovery prompts for workflow selection.

Updated for pure discovery system - no hardcoded scoring, agents make decisions.
"""


from fastmcp import FastMCP


def register_discovery_prompts(mcp: FastMCP) -> None:
    """Register discovery prompt tools for workflow selection."""

    @mcp.tool()
    def workflow_discovery(
        task_description: str,
        workflows_dir: str = ".workflow-commander/workflows",
    ) -> dict:
        """Discover available workflows through agent file access.

        The MCP server cannot access files directly. This tool instructs the agent
        to check the workflows directory and provide workflow information.

        Args:
            task_description: Description of the task to be performed
            workflows_dir: Directory containing workflow YAML files (for agent to check)

        Returns:
            dict: Instructions for agent to discover workflows
        """
        return {
            "status": "agent_action_required",
            "task_description": task_description,
            "instructions": {
                "title": "🔍 **AGENT FILE ACCESS REQUIRED**",
                "message": "The MCP server cannot access files directly. Please perform the following steps:",
                "required_steps": [
                    f"1. **Check directory:** Use `list_dir` tool to examine `{workflows_dir}`",
                    "2. **Read workflow files:** Use `read_file` tool to read each .yaml/.yml file found",
                    "3. **Analyze workflows:** Parse the YAML content to understand available workflows",
                    "4. **Select workflow:** Choose the most appropriate workflow for the task",
                    "5. **Start workflow:** Use `workflow_guidance(action='start', context='workflow: <chosen_name>')` to begin"
                ],
                "expected_workflow_structure": {
                    "name": "Workflow display name", 
                    "description": "Brief description of what this workflow does",
                    "workflow": {
                        "goal": "Main objective of the workflow",
                        "root": "starting_node_name",
                        "tree": "Node definitions with goals and transitions"
                    }
                },
                "selection_criteria": [
                    "**Task complexity:** Simple vs complex multi-step tasks",
                    "**Domain match:** Coding, documentation, debugging, etc.",
                    "**Requirements:** What the task needs vs what workflow provides",
                    "**Goal alignment:** Task objective vs workflow goal"
                ]
            },
            "agent_guidance": {
                "workflow_directory": workflows_dir,
                "file_patterns": ["*.yaml", "*.yml"],
                "discovery_process": "Use file system tools to discover and analyze workflows",
                "selection_method": "Agent decides based on task requirements and workflow capabilities"
            },
            "fallback": {
                "option": "If no workflows found or accessible, use legacy workflow",
                "command": "workflow_guidance(action='start') without context parameter"
            }
        }

    @mcp.tool()
    def list_available_workflows(
        workflows_dir: str = ".workflow-commander/workflows",
    ) -> dict:
        """Instruct agent to list available workflows.

        The MCP server cannot access files directly. This tool provides instructions
        for the agent to discover available workflows.

        Args:
            workflows_dir: Directory containing workflow YAML files (for agent to check)

        Returns:
            dict: Instructions for agent to list workflows
        """
        return {
            "status": "agent_action_required",
            "instructions": {
                "title": "📋 **AGENT WORKFLOW LISTING REQUIRED**",
                "message": "Please use file system tools to list available workflows:",
                "steps": [
                    f"1. **List directory:** `list_dir(relative_workspace_path='{workflows_dir}')`",
                    "2. **Find YAML files:** Look for .yaml or .yml files in the output",
                    "3. **Read each file:** Use `read_file` on each workflow file found",
                    "4. **Extract info:** Parse name, description, goal, and node structure",
                    "5. **Summarize:** Provide a summary of all available workflows"
                ],
                "expected_output": "List of workflows with names, descriptions, and capabilities"
            },
            "directory_to_check": workflows_dir,
            "file_extensions": [".yaml", ".yml"],
            "agent_tools_needed": ["list_dir", "read_file"],
            "purpose": "Discover all available YAML workflow definitions for selection"
        }

    @mcp.tool()
    def validate_workflow_file(workflow_path: str) -> dict:
        """Instruct agent to validate a specific workflow file.

        The MCP server cannot access files directly. This tool provides instructions
        for the agent to validate a workflow file.

        Args:
            workflow_path: Path to the workflow YAML file to validate

        Returns:
            dict: Instructions for agent to validate the workflow
        """
        return {
            "status": "agent_action_required",
            "workflow_path": workflow_path,
            "instructions": {
                "title": "✅ **AGENT WORKFLOW VALIDATION REQUIRED**",
                "message": f"Please validate the workflow file: {workflow_path}",
                "validation_steps": [
                    f"1. **Check file exists:** Use `read_file(target_file='{workflow_path}')`",
                    "2. **Parse YAML:** Verify the file contains valid YAML syntax",
                    "3. **Check structure:** Ensure required fields are present",
                    "4. **Validate nodes:** Verify workflow tree structure is correct",
                    "5. **Check transitions:** Ensure node transitions are valid"
                ],
                "required_fields": [
                    "name - Workflow display name",
                    "description - Brief workflow description", 
                    "workflow.goal - Main workflow objective",
                    "workflow.root - Starting node name",
                    "workflow.tree - Node definitions with goals and next_allowed_nodes"
                ],
                "validation_criteria": [
                    "YAML syntax is valid",
                    "All required fields are present",
                    "Root node exists in tree",
                    "Node transitions reference valid nodes",
                    "No circular dependencies"
                ]
            },
            "agent_tools_needed": ["read_file"],
            "expected_result": "Validation report with any errors found or confirmation of validity"
        }
