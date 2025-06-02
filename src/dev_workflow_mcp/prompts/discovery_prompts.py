"""Discovery prompts for workflow selection.

Updated for pure discovery system - no hardcoded scoring, agents make decisions.
"""

from fastmcp import FastMCP

from ..utils.session_manager import (
    clear_session_completely,
    detect_session_conflict,
    get_session_summary,
)


def register_discovery_prompts(mcp: FastMCP) -> None:
    """Register discovery prompt tools for workflow selection."""

    @mcp.tool()
    def workflow_discovery(
        task_description: str,
        workflows_dir: str = ".workflow-commander/workflows",
        client_id: str = "default",
    ) -> dict:
        """Discover available workflows through agent file access.

        The MCP server cannot access files directly. This tool instructs the agent
        to check the workflows directory and provide workflow information.

        Args:
            task_description: Description of the task to be performed
            workflows_dir: Directory containing workflow YAML files (for agent to check)
            client_id: Client session identifier

        Returns:
            dict: Instructions for agent to discover workflows or session conflict information
        """
        # First, check for existing session conflicts
        conflict_info = detect_session_conflict(client_id)
        if conflict_info:
            # Session conflict detected - prompt user for resolution
            session_summary = get_session_summary(client_id)
            return {
                "status": "session_conflict_detected",
                "conflict_info": conflict_info,
                "session_summary": session_summary,
                "message": {
                    "title": "⚠️ **EXISTING WORKFLOW SESSION DETECTED**",
                    "description": "There is already an active workflow session for this client.",
                    "current_session": session_summary,
                    "conflict_details": {
                        "workflow_type": conflict_info["session_type"],
                        "workflow_name": conflict_info["workflow_name"],
                        "current_phase_or_node": conflict_info["phase_or_node"],
                        "status": conflict_info["status"],
                        "current_task": conflict_info["current_item"],
                        "last_updated": conflict_info["last_updated"],
                    },
                },
                "user_choice_required": {
                    "title": "🤔 **WHAT WOULD YOU LIKE TO DO?**",
                    "options": [
                        {
                            "choice": "cleanup",
                            "description": "Clear the existing session and start fresh",
                            "action": f"resolve_session_conflict(action='cleanup', client_id='{client_id}')",
                            "consequences": [
                                "• All current session data will be lost",
                                "• You can start a new workflow from scratch",
                                "• Previous progress will not be recoverable",
                            ],
                        },
                        {
                            "choice": "continue",
                            "description": "Continue with the existing workflow session",
                            "action": f"resolve_session_conflict(action='continue', client_id='{client_id}')",
                            "consequences": [
                                "• Keep all current session data",
                                "• Resume from where you left off",
                                "• No new workflow discovery needed",
                            ],
                        },
                    ],
                    "instructions": [
                        "1. **Review the current session details above**",
                        "2. **Choose one of the options below:**",
                        "   - Use `resolve_session_conflict(action='cleanup')` to clear and start fresh",
                        "   - Use `resolve_session_conflict(action='continue')` to resume existing workflow",
                        "3. **After resolving the conflict, you can proceed with your intended action**",
                    ],
                },
                "task_description": task_description,
                "workflows_dir": workflows_dir,
            }

        # No conflict - proceed with normal workflow discovery
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
                    "5. **Start workflow:** Use `workflow_guidance(action='start', context='workflow: <name>\\nyaml: <full_yaml_content>')` with the selected workflow's YAML content",
                ],
                "expected_workflow_structure": {
                    "name": "Workflow display name",
                    "description": "Brief description of what this workflow does",
                    "workflow": {
                        "goal": "Main objective of the workflow",
                        "root": "starting_node_name",
                        "tree": "Node definitions with goals and transitions",
                    },
                },
                "selection_criteria": [
                    "**Task complexity:** Simple vs complex multi-step tasks",
                    "**Domain match:** Coding, documentation, debugging, etc.",
                    "**Requirements:** What the task needs vs what workflow provides",
                    "**Goal alignment:** Task objective vs workflow goal",
                ],
            },
            "agent_guidance": {
                "workflow_directory": workflows_dir,
                "file_patterns": ["*.yaml", "*.yml"],
                "discovery_process": "Use file system tools to discover and analyze workflows",
                "selection_method": "Agent decides based on task requirements and workflow capabilities",
            },
            "fallback": {
                "option": "If no workflows found or accessible, use legacy workflow",
                "command": "workflow_guidance(action='start') without context parameter",
            },
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
                    "5. **Summarize:** Provide a summary of all available workflows",
                ],
                "expected_output": "List of workflows with names, descriptions, and capabilities",
            },
            "directory_to_check": workflows_dir,
            "file_extensions": [".yaml", ".yml"],
            "agent_tools_needed": ["list_dir", "read_file"],
            "purpose": "Discover all available YAML workflow definitions for selection",
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
                    "5. **Check transitions:** Ensure node transitions are valid",
                ],
                "required_fields": [
                    "name - Workflow display name",
                    "description - Brief workflow description",
                    "workflow.goal - Main workflow objective",
                    "workflow.root - Starting node name",
                    "workflow.tree - Node definitions with goals and next_allowed_nodes",
                ],
                "validation_criteria": [
                    "YAML syntax is valid",
                    "All required fields are present",
                    "Root node exists in tree",
                    "Node transitions reference valid nodes",
                    "No circular dependencies",
                ],
            },
            "agent_tools_needed": ["read_file"],
            "expected_result": "Validation report with any errors found or confirmation of validity",
        }

    @mcp.tool()
    def resolve_session_conflict(
        action: str,
        client_id: str = "default",
    ) -> dict:
        """Resolve a session conflict by either cleaning up the existing session or continuing with it.

        Args:
            action: Action to take - either "cleanup" to clear the session or "continue" to keep it
            client_id: Client session identifier

        Returns:
            dict: Result of the conflict resolution action
        """
        # Validate action parameter
        if action not in ["cleanup", "continue"]:
            return {
                "status": "error",
                "error": "Invalid action. Must be 'cleanup' or 'continue'",
                "valid_actions": ["cleanup", "continue"],
            }

        # Check if there's actually a conflict to resolve
        conflict_info = detect_session_conflict(client_id)
        if not conflict_info:
            return {
                "status": "no_conflict",
                "message": "No session conflict detected. You can proceed with workflow discovery.",
                "next_action": "Call workflow_discovery to start a new workflow",
            }

        if action == "cleanup":
            # Clear the session completely
            cleanup_results = clear_session_completely(client_id)

            if cleanup_results["success"]:
                return {
                    "status": "cleanup_successful",
                    "message": "Session cleared successfully. You can now start a new workflow.",
                    "cleanup_details": {
                        "previous_session_type": cleanup_results[
                            "previous_session_type"
                        ],
                        "session_cleared": cleanup_results["session_cleared"],
                        "cache_cleared": cleanup_results["cache_cleared"],
                    },
                    "next_actions": [
                        "1. Call workflow_discovery to find available workflows",
                        "2. Start a new workflow with workflow_guidance",
                    ],
                }
            else:
                return {
                    "status": "cleanup_failed",
                    "error": f"Failed to clear session: {cleanup_results.get('error', 'Unknown error')}",
                    "cleanup_details": cleanup_results,
                    "recommendation": "Try manual session cleanup or contact support",
                }

        elif action == "continue":
            # Continue with existing session
            session_summary = get_session_summary(client_id)
            return {
                "status": "continue_existing",
                "message": "Continuing with existing workflow session.",
                "session_info": conflict_info,
                "session_summary": session_summary,
                "next_actions": [
                    "1. Use workflow_guidance to continue the current workflow",
                    "2. Check workflow_state to see current progress",
                    "3. Use appropriate workflow actions based on current phase/node",
                ],
                "current_state": {
                    "workflow": conflict_info["workflow_name"],
                    "type": conflict_info["session_type"],
                    "current": conflict_info["phase_or_node"],
                    "status": conflict_info["status"],
                    "task": conflict_info["current_item"],
                },
            }

        # This should never be reached due to validation above
        return {
            "status": "error",
            "error": "Unexpected error in conflict resolution",
        }
