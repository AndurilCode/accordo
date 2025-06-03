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
                        "1. **Break down the task** into distinct phases or steps",
                        "2. **Identify decision points** where different paths might be needed",
                        "3. **Determine dependencies** between different phases",
                        "4. **Consider validation points** and quality gates",
                        "5. **Plan for error handling** and alternative paths",
                    ],
                    "workflow_design_principles": [
                        "• **Atomic phases**: Each node should represent a single, clear objective",
                        "• **Clear transitions**: Define specific conditions for moving between nodes",
                        "• **Validation focus**: Include acceptance criteria for each phase",
                        "• **Flexibility**: Allow for backtracking and alternative paths when needed",
                        "• **Progress tracking**: Enable detailed progress monitoring",
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
                "goal_formatting_requirements": {
                    "structure": [
                        "1. **Start with phase title**: `**MANDATORY [PHASE_NAME] PHASE - FOLLOW EXACTLY:**`",
                        "2. **Include task reference**: `**TASK:** ${{ inputs.task_description }}`",
                        "3. **Add execution steps**: `**🔨 REQUIRED EXECUTION STEPS - NO EXCEPTIONS:**`",
                        "4. **List numbered steps**: Each step with ⚠️ MANDATORY markers",
                        "5. **Include guidance**: DO NOT and FOCUS sections for clarity",
                    ],
                    "step_formatting": [
                        "• Use **bold headers** for each main step",
                        "• Include ⚠️ MANDATORY markers for critical steps",
                        "• Provide specific, actionable instructions",
                        "• Include verification or validation requirements",
                        "• Add context about why each step is important",
                    ],
                    "mandatory_elements": [
                        "🔨 REQUIRED EXECUTION STEPS marker",
                        "⚠️ MANDATORY markers for critical steps",
                        "Clear DO NOT and FOCUS guidance",
                        "Specific, actionable instructions",
                        "Progress tracking requirements where applicable",
                    ],
                },
                "acceptance_criteria_structure": {
                    "format": "Each criterion should be a key-value pair",
                    "key_naming": "Use descriptive, snake_case keys",
                    "value_format": "Clear, measurable success conditions",
                    "examples": {
                        "task_analysis": "Complete breakdown of task into actionable requirements with scope boundaries defined",
                        "implementation_quality": "Code follows project standards with comprehensive error handling and validation",
                        "documentation_completeness": "All changes documented with examples and integration instructions provided",
                    },
                },
            },
            "workflow_templates": {
                "simple_linear": {
                    "description": "Simple sequential workflow with 2-3 phases",
                    "use_case": "Straightforward tasks with clear sequential steps",
                    "example_nodes": ["analyze", "implement", "validate"],
                },
                "analysis_planning_construction": {
                    "description": "Standard development workflow pattern",
                    "use_case": "Most coding and development tasks",
                    "example_nodes": ["analyze", "blueprint", "construct", "validate"],
                },
                "investigation_resolution": {
                    "description": "Problem-solving and debugging workflow",
                    "use_case": "Debugging, troubleshooting, research tasks",
                    "example_nodes": ["investigate", "analyze_root_cause", "develop_solution", "test_solution"],
                },
                "iterative_refinement": {
                    "description": "Workflow with revision and improvement cycles",
                    "use_case": "Creative tasks, documentation, complex problem solving",
                    "example_nodes": ["initial_draft", "review_feedback", "refine", "finalize"],
                },
                "branching_decision": {
                    "description": "Workflow with decision points and alternative paths",
                    "use_case": "Tasks requiring different approaches based on conditions",
                    "example_nodes": ["assess", "choose_approach", "path_a", "path_b", "converge"],
                },
            },
            "complete_example": {
                "title": "Complete Workflow Example",
                "yaml_content": '''name: Custom Task Workflow
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
        **MANDATORY ANALYZE PHASE - FOLLOW EXACTLY:**

        **TASK:** ${{ inputs.task_description }}

        **🔨 REQUIRED EXECUTION STEPS - NO EXCEPTIONS:**

        **1. UNDERSTAND REQUIREMENTS** ⚠️ MANDATORY
           - MUST read and comprehend the complete task description
           - MUST identify all explicit and implicit requirements
           - MUST note any constraints or limitations
           - MUST clarify any ambiguous aspects

        **2. GATHER CONTEXT** ⚠️ MANDATORY
           - MUST examine relevant existing systems, code, or documentation
           - MUST understand the current state and environment
           - MUST identify dependencies and integration points
           - MUST assess available resources and tools

        **3. DEFINE SCOPE** ⚠️ MANDATORY
           - MUST clearly define what is included and excluded from the task
           - MUST identify potential risks and challenges
           - MUST estimate complexity and effort required
           - MUST document any assumptions being made

        **DO NOT:** Start implementation or make changes during analysis.
        **FOCUS:** Complete understanding and documentation of requirements.
      acceptance_criteria:
        requirement_analysis: "Complete understanding of task requirements with all ambiguities resolved"
        context_gathering: "Thorough examination of existing systems and relevant documentation"
        scope_definition: "Clear scope boundaries defined with risks and assumptions documented"
      next_allowed_nodes: [plan]

    plan:
      goal: |
        **MANDATORY PLAN PHASE - FOLLOW EXACTLY:**

        **TASK:** ${{ inputs.task_description }}

        **🔨 REQUIRED EXECUTION STEPS - NO EXCEPTIONS:**

        **1. DESIGN APPROACH** ⚠️ MANDATORY
           - MUST define the overall strategy and methodology
           - MUST break down the work into manageable steps
           - MUST identify required tools, technologies, or resources
           - MUST plan for quality assurance and validation

        **2. CREATE IMPLEMENTATION PLAN** ⚠️ MANDATORY
           - MUST outline specific steps in logical sequence
           - MUST define success criteria for each step
           - MUST identify potential obstacles and mitigation strategies
           - MUST plan for testing and validation throughout

        **3. VALIDATE PLAN** ⚠️ MANDATORY
           - MUST review plan for completeness and feasibility
           - MUST ensure plan addresses all identified requirements
           - MUST verify resource availability and timeline reasonableness
           - MUST confirm plan aligns with overall objectives

        **PLANNING DEPTH:** Plan must be detailed enough for systematic execution.
      acceptance_criteria:
        approach_design: "Comprehensive strategy defined with methodology and resource requirements"
        implementation_plan: "Detailed step-by-step plan with success criteria and risk mitigation"
        plan_validation: "Plan reviewed and confirmed to address all requirements effectively"
      next_allowed_nodes: [execute]

    execute:
      goal: |
        **MANDATORY EXECUTE PHASE - FOLLOW EXACTLY:**

        **TASK:** ${{ inputs.task_description }}

        **🔨 REQUIRED EXECUTION STEPS - NO EXCEPTIONS:**

        **1. IMPLEMENT PLAN SYSTEMATICALLY** ⚠️ MANDATORY
           - MUST follow the planned sequence of steps exactly
           - MUST complete each step fully before proceeding
           - MUST validate completion of each step against success criteria
           - MUST document progress and any deviations from plan

        **2. MAINTAIN QUALITY STANDARDS** ⚠️ MANDATORY
           - MUST ensure all work meets defined quality criteria
           - MUST perform validation and testing as planned
           - MUST address any issues or defects immediately
           - MUST follow best practices and established standards

        **3. TRACK PROGRESS** ⚠️ MANDATORY
           - MUST update workflow_state after each major step completion
           - MUST log significant decisions and their rationale
           - MUST document any challenges encountered and solutions applied
           - MUST maintain clear record of what has been accomplished

        **EXECUTION DISCIPLINE:** Strict adherence to plan with systematic progress tracking.
      acceptance_criteria:
        plan_execution: "All planned steps executed systematically with full completion verification"
        quality_maintenance: "All work meets defined quality standards with validation completed"
        progress_tracking: "Complete progress log maintained with all major steps documented"
      next_allowed_nodes: [validate]

    validate:
      goal: |
        **MANDATORY VALIDATE PHASE - FOLLOW EXACTLY:**

        **TASK:** ${{ inputs.task_description }}

        **🔨 REQUIRED EXECUTION STEPS - NO EXCEPTIONS:**

        **1. VERIFY REQUIREMENTS FULFILLMENT** ⚠️ MANDATORY
           - MUST confirm all original requirements have been met
           - MUST test functionality against acceptance criteria
           - MUST verify no requirements have been missed or inadequately addressed
           - MUST document evidence of requirement satisfaction

        **2. CONDUCT QUALITY VERIFICATION** ⚠️ MANDATORY
           - MUST perform comprehensive testing of all deliverables
           - MUST verify adherence to quality standards and best practices
           - MUST check for any defects, errors, or omissions
           - MUST ensure robustness and reliability of solution

        **3. PREPARE FINAL DELIVERABLES** ⚠️ MANDATORY
           - MUST organize all outputs in clear, accessible format
           - MUST provide documentation and usage instructions
           - MUST include any necessary maintenance or support information
           - MUST ensure deliverables are ready for handover or deployment

        **VALIDATION THOROUGHNESS:** Comprehensive verification with complete documentation.
      acceptance_criteria:
        requirement_verification: "All requirements verified as fulfilled with documented evidence"
        quality_verification: "Comprehensive quality checks completed with all standards met"
        deliverable_preparation: "Final deliverables organized and documented for handover"
      next_allowed_nodes: []
''',
            },
            "creation_instructions": {
                "title": "🎯 **WORKFLOW CREATION INSTRUCTIONS**",
                "steps": [
                    "1. **Analyze your specific task** to identify the unique phases needed",
                    "2. **Choose appropriate template** from the provided examples as starting point",
                    "3. **Customize node structure** to match your task's specific requirements",
                    "4. **Write detailed goals** following the formatting requirements with mandatory steps",
                    "5. **Define acceptance criteria** with specific, measurable success conditions",
                    "6. **Set up transitions** between nodes using next_allowed_nodes",
                    "7. **Validate YAML syntax** and structure completeness",
                    "8. **Start workflow** using: `workflow_guidance(action='start', context='workflow: <name>\\nyaml: <yaml_content>')`",
                ],
                "key_considerations": [
                    "• **Task-specific adaptation**: Modify templates to fit your exact needs",
                    "• **Clear phase separation**: Each node should have a distinct, focused purpose",
                    "• **Actionable instructions**: Goals should provide specific, executable steps",
                    "• **Quality gates**: Include validation and verification at appropriate points",
                    "• **Progress tracking**: Plan for monitoring and logging throughout execution",
                ],
                "validation_checklist": [
                    "✓ All required YAML fields present (name, description, workflow)",
                    "✓ Root node specified and exists in tree",
                    "✓ All nodes have goals and acceptance_criteria",
                    "✓ next_allowed_nodes reference valid nodes (or [] for terminal)",
                    "✓ Goals follow formatting requirements with mandatory steps",
                    "✓ Acceptance criteria are specific and measurable",
                    "✓ Workflow covers all aspects of the task",
                    "✓ YAML syntax is valid and properly formatted",
                ],
            },
            "next_action": {
                "message": "After creating your custom workflow YAML, start it with:",
                "command_template": "workflow_guidance(action='start', context='workflow: <workflow_name>\\nyaml: <complete_yaml_content>')",
                "reminder": "Ensure the YAML content is complete and properly formatted before starting the workflow.",
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
