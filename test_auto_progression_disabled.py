#!/usr/bin/env python3
"""Test script to verify auto-progression can be disabled."""

import os
from src.dev_workflow_mcp.utils.schema_analyzer import should_auto_progress
from src.dev_workflow_mcp.utils.yaml_loader import WorkflowLoader


def test_auto_progression_disabled():
    """Test that auto-progression can be disabled via environment variable."""
    loader = WorkflowLoader()
    workflow = loader.load_workflow('.workflow-commander/workflows/auto-progression-test.yaml')
    
    print("🔧 Testing Auto-Progression Disable Feature")
    print("=" * 50)
    
    # Test with auto-progression enabled (set environment variable)
    os.environ['WORKFLOW_AUTO_PROGRESSION_ENABLED'] = 'true'
    print("🟢 Testing with WORKFLOW_AUTO_PROGRESSION_ENABLED=true")
    
    enabled_results = {}
    for node_name, node in workflow.workflow.tree.items():
        auto = should_auto_progress(node)
        enabled_results[node_name] = auto
        next_count = len(node.next_allowed_nodes or [])
        print(f"  {node_name:15} | auto-progress = {str(auto):5} | next_nodes: {next_count}")
    
    print("\n🔴 Testing with WORKFLOW_AUTO_PROGRESSION_ENABLED=false")
    
    # Test with auto-progression disabled
    os.environ['WORKFLOW_AUTO_PROGRESSION_ENABLED'] = 'false'
    
    disabled_results = {}
    for node_name, node in workflow.workflow.tree.items():
        auto = should_auto_progress(node)
        disabled_results[node_name] = auto
        next_count = len(node.next_allowed_nodes or [])
        print(f"  {node_name:15} | auto-progress = {str(auto):5} | next_nodes: {next_count}")
    
    # Verify results
    print("\n" + "=" * 50)
    print("📊 VERIFICATION RESULTS:")
    
    all_disabled = all(not auto for auto in disabled_results.values())
    some_enabled = any(auto for auto in enabled_results.values())
    
    if all_disabled and some_enabled:
        print("✅ SUCCESS: Auto-progression correctly disabled when WORKFLOW_AUTO_PROGRESSION_ENABLED=false")
        print(f"   - Enabled state: {sum(enabled_results.values())} nodes can auto-progress")
        print(f"   - Disabled state: {sum(disabled_results.values())} nodes can auto-progress (should be 0)")
    else:
        print("❌ FAILURE: Auto-progression disable not working correctly")
        print(f"   - Enabled state: {sum(enabled_results.values())} nodes can auto-progress")
        print(f"   - Disabled state: {sum(disabled_results.values())} nodes can auto-progress")
    
    # Clean up environment variable
    if 'WORKFLOW_AUTO_PROGRESSION_ENABLED' in os.environ:
        del os.environ['WORKFLOW_AUTO_PROGRESSION_ENABLED']
    
    return all_disabled and some_enabled


if __name__ == "__main__":
    success = test_auto_progression_disabled()
    exit(0 if success else 1) 