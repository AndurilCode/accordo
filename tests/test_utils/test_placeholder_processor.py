"""Tests for placeholder processor functionality."""

import pytest

from src.dev_workflow_mcp.utils.placeholder_processor import (
    replace_placeholders,
    process_workflow_content,
)


class TestReplacePlaceholders:
    """Test the replace_placeholders function."""

    def test_basic_replacement(self):
        """Test basic placeholder replacement."""
        content = "**ANALYZE PHASE:** ${{ inputs.task_description }}"
        inputs = {"task_description": "Add user authentication"}
        
        result = replace_placeholders(content, inputs)
        expected = "**ANALYZE PHASE:** Add user authentication"
        
        assert result == expected

    def test_multiple_placeholders(self):
        """Test multiple placeholders in one string."""
        content = "Task: ${{ inputs.task_description }} at path ${{ inputs.project_config_path }}"
        inputs = {
            "task_description": "Fix memory leak", 
            "project_config_path": "/path/to/config.md"
        }
        
        result = replace_placeholders(content, inputs)
        expected = "Task: Fix memory leak at path /path/to/config.md"
        
        assert result == expected

    def test_missing_input_leaves_placeholder(self):
        """Test that missing inputs leave placeholders unchanged."""
        content = "Task: ${{ inputs.task_description }} with ${{ inputs.missing_var }}"
        inputs = {"task_description": "Add tests"}
        
        result = replace_placeholders(content, inputs)
        expected = "Task: Add tests with ${{ inputs.missing_var }}"
        
        assert result == expected

    def test_whitespace_handling(self):
        """Test placeholder replacement with various whitespace."""
        test_cases = [
            ("${{ inputs.task_description }}", "Test task"),
            ("${{inputs.task_description}}", "Test task"),
            ("${{ inputs.task_description}}", "Test task"),
            ("${{inputs.task_description }}", "Test task"),
        ]
        
        inputs = {"task_description": "Test task"}
        
        for content, expected in test_cases:
            result = replace_placeholders(content, inputs)
            assert result == expected, f"Failed for input: {content}"

    def test_empty_content(self):
        """Test with empty content."""
        result = replace_placeholders("", {"task_description": "test"})
        assert result == ""

    def test_empty_inputs(self):
        """Test with empty inputs."""
        content = "Task: ${{ inputs.task_description }}"
        result = replace_placeholders(content, {})
        assert result == content  # Should remain unchanged

    def test_none_values(self):
        """Test with None input values."""
        content = "Task: ${{ inputs.task_description }}"
        inputs = {"task_description": None}
        
        result = replace_placeholders(content, inputs)
        expected = "Task: "  # None becomes empty string
        
        assert result == expected

    def test_non_string_values(self):
        """Test with non-string input values."""
        content = "Count: ${{ inputs.item_count }}, Flag: ${{ inputs.is_enabled }}"
        inputs = {"item_count": 42, "is_enabled": True}
        
        result = replace_placeholders(content, inputs)
        expected = "Count: 42, Flag: True"
        
        assert result == expected

    def test_complex_variable_names(self):
        """Test with complex variable names."""
        content = "Config: ${{ inputs.project_config_path_v2 }}"
        inputs = {"project_config_path_v2": "/path/to/config"}
        
        result = replace_placeholders(content, inputs)
        expected = "Config: /path/to/config"
        
        assert result == expected

    def test_no_placeholders(self):
        """Test content with no placeholders."""
        content = "This is plain text with no variables."
        inputs = {"task_description": "test"}
        
        result = replace_placeholders(content, inputs)
        assert result == content


class TestProcessWorkflowContent:
    """Test the process_workflow_content function."""

    def test_workflow_processing(self):
        """Test processing a workflow-like structure."""
        workflow = {
            "name": "Test Workflow",
            "workflow": {
                "tree": {
                    "analyze": {
                        "goal": "**ANALYZE:** ${{ inputs.task_description }}",
                        "acceptance_criteria": {
                            "config_check": "Read ${{ inputs.project_config_path }} completely"
                        }
                    }
                }
            }
        }
        
        inputs = {
            "task_description": "Implement OAuth",
            "project_config_path": ".workflow-commander/project_config.md"
        }
        
        result = process_workflow_content(workflow, inputs)
        
        assert result["workflow"]["tree"]["analyze"]["goal"] == "**ANALYZE:** Implement OAuth"
        assert result["workflow"]["tree"]["analyze"]["acceptance_criteria"]["config_check"] == "Read .workflow-commander/project_config.md completely"

    def test_nested_structure_processing(self):
        """Test processing deeply nested structures."""
        workflow = {
            "levels": {
                "level1": {
                    "level2": {
                        "content": "Task: ${{ inputs.task_description }}"
                    }
                }
            },
            "list_content": [
                "First: ${{ inputs.first_item }}",
                "Second: ${{ inputs.second_item }}"
            ]
        }
        
        inputs = {
            "task_description": "Deep nesting test",
            "first_item": "Item 1",
            "second_item": "Item 2"
        }
        
        result = process_workflow_content(workflow, inputs)
        
        assert result["levels"]["level1"]["level2"]["content"] == "Task: Deep nesting test"
        assert result["list_content"][0] == "First: Item 1"
        assert result["list_content"][1] == "Second: Item 2"

    def test_empty_inputs_no_processing(self):
        """Test that empty inputs don't modify the workflow."""
        workflow = {
            "goal": "Task: ${{ inputs.task_description }}"
        }
        
        result = process_workflow_content(workflow, {})
        
        assert result == workflow  # Should be unchanged

    def test_original_workflow_unchanged(self):
        """Test that the original workflow dict is not modified."""
        original_workflow = {
            "goal": "Task: ${{ inputs.task_description }}"
        }
        
        inputs = {"task_description": "Test task"}
        
        result = process_workflow_content(original_workflow, inputs)
        
        # Original should be unchanged
        assert original_workflow["goal"] == "Task: ${{ inputs.task_description }}"
        # Result should be processed
        assert result["goal"] == "Task: Test task" 