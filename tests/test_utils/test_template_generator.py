"""Tests for workflow template generator functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from src.accordo_workflow_mcp.models.yaml_workflow import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTree,
)
from src.accordo_workflow_mcp.utils.template_generator import (
    WorkflowTemplateGenerator,
    analyze_existing_workflows,
    create_workflow_template,
)


class TestWorkflowTemplateGenerator:
    """Test WorkflowTemplateGenerator class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def generator(self, temp_dir):
        """Create a WorkflowTemplateGenerator instance for testing."""
        templates_dir = os.path.join(temp_dir, "templates")
        return WorkflowTemplateGenerator(templates_dir)

    @pytest.fixture
    def mock_workflow(self):
        """Create a mock workflow for testing."""
        # Create mock nodes
        node1 = Mock(spec=WorkflowNode)
        node1.goal = "First step goal"
        node1.acceptance_criteria = {"criterion1": "First criterion"}
        node1.next_allowed_nodes = ["step2"]
        node1.next_allowed_workflows = []

        node2 = Mock(spec=WorkflowNode)
        node2.goal = "Second step goal"
        node2.acceptance_criteria = {"criterion2": "Second criterion"}
        node2.next_allowed_nodes = []
        node2.next_allowed_workflows = []

        # Create mock workflow tree
        tree = Mock(spec=WorkflowTree)
        tree.tree = {"step1": node1, "step2": node2}
        tree.goal = "Test workflow goal"
        tree.root = "step1"

        # Create mock workflow definition
        workflow = Mock(spec=WorkflowDefinition)
        workflow.name = "Test Workflow"
        workflow.description = "Test workflow description"
        workflow.inputs = {
            "task_description": {
                "type": "string",
                "description": "Task description",
                "required": True,
            }
        }
        workflow.execution = Mock()
        workflow.execution.max_depth = 5
        workflow.execution.allow_backtracking = True
        workflow.workflow = tree

        return workflow

    def test_init_creates_templates_directory(self, temp_dir):
        """Test that initialization creates the templates directory."""
        templates_dir = os.path.join(temp_dir, "new_templates")
        generator = WorkflowTemplateGenerator(templates_dir)

        assert generator.templates_dir == Path(templates_dir)
        assert os.path.exists(templates_dir)

    @patch("src.accordo_workflow_mcp.utils.template_generator.WorkflowLoader")
    def test_generate_template_from_existing_success(
        self, mock_loader_class, generator, temp_dir
    ):
        """Test successful template generation from existing workflow."""

        # Create a simple object that mimics the workflow structure without Mock complications
        class SimpleNode:
            def __init__(
                self,
                goal,
                acceptance_criteria,
                next_allowed_nodes,
                next_allowed_workflows,
            ):
                self.goal = goal
                self.acceptance_criteria = acceptance_criteria
                self.next_allowed_nodes = next_allowed_nodes
                self.next_allowed_workflows = next_allowed_workflows

        class SimpleTree:
            def __init__(self, goal, root, tree):
                self.goal = goal
                self.root = root
                self.tree = tree

        class SimpleWorkflow:
            def __init__(self, name, description, inputs, execution, workflow):
                self.name = name
                self.description = description
                self.inputs = inputs
                self.execution = execution  # This should be a dictionary, not an object
                self.workflow = workflow

        # Create simple objects instead of Mock objects
        node1 = SimpleNode(
            "First step goal", {"criterion1": "First criterion"}, ["step2"], []
        )
        node2 = SimpleNode(
            "Second step goal", {"criterion2": "Second criterion"}, [], []
        )
        tree = SimpleTree(
            "Test workflow goal", "step1", {"step1": node1, "step2": node2}
        )

        # Use a dictionary for execution instead of a custom object
        execution = {"max_depth": 5, "allow_backtracking": True}

        workflow = SimpleWorkflow(
            "Test Workflow",
            "Test workflow description",
            {
                "task_description": {
                    "type": "string",
                    "description": "Task description",
                    "required": True,
                }
            },
            execution,  # Pass dictionary directly
            tree,
        )

        # Setup mock loader
        mock_loader = Mock()
        mock_loader.load_workflow.return_value = workflow
        mock_loader_class.return_value = mock_loader

        output_path = os.path.join(temp_dir, "test_template.yaml")
        result = generator.generate_template_from_existing("source.yaml", output_path)

        assert result is True
        assert os.path.exists(output_path)

        # Verify the generated template content
        with open(output_path) as f:
            template_data = yaml.safe_load(f)

        assert "Custom Workflow (Based on Test Workflow)" in template_data["name"]
        assert "Template based on Test Workflow" in template_data["description"]
        assert "task_description" in template_data["inputs"]
        assert template_data["workflow"]["root"] == "step1"

    def test_create_basic_template_success(self, generator, temp_dir):
        """Test successful creation of basic template."""
        output_path = os.path.join(temp_dir, "basic_template.yaml")
        result = generator.create_basic_template("Basic Test Template", output_path, 3)

        assert result is True
        assert os.path.exists(output_path)

        # Verify template content
        with open(output_path) as f:
            template_data = yaml.safe_load(f)

        assert template_data["name"] == "Basic Test Template"
        assert "3-step workflow template" in template_data["description"]
        assert len(template_data["workflow"]["tree"]) == 3
        assert template_data["workflow"]["root"] == "step_1"

    def test_create_basic_template_exception(self, generator):
        """Test basic template creation when an exception occurs."""
        # Use invalid path to cause exception
        result = generator.create_basic_template(
            "Test", "/invalid/path/template.yaml", 3
        )
        assert result is False


class TestModuleFunctions:
    """Test module-level functions."""

    def test_create_workflow_template_basic(self):
        """Test creating a basic workflow template."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            output_path = f.name

        try:
            result = create_workflow_template(
                "Test Template", "A test template", output_path, "basic"
            )

            assert result is True
            assert os.path.exists(output_path)

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_create_workflow_template_pattern_based(self):
        """Test creating a pattern-based workflow template."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            output_path = f.name

        try:
            result = create_workflow_template(
                "Pattern Template",
                "A pattern-based template",
                output_path,
                "pattern-based",
            )

            assert result is True
            assert os.path.exists(output_path)

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_create_workflow_template_unknown_type(self):
        """Test creating a template with unknown type falls back to basic."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            output_path = f.name

        try:
            result = create_workflow_template(
                "Unknown Template",
                "A template with unknown type",
                output_path,
                "unknown_type",
            )

            assert result is True
            assert os.path.exists(output_path)

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_create_workflow_template_exception(self):
        """Test template creation when an exception occurs."""
        result = create_workflow_template(
            "Test", "Test", "/invalid/path/template.yaml", "basic"
        )
        assert result is False

    def test_analyze_existing_workflows(self):
        """Test analyzing existing workflows for patterns."""
        # Test with default workflows directory
        result = analyze_existing_workflows()

        # Should return analysis structure even if no workflows found
        assert isinstance(result, dict)
        assert "total_workflows" in result or "patterns" in result

    def test_analyze_existing_workflows_custom_dir(self):
        """Test analyzing workflows in custom directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = analyze_existing_workflows(temp_dir)

            # Should return analysis for empty directory
            assert isinstance(result, dict)


class TestWorkflowTemplateGeneratorExtended:
    """Extended tests for WorkflowTemplateGenerator methods."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def generator(self, temp_dir):
        """Create a WorkflowTemplateGenerator instance for testing."""
        templates_dir = os.path.join(temp_dir, "templates")
        return WorkflowTemplateGenerator(templates_dir)

    def test_analyze_workflow_patterns_no_workflows(self, generator, temp_dir):
        """Test pattern analysis with no workflows."""
        workflows_dir = os.path.join(temp_dir, "empty_workflows")
        os.makedirs(workflows_dir, exist_ok=True)

        result = generator.analyze_workflow_patterns(workflows_dir)

        assert result["patterns"] == {}
        assert result["analysis"] == "No workflows found"

    def test_suggest_template_from_patterns_empty_analysis(self, generator, temp_dir):
        """Test template suggestion with empty analysis."""
        analysis = {
            "total_workflows": 0,
            "average_workflow_length": 3,
            "most_common_nodes": [],
            "most_common_inputs": [],
        }

        output_path = os.path.join(temp_dir, "pattern_template.yaml")
        result = generator.suggest_template_from_patterns(
            analysis, "Pattern Template", output_path
        )

        assert result is True
        assert os.path.exists(output_path)

    def test_suggest_template_from_patterns_with_data(self, generator, temp_dir):
        """Test template suggestion with pattern data."""
        analysis = {
            "total_workflows": 2,
            "average_workflow_length": 3,
            "most_common_nodes": [("analyze", 2), ("build", 2), ("deploy", 1)],
            "most_common_inputs": [("task_description", 2), ("config", 1)],
        }

        output_path = os.path.join(temp_dir, "pattern_template.yaml")
        result = generator.suggest_template_from_patterns(
            analysis, "Pattern Template", output_path
        )

        assert result is True
        assert os.path.exists(output_path)

        # Verify template content
        with open(output_path) as f:
            template_data = yaml.safe_load(f)

        assert template_data["name"] == "Pattern Template"
        assert "2 existing workflows" in template_data["description"]
        assert "analyze" in template_data["workflow"]["tree"]

    def test_suggest_template_from_patterns_exception(self, generator):
        """Test template suggestion when an exception occurs."""
        analysis = {"invalid": "data"}
        result = generator.suggest_template_from_patterns(
            analysis, "Test", "/invalid/path/template.yaml"
        )
        assert result is False

    def test_list_available_templates_empty(self, generator):
        """Test listing templates when directory is empty."""
        templates = generator.list_available_templates()
        assert templates == []

    def test_list_available_templates_with_files(self, generator, temp_dir):
        """Test listing templates with existing files."""
        # Create some template files
        templates_dir = generator.templates_dir
        templates_dir.mkdir(parents=True, exist_ok=True)

        (templates_dir / "template1.yaml").touch()
        (templates_dir / "template2.yaml").touch()
        (templates_dir / "not_yaml.txt").touch()

        templates = generator.list_available_templates()

        assert len(templates) == 2
        assert "template1.yaml" in templates
        assert "template2.yaml" in templates
        assert "not_yaml.txt" not in templates

    def test_get_template_info_not_found(self, generator):
        """Test getting info for non-existent template."""
        info = generator.get_template_info("nonexistent.yaml")
        assert info is None

    def test_get_template_info_success(self, generator, temp_dir):
        """Test getting info for existing template."""
        templates_dir = generator.templates_dir
        templates_dir.mkdir(parents=True, exist_ok=True)

        template_data = {
            "name": "Test Template",
            "description": "A test template",
            "inputs": {"task_description": {"type": "string"}},
            "workflow": {
                "root": "start",
                "tree": {"start": {"goal": "Begin"}, "end": {"goal": "Finish"}},
            },
        }

        template_path = templates_dir / "test.yaml"
        with open(template_path, "w") as f:
            yaml.dump(template_data, f)

        info = generator.get_template_info("test.yaml")

        assert info is not None
        assert info["name"] == "Test Template"
        assert info["description"] == "A test template"
        assert info["node_count"] == 2
        assert info["inputs"] == ["task_description"]
        assert info["root_node"] == "start"

    def test_get_template_info_invalid_yaml(self, generator, temp_dir):
        """Test getting info for template with invalid YAML."""
        templates_dir = generator.templates_dir
        templates_dir.mkdir(parents=True, exist_ok=True)

        template_path = templates_dir / "invalid.yaml"
        with open(template_path, "w") as f:
            f.write("invalid: yaml: content: [")

        info = generator.get_template_info("invalid.yaml")
        assert info is None
