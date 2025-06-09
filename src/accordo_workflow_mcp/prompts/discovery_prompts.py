"""Discovery prompts for workflow selection.

Updated for pure discovery system - no hardcoded scoring, agents make decisions.
"""

from fastmcp import FastMCP

from ..utils.session_id_utils import add_session_id_to_response
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
    # Initialize session manager with server config for auto-sync
    if config:
        from ..utils.session_manager import set_server_config

        set_server_config(config)

    @mcp.tool()
    def workflow_discovery(
        task_description: str,
        workflows_dir: str = None,
        client_id: str = "default",
    ) -> dict:
        """Discover available workflows and provide them to the agent for selection.

        The MCP server now performs server-side workflow discovery and provides
        the actual workflow content to the agent for selection.

        🎯 **SESSION_ID WORKFLOW**: When starting workflows, they auto-generate unique session_ids
        that are returned in all responses. Use these session_ids for multi-session support:
        - workflow_guidance(session_id='returned-uuid', ...) to target specific sessions
        - workflow_state(session_id='returned-uuid', ...) to check specific session status

        Args:
            task_description: Description of the task to be performed
            workflows_dir: Directory containing workflow YAML files (optional, uses config if available)
            client_id: Client session identifier

        Returns:
            dict: Available workflows with their content or session conflict information.
                  All responses include session_id when workflows are started.
        """
        # NOTE: Conflict detection has been disabled to fix multi-chat environment issues.
        # Previously, this function would check for existing sessions using client_id,
        # but this created false conflicts in environments like Cursor where multiple
        # chat windows share the same client_id. Each chat now operates independently.

        # REMOVED: Client-based conflict detection that caused false positives
        # in multi-chat environments. Sessions are now truly independent.

        # Determine workflows directory
        if workflows_dir is None and config is not None:
            # Use server configuration
            workflows_dir = str(config.workflows_dir)
        elif workflows_dir is None:
            # Fall back to default
            workflows_dir = ".accordo/workflows"

        # Perform server-side workflow discovery
        try:
            loader = WorkflowLoader(workflows_dir)
            workflows = loader.discover_workflows()

            if not workflows:
                return add_session_id_to_response(
                    {
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
                                "• Ensure .accordo/workflows directory exists",
                            ],
                        },
                        "fallback": {
                            "option": "Create a custom workflow",
                            "command": f"workflow_creation_guidance(task_description='{task_description}')",
                        },
                    },
                    None,
                )

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

            return add_session_id_to_response(
                {
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
                        "session_tracking": {
                            "auto_generation": "🎯 Workflows auto-generate unique session_ids when started",
                            "usage_pattern": "Save the returned session_id and use it in subsequent calls:",
                            "examples": [
                                "workflow_guidance(session_id='returned-uuid', action='next', ...)",
                                "workflow_state(session_id='returned-uuid', operation='get')",
                            ],
                            "multi_session": "🔄 This enables multiple concurrent workflows per client",
                        },
                    },
                    "fallback": {
                        "option": "If none of these workflows fit, create a custom one",
                        "command": f"workflow_creation_guidance(task_description='{task_description}')",
                    },
                },
                None,
            )

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

        🎯 **SESSION_ID INTEGRATION**: When you start the custom workflow with:
        workflow_guidance(action="start", context="workflow: MyWorkflow\\nyaml: <content>")
        The response will include a session_id for tracking. Use this session_id in subsequent calls:
        - workflow_guidance(session_id='abc-123', action='next', ...)
        - workflow_state(session_id='abc-123', operation='get')

        Args:
            task_description: Description of the task requiring a custom workflow
            workflow_type: Type of workflow (coding, documentation, debugging, testing, analysis, etc.)
            complexity_level: Complexity level (simple, medium, complex)
            client_id: Client session identifier

        Returns:
            dict: Comprehensive guidance for creating a YAML workflow that will auto-generate session_ids
        """
        # NOTE: Conflict detection has been disabled to allow independent workflow creation.
        # Each chat/conversation can now create workflows without false conflict detection.
        # REMOVED: Client-based conflict checking that prevented workflow creation in multi-chat environments.

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
            "components": {
                "name": "Workflow name - descriptive but concise",
                "description": "Brief description of workflow purpose and scope",
                "inputs": "Define workflow parameters with types and descriptions",
                "workflow": "Root workflow structure with goal, root node, and tree definition",
            },
        }
