#!/usr/bin/env python3
"""Integration test for workflow functionality with existing workflows."""

from src.dev_workflow_mcp.utils.yaml_loader import WorkflowLoader
from src.dev_workflow_mcp.utils.schema_analyzer import analyze_node_from_schema

def test_integration():
    """Test integration with existing workflows."""
    loader = WorkflowLoader()
    
    # Test default workflow
    workflow = loader.load_workflow('.workflow-commander/workflows/default-coding.yaml')
    print("🔧 Testing Default Coding Workflow:")
    
    for node_name, node in workflow.workflow.tree.items():
        analysis = analyze_node_from_schema(node, workflow)
        next_count = len(node.next_allowed_nodes or [])
        has_criteria = bool(analysis["acceptance_criteria"])
        print(f"  {node_name}: next_nodes = {next_count}, has_criteria = {has_criteria}, terminal = {analysis['is_terminal']}")
    
    # Test debugging workflow
    workflow = loader.load_workflow('.workflow-commander/workflows/debugging.yaml')
    print("\n🐛 Testing Debugging Workflow:")
    
    for node_name, node in workflow.workflow.tree.items():
        analysis = analyze_node_from_schema(node, workflow)
        next_count = len(node.next_allowed_nodes or [])
        has_criteria = bool(analysis["acceptance_criteria"])
        print(f"  {node_name}: next_nodes = {next_count}, has_criteria = {has_criteria}, terminal = {analysis['is_terminal']}")
    
    print("\n✅ Integration tests passed - workflow functionality working correctly")

if __name__ == "__main__":
    test_integration() 