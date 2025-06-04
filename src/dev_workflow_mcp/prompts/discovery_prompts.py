"""Discovery prompts for workflow selection.

Updated for pure discovery system - no hardcoded scoring, agents make decisions.
"""

from fastmcp import FastMCP

from ..utils.session_manager import (
    clear_session_completely,
    detect_session_conflict,
    get_session_summary,
)
from ..utils.yaml_loader import WorkflowLoader

# Global cache for discovered workflows (workflow_name -> workflow_definition)
_discovered_workflows_cache = {}


def get_cached_workflow(workflow_name: str):
    """Retrieve a workflow from the cache by name.

    Args:
        workflow_name: Name of the workflow to retrieve

    Returns:
        WorkflowDefinition or None if not found
    """
    return _discovered_workflows_cache.get(workflow_name)


def cache_workflows(workflows: dict):
    """Cache discovered workflows for later lookup.

    Args:
        workflows: Dictionary of workflow_name -> WorkflowDefinition
    """
    global _discovered_workflows_cache
    _discovered_workflows_cache.update(workflows)


def register_discovery_prompts(mcp: FastMCP, config=None) -> None:
    """Register discovery prompt tools for workflow selection.

    Args:
        mcp: FastMCP application instance
        config: ServerConfig instance with repository path settings (optional)
    """

    @mcp.tool()
    def workflow_discovery(
        task_description: str,
        workflows_dir: str = None,
        client_id: str = "default",
    ) -> dict:
        """Discover available workflows and provide them to the agent for selection.

        The MCP server now performs server-side workflow discovery and provides
        the actual workflow content to the agent for selection.

        Args:
            task_description: Description of the task to be performed
            workflows_dir: Directory containing workflow YAML files (optional, uses config if available)
            client_id: Client session identifier

        Returns:
            dict: Available workflows with their content or session conflict information
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

        # Determine workflows directory
        if workflows_dir is None and config is not None:
            # Use server configuration
            workflows_dir = str(config.workflows_dir)
        elif workflows_dir is None:
            # Fall back to default
            workflows_dir = ".workflow-commander/workflows"

        # Perform server-side workflow discovery
        try:
            loader = WorkflowLoader(workflows_dir)
            workflows = loader.discover_workflows()

            if not workflows:
                return {
                    "status": "no_workflows_found",
                    "task_description": task_description,
                    "workflows_dir": workflows_dir,
                    "message": {
                        "title": "📁 **NO WORKFLOWS FOUND**",
                        "description": f"No workflow YAML files found in: {workflows_dir}",
                        "suggestions": [
                            "• Create workflow YAML files in the workflows directory",
                            "• Use workflow_creation_guidance() to create a custom workflow",
                            "• Check that the repository path is correct",
                            "• Ensure .workflow-commander/workflows directory exists",
                        ],
                    },
                    "fallback": {
                        "option": "Create a custom workflow",
                        "command": f"workflow_creation_guidance(task_description='{task_description}')",
                    },
                }

            # Cache the discovered workflows for later lookup
            cache_workflows(workflows)

            # Format workflows for agent selection (without YAML content)
            workflow_choices = {}
            for name, workflow_def in workflows.items():
                workflow_choices[name] = {
                    "name": workflow_def.name,
                    "description": workflow_def.description,
                    "goal": workflow_def.workflow.goal,
                    "root_node": workflow_def.workflow.root,
                    "total_nodes": len(workflow_def.workflow.tree),
                    "node_names": list(workflow_def.workflow.tree.keys()),
                }

            return {
                "status": "workflows_discovered",
                "task_description": task_description,
                "workflows_dir": workflows_dir,
                "total_workflows": len(workflows),
                "message": {
                    "title": "🔍 **WORKFLOWS DISCOVERED**",
                    "description": f"Found {len(workflows)} workflow(s) in: {workflows_dir}",
                    "instructions": [
                        "1. **Review the available workflows below**",
                        "2. **Choose the most appropriate workflow for your task**",
                        "3. **Start the selected workflow using the provided command**",
                    ],
                },
                "available_workflows": workflow_choices,
                "selection_guidance": {
                    "criteria": [
                        "**Task complexity:** Choose workflows that match your task's complexity",
                        "**Domain match:** Select workflows designed for your type of work (coding, documentation, debugging)",
                        "**Goal alignment:** Pick workflows whose goals align with your objectives",
                        "**Node structure:** Consider the workflow phases that best fit your needs",
                    ],
                    "start_command": "workflow_guidance(action='start', context='workflow: <workflow_name>')",
                    "note": "⚠️ Just provide the workflow name - the server will look up the YAML content automatically",
                },
                "fallback": {
                    "option": "If none of these workflows fit, create a custom one",
                    "command": f"workflow_creation_guidance(task_description='{task_description}')",
                },
            }

        except Exception as e:
            return {
                "status": "discovery_error",
                "task_description": task_description,
                "workflows_dir": workflows_dir,
                "error": str(e),
                "message": {
                    "title": "❌ **WORKFLOW DISCOVERY ERROR**",
                    "description": f"Error discovering workflows: {str(e)}",
                    "suggestions": [
                        "• Check that the workflows directory exists and is accessible",
                        "• Verify YAML files are valid",
                        "• Try using a different repository path if specified",
                        "• Create a custom workflow as alternative",
                    ],
                },
                "fallback": {
                    "option": "Create a custom workflow",
                    "command": f"workflow_creation_guidance(task_description='{task_description}')",
                },
            }

    @mcp.tool()
    def workflow_creation_guidance(
        task_description: str,
        workflow_type: str = "general",
        complexity_level: str = "medium",
        client_id: str = "default",
    ) -> dict:
        """Guide agent through creating a custom YAML workflow for specific task requirements.

        Use this tool when existing workflows don't match the task requirements and a custom
        workflow needs to be created. This tool provides comprehensive guidance on workflow
        structure, format, and best practices.

        Args:
            task_description: Description of the task requiring a custom workflow
            workflow_type: Type of workflow (coding, documentation, debugging, testing, analysis, etc.)
            complexity_level: Complexity level (simple, medium, complex)
            client_id: Client session identifier

        Returns:
            dict: Comprehensive guidance for creating a YAML workflow
        """
        # First, check for existing session conflicts
        conflict_info = detect_session_conflict(client_id)
        if conflict_info:
            session_summary = get_session_summary(client_id)
            return {
                "status": "session_conflict_detected",
                "message": "Active session detected. Resolve conflict before creating new workflow.",
                "conflict_info": conflict_info,
                "session_summary": session_summary,
                "required_action": f"Call resolve_session_conflict(action='cleanup' or 'continue', client_id='{client_id}') first",
            }

        # Provide comprehensive workflow creation guidance
        return {
            "status": "workflow_creation_guidance",
            "task_description": task_description,
            "workflow_type": workflow_type,
            "complexity_level": complexity_level,
            "guidance": {
                "title": "🔧 **DYNAMIC WORKFLOW CREATION GUIDANCE**",
                "message": f"Creating custom workflow for: **{task_description}**",
                "workflow_requirements": {
                    "task_analysis": [
                        "• Break down the task into logical phases or steps",
                        "• Consider where decision points or alternative paths might be useful",
                        "• Think about dependencies between different phases",
                        "• Include validation or quality checks where appropriate",
                    ],
                    "workflow_design_principles": [
                        "• **Clear objectives**: Each node should have a focused purpose",
                        "• **Logical flow**: Organize nodes in a sensible sequence",
                        "• **Appropriate granularity**: Balance detail with practical execution",
                        "• **Quality focus**: Include validation where it adds value",
                        "• **Agent autonomy**: Trust the agent to execute effectively within the framework",
                    ],
                },
                "yaml_structure_specification": {
                    "required_top_level_fields": {
                        "name": "Human-readable workflow name",
                        "description": "Brief description of workflow purpose and scope",
                        "inputs": "Optional: Define input parameters with types and defaults",
                        "execution": "Optional: Configure max_depth, allow_backtracking, etc.",
                        "workflow": "Core workflow definition containing goal, root, and tree",
                    },
                    "workflow_section_structure": {
                        "goal": "Overall objective of the entire workflow",
                        "root": "Name of the starting node (must exist in tree)",
                        "tree": "Dictionary of node definitions with goals and transitions",
                    },
                    "node_structure": {
                        "goal": "Detailed, actionable goal with mandatory execution steps",
                        "acceptance_criteria": "Dictionary of criteria that must be met",
                        "next_allowed_nodes": "List of possible next nodes (or [] for terminal nodes)",
                        "optional_fields": [
                            "next_allowed_workflows: List of workflows that can be transitioned to",
                            "auto_transition: Boolean for automatic progression",
                            "require_approval: Boolean for manual approval gates",
                        ],
                    },
                },
                "goal_formatting_guidelines": {
                    "approach": "Goals should provide clear direction while allowing agent flexibility in execution",
                    "suggested_structure": [
                        "• **Phase purpose**: Brief description of what this phase accomplishes",
                        "• **Key activities**: Main activities or areas of focus (not rigid steps)",
                        "• **Task reference**: You can include `${{ inputs.task_description }}` to reference the user's task",
                        "• **Guidance**: Optional guidance on approach or important considerations",
                    ],
                    "formatting_options": [
                        "• Use markdown formatting for readability",
                        "• Organize information logically (lists, headers, etc.)",
                        "• Include context and rationale where helpful",
                        "• Focus on outcomes rather than rigid procedures",
                    ],
                    "flexibility_note": "The goal should guide the agent toward success while respecting their judgment and expertise",
                },
                "acceptance_criteria_structure": {
                    "purpose": "Define success conditions for the phase (optional but recommended)",
                    "format": "Key-value pairs where keys are descriptive and values define success",
                    "key_naming": "Use clear, descriptive names (snake_case preferred)",
                    "value_format": "Describe what constitutes successful completion",
                    "examples": {
                        "requirements_understood": "Task requirements clearly understood and documented",
                        "solution_implemented": "Working solution that addresses the core requirements",
                        "quality_verified": "Solution tested and meets quality standards",
                    },
                    "note": "Keep criteria focused on outcomes that matter for the specific task",
                },
            },
            "complete_example": {
                "title": "Complete Workflow Example",
                "yaml_content": """name: Custom Task Workflow
description: Dynamically created workflow for specific task requirements

inputs:
  task_description:
    type: string
    description: Task provided by the user
    required: true

execution:
  max_depth: 10
  allow_backtracking: true

workflow:
  goal: Complete the specified task with thorough analysis, planning, and implementation

  root: analyze

  tree:
    analyze:
      goal: |
        **Analysis Phase**

        **Task:** ${{ inputs.task_description }}

        **Objective:** Understand the requirements and context for this task.

        **Key Activities:**
        • Review and understand the task requirements
        • Examine relevant existing systems, code, or documentation  
        • Identify dependencies, constraints, and scope boundaries
        • Clarify any ambiguous aspects of the requirements

        **Approach:** Focus on gaining a complete understanding before moving to planning.
      acceptance_criteria:
        requirements_understood: "Task requirements clearly understood and documented"
        context_assessed: "Relevant systems and dependencies identified"
        scope_defined: "Clear scope boundaries established"
      next_allowed_nodes: [plan]

    plan:
      goal: |
        **Planning Phase**

        **Task:** ${{ inputs.task_description }}

        **Objective:** Create a solid plan for implementing the solution.

        **Key Activities:**
        • Design the overall approach and strategy
        • Break down the work into manageable steps
        • Identify required tools, technologies, or resources
        • Plan for quality assurance and testing

        **Outcome:** A clear, actionable plan ready for execution.
      acceptance_criteria:
        approach_designed: "Clear strategy and methodology defined"
        plan_created: "Detailed implementation plan with logical steps"
        resources_identified: "Required tools and resources identified"
      next_allowed_nodes: [execute]

    execute:
      goal: |
        **Implementation Phase**

        **Task:** ${{ inputs.task_description }}

        **Objective:** Execute the plan and build the solution.

        **Key Activities:**
        • Implement the solution according to the plan
        • Follow quality standards and best practices
        • Test and validate work as you progress
        • Document important decisions and progress

        **Focus:** Deliver a working solution that meets the requirements.
      acceptance_criteria:
        solution_implemented: "Working solution built according to plan"
        quality_maintained: "Solution follows standards and best practices"
        progress_documented: "Key decisions and progress documented"
      next_allowed_nodes: [validate]

    validate:
      goal: |
        **Validation Phase**

        **Task:** ${{ inputs.task_description }}

        **Objective:** Verify the solution meets all requirements and is ready for use.

        **Key Activities:**
        • Test the solution thoroughly against requirements
        • Verify quality standards are met
        • Prepare documentation and deliverables
        • Ensure the solution is complete and ready

        **Outcome:** Verified, documented solution ready for delivery.
      acceptance_criteria:
        requirements_verified: "Solution verified against all requirements"
        quality_confirmed: "Quality standards met and verified"
        deliverables_ready: "Documentation and deliverables prepared"
      next_allowed_nodes: []
""",
            },
            "creation_instructions": {
                "title": "🎯 **WORKFLOW CREATION GUIDANCE**",
                "approach": "Create a workflow that provides structure while respecting agent autonomy",
                "steps": [
                    "1. **Analyze the task** to identify logical phases or steps",
                    "2. **Consider templates** provided as inspiration (adapt freely)",
                    "3. **Design node structure** that makes sense for your specific task",
                    "4. **Write clear goals** that guide without over-constraining",
                    "5. **Add acceptance criteria** to define success (optional but helpful)",
                    "6. **Set up logical transitions** between nodes",
                    "7. **Validate YAML format** for technical correctness",
                    "8. **Start workflow** with the complete YAML content",
                ],
                "design_philosophy": [
                    "• **Agent expertise**: Trust the agent to execute effectively within the framework",
                    "• **Outcome focus**: Emphasize what needs to be achieved, not how",
                    "• **Logical structure**: Organize work in a way that makes sense",
                    "• **Appropriate detail**: Balance guidance with flexibility",
                    "• **Quality awareness**: Include validation where it adds value",
                ],
                "technical_requirements": [
                    "✓ Required YAML fields: name, description, workflow (with goal, root, tree)",
                    "✓ Root node must exist in the tree",
                    "✓ All nodes need goals and next_allowed_nodes ([] for terminal nodes)",
                    "✓ Valid YAML syntax and proper indentation",
                    "✓ Logical workflow structure with clear transitions",
                ],
            },
            "next_action": {
                "message": "After creating your custom workflow YAML, start it with:",
                "command_template": "workflow_guidance(action='start', context='workflow: <workflow_name>\\nyaml: <complete_yaml_content>')",
                "freedom_note": "Feel free to adapt the examples and guidance to fit your specific needs. The goal is a workflow that makes sense for your task.",
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
