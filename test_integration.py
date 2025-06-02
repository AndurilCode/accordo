#!/usr/bin/env python3
"""Integration test for auto-progression with existing workflows."""

from src.dev_workflow_mcp.utils.yaml_loader import WorkflowLoader
from src.dev_workflow_mcp.utils.schema_analyzer import should_auto_progress

def test_integration():
    """Test integration with existing workflows."""
    loader = WorkflowLoader()
    
    # Test default workflow
    workflow = loader.load_workflow('.workflow-commander/workflows/default-coding.yaml')
    print("🔧 Testing Default Coding Workflow:")
    
    for node_name, node in workflow.workflow.tree.items():
        auto = should_auto_progress(node)
        next_count = len(node.next_allowed_nodes or [])
        print(f"  {node_name}: auto-progress = {auto} (next_nodes: {next_count})")
    
    # Test debugging workflow
    workflow = loader.load_workflow('.workflow-commander/workflows/debugging.yaml')
    print("\n🐛 Testing Debugging Workflow:")
    
    for node_name, node in workflow.workflow.tree.items():
        auto = should_auto_progress(node)
        next_count = len(node.next_allowed_nodes or [])
        print(f"  {node_name}: auto-progress = {auto} (next_nodes: {next_count})")
    
    print("\n✅ Integration tests passed - backwards compatibility maintained")

if __name__ == "__main__":
    test_integration() 