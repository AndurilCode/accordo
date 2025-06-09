"""Tests for YAML workflow loader functionality."""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.accordo_workflow_mcp.models.yaml_workflow import WorkflowDefinition
from src.accordo_workflow_mcp.utils.yaml_loader import (
    WorkflowLoader,
    WorkflowLoadError,
    get_available_workflows,
    load_workflow_by_name,
    validate_workflow,
)


class TestWorkflowLoadError:
    """Test WorkflowLoadError exception."""

    def test_workflow_load_error_creation(self):
        """Test creating WorkflowLoadError."""
        error = WorkflowLoadError("Test error message")
        assert str(error) == "Test error message"
        assert error.file_path is None
        assert isinstance(error, Exception)

    def test_workflow_load_error_with_file_path(self):
        """Test creating WorkflowLoadError with file path."""
        error = WorkflowLoadError("Test error message", "/path/to/file.yaml")
        assert str(error) == "Test error message"
        assert error.file_path == "/path/to/file.yaml"


class TestWorkflowLoader:
    """Test WorkflowLoader class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def valid_workflow_yaml(self):
        """Create valid workflow YAML content."""
        return """
name: Test Workflow
description: A test workflow for unit testing

inputs:
  task_description:
    type: string
    description: Description of the task to be performed
    required: true

workflow:
  goal: Complete test task
  root: start
  tree:
    start:
      goal: Start the workflow
      acceptance_criteria:
        setup: "Initial setup completed"
      next_allowed_nodes: [middle]
      next_allowed_workflows: []
    middle:
      goal: Middle step
      acceptance_criteria:
        progress: "Middle step completed"
      next_allowed_nodes: [end]
      next_allowed_workflows: []
    end:
      goal: End the workflow
      acceptance_criteria:
        completion: "Workflow completed"
      next_allowed_nodes: []
      next_allowed_workflows: []
"""

    @pytest.fixture
    def invalid_workflow_yaml(self):
        """Create invalid workflow YAML content."""
        return """
name: Invalid Workflow
# Missing required fields like description, workflow, etc.
invalid_field: "This should not be here"
"""

    @pytest.fixture
    def workflows_dir_with_files(
        self, temp_dir, valid_workflow_yaml, invalid_workflow_yaml
    ):
        """Create a workflows directory with test files."""
        workflows_dir = temp_dir / "workflows"
        workflows_dir.mkdir()

        # Create valid workflow file
        valid_file = workflows_dir / "valid_workflow.yaml"
        valid_file.write_text(valid_workflow_yaml)

        # Create invalid workflow file
        invalid_file = workflows_dir / "invalid_workflow.yaml"
        invalid_file.write_text(invalid_workflow_yaml)

        # Create non-YAML file (should be ignored)
        text_file = workflows_dir / "readme.txt"
        text_file.write_text("This is not a YAML file")

        return workflows_dir

    def test_init(self, temp_dir):
        """Test WorkflowLoader initialization."""
        loader = WorkflowLoader(str(temp_dir))
        assert loader.workflows_dir == temp_dir

    def test_init_default_path(self):
        """Test WorkflowLoader initialization with default path."""
        loader = WorkflowLoader()
        assert loader.workflows_dir == Path(".accordo/workflows")

    def test_discover_workflows_no_directory(self, temp_dir):
        """Test discover_workflows when directory doesn't exist."""
        nonexistent_dir = temp_dir / "nonexistent"
        loader = WorkflowLoader(str(nonexistent_dir))

        result = loader.discover_workflows()

        assert result == {}

    def test_discover_workflows_empty_directory(self, temp_dir):
        """Test discover_workflows with empty directory."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()
        loader = WorkflowLoader(str(empty_dir))

        result = loader.discover_workflows()

        assert result == {}

    def test_discover_workflows_with_files(self, workflows_dir_with_files):
        """Test discover_workflows with valid and invalid files."""
        loader = WorkflowLoader(str(workflows_dir_with_files))

        result = loader.discover_workflows()

        # Should only include valid workflows
        assert len(result) == 1
        assert "Test Workflow" in result
        assert isinstance(result["Test Workflow"], WorkflowDefinition)

    def test_load_workflow_success(self, temp_dir, valid_workflow_yaml):
        """Test loading a valid workflow file."""
        workflow_file = temp_dir / "test_workflow.yaml"
        workflow_file.write_text(valid_workflow_yaml)

        loader = WorkflowLoader()
        result = loader.load_workflow(str(workflow_file))

        assert result is not None
        assert isinstance(result, WorkflowDefinition)
        assert result.name == "Test Workflow"
        assert result.description == "A test workflow for unit testing"

    def test_load_workflow_file_not_found(self, temp_dir):
        """Test loading a non-existent workflow file."""
        nonexistent_file = temp_dir / "nonexistent.yaml"

        loader = WorkflowLoader()
        result = loader.load_workflow(str(nonexistent_file))

        assert result is None

    def test_load_workflow_invalid_yaml(self, temp_dir):
        """Test loading an invalid YAML file."""
        invalid_file = temp_dir / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [")

        loader = WorkflowLoader()
        result = loader.load_workflow(str(invalid_file))

        assert result is None

    def test_load_workflow_invalid_schema(self, temp_dir, invalid_workflow_yaml):
        """Test loading a YAML file with invalid schema."""
        invalid_file = temp_dir / "invalid_schema.yaml"
        invalid_file.write_text(invalid_workflow_yaml)

        loader = WorkflowLoader()
        result = loader.load_workflow(str(invalid_file))

        assert result is None

    def test_load_workflow_from_string_success(self, valid_workflow_yaml):
        """Test loading workflow from string content."""
        loader = WorkflowLoader()
        result = loader.load_workflow_from_string(valid_workflow_yaml)

        assert result is not None
        assert isinstance(result, WorkflowDefinition)
        assert result.name == "Test Workflow"

    def test_load_workflow_from_string_with_name_override(self, valid_workflow_yaml):
        """Test loading workflow from string with name override."""
        loader = WorkflowLoader()
        result = loader.load_workflow_from_string(valid_workflow_yaml, "Override Name")

        assert result is not None
        assert result.name == "Override Name"

    def test_load_workflow_from_string_invalid(self):
        """Test loading workflow from invalid string content."""
        loader = WorkflowLoader()
        result = loader.load_workflow_from_string("invalid: yaml: [")

        assert result is None

    def test_load_all_workflows(self, workflows_dir_with_files):
        """Test load_all_workflows method."""
        loader = WorkflowLoader(str(workflows_dir_with_files))

        result = loader.load_all_workflows()

        assert len(result) == 1
        assert "Test Workflow" in result

    def test_list_workflow_names(self, workflows_dir_with_files):
        """Test list_workflow_names method."""
        loader = WorkflowLoader(str(workflows_dir_with_files))

        result = loader.list_workflow_names()

        assert result == ["Test Workflow"]

    def test_list_workflow_names_empty(self, temp_dir):
        """Test list_workflow_names with no workflows."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()
        loader = WorkflowLoader(str(empty_dir))

        result = loader.list_workflow_names()

        assert result == []

    def test_get_workflow_by_name_found(self, workflows_dir_with_files):
        """Test get_workflow_by_name when workflow exists."""
        loader = WorkflowLoader(str(workflows_dir_with_files))

        result = loader.get_workflow_by_name("Test Workflow")

        assert result is not None
        assert isinstance(result, WorkflowDefinition)
        assert result.name == "Test Workflow"

    def test_get_workflow_by_name_not_found(self, workflows_dir_with_files):
        """Test get_workflow_by_name when workflow doesn't exist."""
        loader = WorkflowLoader(str(workflows_dir_with_files))

        result = loader.get_workflow_by_name("Nonexistent Workflow")

        assert result is None

    def test_validate_workflow_file_valid(self, temp_dir, valid_workflow_yaml):
        """Test validating a valid workflow file."""
        workflow_file = temp_dir / "valid.yaml"
        workflow_file.write_text(valid_workflow_yaml)

        loader = WorkflowLoader()
        result = loader.validate_workflow_file(str(workflow_file))

        assert result["valid"] is True
        assert result["errors"] == []
        assert result["workflow_name"] == "Test Workflow"
        assert result["node_count"] == 3

    def test_validate_workflow_file_invalid_yaml(self, temp_dir):
        """Test validating an invalid YAML file."""
        invalid_file = temp_dir / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: [")

        loader = WorkflowLoader()
        result = loader.validate_workflow_file(str(invalid_file))

        assert result["valid"] is False
        assert "error" in result

    def test_validate_workflow_file_missing_fields(self, temp_dir):
        """Test validating a workflow with missing required fields."""
        incomplete_yaml = """
name: ""
description: ""
workflow:
  goal: "Test"
  root: "nonexistent"
  tree: {}
"""
        workflow_file = temp_dir / "incomplete.yaml"
        workflow_file.write_text(incomplete_yaml)

        loader = WorkflowLoader()
        result = loader.validate_workflow_file(str(workflow_file))

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("name is required" in error for error in result["errors"])
        assert any("description is required" in error for error in result["errors"])

    def test_validate_workflow_file_invalid_node_references(self, temp_dir):
        """Test validating a workflow with invalid node references."""
        invalid_refs_yaml = """
name: Test Workflow
description: Test description
workflow:
  goal: Test goal
  root: start
  tree:
    start:
      goal: Start goal
      acceptance_criteria: {}
      next_allowed_nodes: [nonexistent_node]
      next_allowed_workflows: []
"""
        workflow_file = temp_dir / "invalid_refs.yaml"
        workflow_file.write_text(invalid_refs_yaml)

        loader = WorkflowLoader()
        result = loader.validate_workflow_file(str(workflow_file))

        assert result["valid"] is False
        assert any(
            "references non-existent node" in error for error in result["errors"]
        )

    def test_validate_workflow_file_root_not_in_tree(self, temp_dir):
        """Test validating a workflow where root node is not in tree."""
        invalid_root_yaml = """
name: Test Workflow
description: Test description
workflow:
  goal: Test goal
  root: nonexistent_root
  tree:
    start:
      goal: Start goal
      acceptance_criteria: {}
      next_allowed_nodes: []
      next_allowed_workflows: []
"""
        workflow_file = temp_dir / "invalid_root.yaml"
        workflow_file.write_text(invalid_root_yaml)

        loader = WorkflowLoader()
        result = loader.validate_workflow_file(str(workflow_file))

        assert result["valid"] is False
        assert any(
            "Root node 'nonexistent_root' not found" in error
            for error in result["errors"]
        )

    def test_validate_workflow_file_exception(self, temp_dir):
        """Test validate_workflow_file when an exception occurs."""
        nonexistent_file = temp_dir / "nonexistent.yaml"

        loader = WorkflowLoader()
        result = loader.validate_workflow_file(str(nonexistent_file))

        assert result["valid"] is False
        assert "Exception during validation" in result["error"]


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def valid_workflow_yaml(self):
        """Create valid workflow YAML content."""
        return """
name: Test Workflow
description: A test workflow for unit testing

inputs:
  task_description:
    type: string
    description: Description of the task to be performed
    required: true

workflow:
  goal: Complete test task
  root: start
  tree:
    start:
      goal: Start the workflow
      acceptance_criteria:
        setup: "Initial setup completed"
      next_allowed_nodes: []
      next_allowed_workflows: []
"""

    def test_load_workflow_by_name_found(self, temp_dir, valid_workflow_yaml):
        """Test load_workflow_by_name convenience function when workflow exists."""
        workflows_dir = temp_dir / "workflows"
        workflows_dir.mkdir()
        workflow_file = workflows_dir / "test.yaml"
        workflow_file.write_text(valid_workflow_yaml)

        result = load_workflow_by_name("Test Workflow", str(workflows_dir))

        assert result is not None
        assert result.name == "Test Workflow"

    def test_load_workflow_by_name_not_found(self, temp_dir):
        """Test load_workflow_by_name convenience function when workflow doesn't exist."""
        workflows_dir = temp_dir / "workflows"
        workflows_dir.mkdir()

        result = load_workflow_by_name("Nonexistent", str(workflows_dir))

        assert result is None

    def test_get_available_workflows_with_workflows(
        self, temp_dir, valid_workflow_yaml
    ):
        """Test get_available_workflows convenience function with workflows."""
        workflows_dir = temp_dir / "workflows"
        workflows_dir.mkdir()
        workflow_file = workflows_dir / "test.yaml"
        workflow_file.write_text(valid_workflow_yaml)

        result = get_available_workflows(str(workflows_dir))

        assert result == ["Test Workflow"]

    def test_get_available_workflows_empty(self, temp_dir):
        """Test get_available_workflows convenience function with no workflows."""
        workflows_dir = temp_dir / "workflows"
        workflows_dir.mkdir()

        result = get_available_workflows(str(workflows_dir))

        assert result == []

    def test_validate_workflow_convenience_function(
        self, temp_dir, valid_workflow_yaml
    ):
        """Test validate_workflow convenience function."""
        workflow_file = temp_dir / "test.yaml"
        workflow_file.write_text(valid_workflow_yaml)

        result = validate_workflow(str(workflow_file))

        assert result["valid"] is True
        assert result["workflow_name"] == "Test Workflow"
