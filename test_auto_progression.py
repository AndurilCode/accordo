#!/usr/bin/env python3
"""Test script for auto-progression functionality."""

import os
from src.dev_workflow_mcp.utils.schema_analyzer import (
    get_auto_transition_target,
    should_auto_progress,
)
from src.dev_workflow_mcp.utils.yaml_loader import WorkflowLoader


def test_auto_progression():
    """Test auto-progression detection on all nodes."""
    # Enable auto-progression for this test
    os.environ['WORKFLOW_AUTO_PROGRESSION_ENABLED'] = 'true'
    
    loader = WorkflowLoader()
    workflow = loader.load_workflow('.workflow-commander/workflows/auto-progression-test.yaml')
    
    print("🧪 Testing Auto-Progression Detection")
    print("=" * 50)
    
    # Expected results
    expected_results = {
        'start': True,       # Single path to linear1
        'linear1': True,     # Single path to linear2  
        'linear2': True,     # Single path to decision_point
        'decision_point': False,  # Multiple paths (decision)
        'option_a': True,    # Single path to final
        'option_b': True,    # Single path to final
        'final': False       # Terminal node (no next nodes)
    }
    
    all_passed = True
    
    for node_name, expected in expected_results.items():
        node = workflow.workflow.tree[node_name]
        actual = should_auto_progress(node)
        target = get_auto_transition_target(node)
        
        status = "✅ PASS" if actual == expected else "❌ FAIL"
        if actual != expected:
            all_passed = False
            
        print(f"{node_name:15} | Expected: {str(expected):5} | Actual: {str(actual):5} | Target: {target or 'None':15} | {status}")
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Auto-progression detection working correctly.")
    else:
        print("❌ SOME TESTS FAILED! Check implementation.")
    
    # Clean up environment variable
    if 'WORKFLOW_AUTO_PROGRESSION_ENABLED' in os.environ:
        del os.environ['WORKFLOW_AUTO_PROGRESSION_ENABLED']
    
    return all_passed

if __name__ == "__main__":
    test_auto_progression() 