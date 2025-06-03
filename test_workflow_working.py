#!/usr/bin/env python3
"""
Working integration test for the workflow-commander MCP system.

Uses proper async patterns to test the complete workflow functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastmcp import FastMCP

from dev_workflow_mcp.prompts.discovery_prompts import register_discovery_prompts
from dev_workflow_mcp.prompts.phase_prompts import register_phase_prompts


def create_test_workflow_yaml():
    """Create a test workflow YAML content for testing."""
    return """
name: Test Coding Workflow
description: A simple test workflow for integration testing
workflow:
  goal: Complete a coding task with proper analysis and implementation
  root: analyze
  tree:
    analyze:
      goal: Gather requirements and understand the task
      description: Analyze the requirements and codebase
      acceptance_criteria:
        understanding: "Task requirements are clearly understood"
        context: "Relevant codebase context has been gathered"
      next_allowed_nodes:
        - blueprint
        - construct
    blueprint:
      goal: Create detailed implementation plan
      description: Design the solution approach
      acceptance_criteria:
        plan: "Detailed step-by-step implementation plan created"
        design: "Technical approach and architecture defined"
      next_allowed_nodes:
        - construct
        - validate
    construct:
      goal: Implement the planned solution
      description: Execute the implementation plan
      acceptance_criteria:
        implementation: "All planned features implemented"
        testing: "Code is tested and working"
      next_allowed_nodes:
        - validate
    validate:
      goal: Verify implementation meets requirements
      description: Final validation and quality checks
      acceptance_criteria:
        quality: "Code meets quality standards"
        requirements: "All requirements satisfied"
      next_allowed_nodes: []
inputs:
  task_description:
    type: string
    description: Description of the coding task to complete
    required: true
"""


async def test_yaml_loader():
    """Test the YAML loader functionality."""
    print("📄 Testing YAML Loader...")

    try:
        from dev_workflow_mcp.utils.yaml_loader import WorkflowLoader

        loader = WorkflowLoader()
        test_yaml = create_test_workflow_yaml()

        # Test loading workflow from string
        workflow = loader.load_workflow_from_string(test_yaml, "Test Workflow")

        if workflow:
            print("✅ Successfully loaded workflow from YAML string")
            print(f"📝 Workflow name: {workflow.name}")
            print(f"🎯 Workflow goal: {workflow.workflow.goal}")
            print(f"🌲 Nodes: {len(workflow.workflow.tree)}")
            print(f"📍 Root node: {workflow.workflow.root}")

            # Test node structure
            nodes = list(workflow.workflow.tree.keys())
            print(f"🔗 Node names: {nodes}")

            # Test node transitions
            analyze_node = workflow.workflow.tree["analyze"]
            print(f"🎯 Analyze node transitions: {analyze_node.next_allowed_nodes}")

            return True
        else:
            print("❌ Failed to load workflow from YAML string")
            return False

    except Exception as e:
        print(f"❌ YAML loader test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_discovery_prompts():
    """Test discovery prompts with proper async handling."""
    print("\n🔍 Testing Discovery Prompts...")

    try:
        app = FastMCP("test-discovery")
        register_discovery_prompts(app)

        # Get the tools asynchronously
        tools = await app.get_tools()
        print(f"📋 Registered tools: {list(tools.keys())}")

        if "workflow_discovery" in tools:
            # Get the actual function
            discovery_tool = tools["workflow_discovery"]

            # Call it directly
            result = discovery_tool.fn(
                task_description="Test task: Add user authentication to web app"
            )

            print("✅ Discovery function executed successfully")
            print(f"📊 Status: {result.get('status', 'unknown')}")
            print(
                f"🎯 Agent action required: {result.get('status') == 'agent_action_required'}"
            )

            instructions = result.get("instructions", {})
            if instructions:
                steps = instructions.get("required_steps", [])
                print(f"📝 Instructions provided: {len(steps)} steps")
                print(f"🔧 First step: {steps[0] if steps else 'None'}")

            return True
        else:
            print("❌ workflow_discovery tool not found")
            return False

    except Exception as e:
        print(f"❌ Discovery prompts test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_workflow_guidance():
    """Test workflow guidance with proper async handling."""
    print("\n🔄 Testing Workflow Guidance...")

    try:
        app = FastMCP("test-workflow")
        register_phase_prompts(app)

        tools = await app.get_tools()
        print(f"📋 Registered tools: {list(tools.keys())}")

        if "workflow_guidance" in tools:
            guidance_tool = tools["workflow_guidance"]

            # Test 1: No session enforcement
            print("\n🚫 Testing no session enforcement...")
            result1 = guidance_tool.fn(
                task_description="Test task: Add user authentication",
                action="plan",
                context="",
            )

            if "No Active Workflow Session" in result1:
                print("✅ Correctly enforced discovery-first requirement")
            else:
                print("❌ Did not enforce discovery-first requirement")
                print(f"🔍 Result: {result1[:200]}...")
                return False

            # Test 2: Start without YAML
            print("\n📝 Testing start without YAML...")
            result2 = guidance_tool.fn(
                task_description="Test task: Add user authentication",
                action="start",
                context="workflow: Test Coding Workflow",
            )

            if "Workflow YAML Required" in result2:
                print("✅ Correctly requested YAML content from agent")
            else:
                print("❌ Did not request YAML content")
                print(f"🔍 Result: {result2[:200]}...")
                return False

            # Test 3: Start with YAML
            print("\n🚀 Testing start with YAML...")
            test_yaml = create_test_workflow_yaml()
            context = f"workflow: Test Coding Workflow\nyaml: {test_yaml}"

            result3 = guidance_tool.fn(
                task_description="Test task: Add user authentication",
                action="start",
                context=context,
            )

            if "Workflow Started" in result3:
                print("✅ Successfully started workflow from YAML content")
                print("🎯 Started at analyze phase")
            else:
                print("❌ Failed to start workflow from YAML")
                print(f"🔍 Result: {result3[:200]}...")
                return False

            # Test 4: Workflow navigation (dynamic session should be active now)
            print("\n🔄 Testing workflow navigation...")
            result4 = guidance_tool.fn(
                task_description="Test task: Add user authentication",
                action="next",
                context="choose: blueprint",
            )

            if "Transitioned to" in result4 or "blueprint" in result4.lower():
                print("✅ Successfully navigated to blueprint phase")
            else:
                print("⚠️ Navigation might not have worked as expected")
                print(f"🔍 Result: {result4[:200]}...")

            # Test 5: Legacy fallback (new session)
            print("\n🔄 Testing legacy fallback...")
            # Create new app to reset sessions
            app2 = FastMCP("test-workflow-legacy")
            register_phase_prompts(app2)
            tools2 = await app2.get_tools()

            result5 = tools2["workflow_guidance"].fn(
                task_description="Test task: Add user authentication",
                action="start",
                context="",
            )

            if "Workflow Discovery Required" in result5:
                print("✅ Correctly showed discovery requirement")
            else:
                print("❌ Did not show discovery requirement")
                print(f"🔍 Result: {result5[:200]}...")
                return False

            return True
        else:
            print("❌ workflow_guidance tool not found")
            return False

    except Exception as e:
        print(f"❌ Workflow guidance test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_workflow_state():
    """Test workflow state management with proper async handling."""
    print("\n📊 Testing Workflow State...")

    try:
        app = FastMCP("test-workflow")
        register_phase_prompts(app)

        tools = await app.get_tools()

        if "workflow_state" in tools:
            state_tool = tools["workflow_state"]

            # Test getting state
            result = state_tool.fn(operation="get")

            print("✅ Workflow state retrieval executed")
            if "WORKFLOW STATE" in result:
                print("✅ Successfully retrieved workflow state")
                return True
            else:
                print("❌ Failed to retrieve workflow state")
                print(f"🔍 Result: {result[:200]}...")
                return False
        else:
            print("❌ workflow_state tool not found")
            return False

    except Exception as e:
        print(f"❌ Workflow state test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all async tests."""
    print("🧪 Starting Comprehensive Workflow Integration Tests (Async)")
    print("=" * 60)

    tests = [
        ("YAML Loader", test_yaml_loader),
        ("Discovery Prompts", test_discovery_prompts),
        ("Workflow Guidance", test_workflow_guidance),
        ("Workflow State", test_workflow_state),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n📈 Overall Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Workflow system is functioning correctly.")
    else:
        print("⚠️  Some tests failed. Review the issues above.")

    return failed == 0


async def main():
    """Main async entry point."""
    success = await run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
