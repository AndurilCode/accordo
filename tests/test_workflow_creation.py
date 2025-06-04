"""Tests for workflow creation guidance functionality."""

import pytest
from fastmcp import FastMCP

from src.dev_workflow_mcp.prompts.discovery_prompts import register_discovery_prompts


class TestWorkflowCreationGuidance:
    """Test workflow creation guidance tool."""

    @pytest.mark.asyncio
    async def test_workflow_creation_guidance_basic_functionality(self):
        """Test basic functionality of workflow_creation_guidance tool."""
        # Create FastMCP app and register discovery tools
        app = FastMCP("test-creation-guidance")
        register_discovery_prompts(app)

        # Get the tools
        tools = await app.get_tools()
        assert "workflow_creation_guidance" in tools

        creation_tool = tools["workflow_creation_guidance"]

        # Test with basic parameters
        result = creation_tool.fn(
            task_description="Create a custom workflow for API testing",
            workflow_type="testing",
            complexity_level="medium",
        )

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["status"] == "workflow_creation_guidance"
        assert result["task_description"] == "Create a custom workflow for API testing"
        assert result["workflow_type"] == "testing"
        assert result["complexity_level"] == "medium"

        # Verify guidance structure
        assert "guidance" in result
        guidance = result["guidance"]

        # Check for essential guidance sections
        assert "title" in guidance
        assert "message" in guidance
        assert "workflow_requirements" in guidance
        assert "yaml_structure_specification" in guidance
        assert "goal_formatting_requirements" in guidance
        assert "acceptance_criteria_structure" in guidance

        # Check workflow templates are provided
        assert "workflow_templates" in result
        templates = result["workflow_templates"]
        assert "simple_linear" in templates
        assert "analysis_planning_construction" in templates
        assert "investigation_resolution" in templates

        # Check complete example is provided
        assert "complete_example" in result
        example = result["complete_example"]
        assert "title" in example
        assert "yaml_content" in example

        # Verify the example YAML contains expected structure
        yaml_content = example["yaml_content"]
        assert "name:" in yaml_content
        assert "description:" in yaml_content
        assert "workflow:" in yaml_content
        assert "goal:" in yaml_content
        assert "root:" in yaml_content
        assert "tree:" in yaml_content

        # Check creation instructions
        assert "creation_instructions" in result
        instructions = result["creation_instructions"]
        assert "title" in instructions
        assert "steps" in instructions
        assert "validation_checklist" in instructions

        # Check next action guidance
        assert "next_action" in result
        next_action = result["next_action"]
        assert "command_template" in next_action
        assert "workflow_guidance" in next_action["command_template"]

    @pytest.mark.asyncio
    async def test_workflow_creation_guidance_with_different_types(self):
        """Test workflow creation guidance with different workflow types."""
        app = FastMCP("test-creation-types")
        register_discovery_prompts(app)

        tools = await app.get_tools()
        creation_tool = tools["workflow_creation_guidance"]

        # Test different workflow types
        workflow_types = ["coding", "debugging", "documentation", "analysis", "testing"]

        for wf_type in workflow_types:
            result = creation_tool.fn(
                task_description=f"Test {wf_type} workflow",
                workflow_type=wf_type,
                complexity_level="medium",
            )

            assert result["status"] == "workflow_creation_guidance"
            assert result["workflow_type"] == wf_type
            assert "guidance" in result
            assert f"Test {wf_type} workflow" in result["guidance"]["message"]

    @pytest.mark.asyncio
    async def test_workflow_creation_guidance_complexity_levels(self):
        """Test workflow creation guidance with different complexity levels."""
        app = FastMCP("test-creation-complexity")
        register_discovery_prompts(app)

        tools = await app.get_tools()
        creation_tool = tools["workflow_creation_guidance"]

        # Test different complexity levels
        complexity_levels = ["simple", "medium", "complex"]

        for complexity in complexity_levels:
            result = creation_tool.fn(
                task_description="Test task with varying complexity",
                workflow_type="general",
                complexity_level=complexity,
            )

            assert result["status"] == "workflow_creation_guidance"
            assert result["complexity_level"] == complexity
            assert "guidance" in result

    @pytest.mark.asyncio
    async def test_workflow_creation_guidance_yaml_format_validation(self):
        """Test that the guidance provides proper YAML formatting requirements."""
        app = FastMCP("test-yaml-format")
        register_discovery_prompts(app)

        tools = await app.get_tools()
        creation_tool = tools["workflow_creation_guidance"]

        result = creation_tool.fn(
            task_description="Validate YAML format guidance", workflow_type="coding"
        )

        # Check that YAML structure specification is comprehensive
        yaml_spec = result["guidance"]["yaml_structure_specification"]

        assert "required_top_level_fields" in yaml_spec
        top_level = yaml_spec["required_top_level_fields"]
        assert "name" in top_level
        assert "description" in top_level
        assert "workflow" in top_level

        assert "workflow_section_structure" in yaml_spec
        workflow_section = yaml_spec["workflow_section_structure"]
        assert "goal" in workflow_section
        assert "root" in workflow_section
        assert "tree" in workflow_section

        assert "node_structure" in yaml_spec
        node_structure = yaml_spec["node_structure"]
        assert "goal" in node_structure
        assert "acceptance_criteria" in node_structure
        assert "next_allowed_nodes" in node_structure

        # Check goal formatting requirements
        goal_format = result["guidance"]["goal_formatting_requirements"]
        assert "structure" in goal_format
        assert "step_formatting" in goal_format
        assert "mandatory_elements" in goal_format

        # Verify mandatory elements are specified
        mandatory_elements = goal_format["mandatory_elements"]
        assert any(
            "🔨 REQUIRED EXECUTION STEPS" in element for element in mandatory_elements
        )
        assert any("⚠️ MANDATORY" in element for element in mandatory_elements)

    @pytest.mark.asyncio
    async def test_workflow_creation_guidance_templates(self):
        """Test that appropriate workflow templates are provided."""
        app = FastMCP("test-templates")
        register_discovery_prompts(app)

        tools = await app.get_tools()
        creation_tool = tools["workflow_creation_guidance"]

        result = creation_tool.fn(
            task_description="Test template provision", workflow_type="coding"
        )

        templates = result["workflow_templates"]

        # Verify all expected templates are present
        expected_templates = [
            "simple_linear",
            "analysis_planning_construction",
            "investigation_resolution",
            "iterative_refinement",
            "branching_decision",
        ]

        for template_name in expected_templates:
            assert template_name in templates
            template = templates[template_name]
            assert "description" in template
            assert "use_case" in template
            assert "example_nodes" in template
            assert isinstance(template["example_nodes"], list)

    @pytest.mark.asyncio
    async def test_workflow_creation_guidance_complete_example(self):
        """Test that the complete example workflow is properly formatted."""
        app = FastMCP("test-complete-example")
        register_discovery_prompts(app)

        tools = await app.get_tools()
        creation_tool = tools["workflow_creation_guidance"]

        result = creation_tool.fn(
            task_description="Test complete example", workflow_type="general"
        )

        example = result["complete_example"]
        yaml_content = example["yaml_content"]

        # Verify the YAML contains all required elements
        required_yaml_elements = [
            "name: Custom Task Workflow",
            "description:",
            "inputs:",
            "task_description:",
            "execution:",
            "max_depth: 10",
            "allow_backtracking: true",
            "workflow:",
            "goal:",
            "root: analyze",
            "tree:",
            "analyze:",
            "plan:",
            "execute:",
            "validate:",
            "acceptance_criteria:",
            "next_allowed_nodes:",
        ]

        for element in required_yaml_elements:
            assert element in yaml_content, f"Missing required YAML element: {element}"

        # Verify the YAML contains proper formatting markers
        formatting_markers = [
            "**MANDATORY",
            "PHASE - FOLLOW EXACTLY:**",
            "**TASK:** ${{ inputs.task_description }}",
            "**🔨 REQUIRED EXECUTION STEPS - NO EXCEPTIONS:**",
            "⚠️ MANDATORY",
        ]

        for marker in formatting_markers:
            assert marker in yaml_content, f"Missing formatting marker: {marker}"
