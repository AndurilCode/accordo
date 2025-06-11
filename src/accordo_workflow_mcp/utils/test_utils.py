"""Test utilities for validating accordo package functionality."""

import importlib
from datetime import UTC, datetime
from typing import Any


def validate_accordo_package() -> dict[str, Any]:
    """
    Validate accordo package functionality by testing key imports and components.

    Returns:
        Dict containing validation results including status, timestamps, and component tests
    """
    results = {
        "status": "success",
        "package_name": "accordo_workflow_mcp",
        "errors": [],
        "warnings": [],
        "key_functions": [],
        "service_availability": {},
        "import_status": {},
    }

    try:
        results["timestamp"] = datetime.now(UTC).isoformat()

        # Test core module imports
        core_modules = [
            "src.accordo_workflow_mcp.server",
            "src.accordo_workflow_mcp.utils.session_manager",
            "src.accordo_workflow_mcp.utils.yaml_loader",
            "src.accordo_workflow_mcp.models.workflow_state",
            "src.accordo_workflow_mcp.models.yaml_workflow",
        ]

        for module_name in core_modules:
            try:
                importlib.import_module(module_name)
                results["import_status"][module_name] = "success"
            except ImportError as e:
                results["import_status"][module_name] = f"failed: {e}"
                results["errors"].append(f"Failed to import {module_name}: {e}")

        # Test key function availability
        key_functions = [
            "get_session",
            "create_dynamic_session",
            "update_session",
            "get_sessions_by_client",
        ]

        try:
            session_manager = importlib.import_module(
                "src.accordo_workflow_mcp.utils.session_manager"
            )
            for func_name in key_functions:
                if hasattr(session_manager, func_name):
                    results["key_functions"].append(func_name)
                else:
                    results["warnings"].append(f"Function {func_name} not found")
        except Exception as e:
            results["errors"].append(f"Failed to test functions: {e}")

    except Exception as e:
        results["status"] = "error"
        results["errors"].append(f"Validation failed: {e}")

    return results


def print_validation_results(results: dict[str, Any]) -> None:
    """Print formatted validation results."""
    print("\n🧪 Accordo Package Validation Results")
    print(f"Status: {results['status'].upper()}")
    print(f"Package: {results['package_name']}")
    print(f"Timestamp: {results.get('timestamp', 'N/A')}")

    if results.get("errors"):
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"  - {error}")

    if results.get("warnings"):
        print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
        for warning in results["warnings"]:
            print(f"  - {warning}")

    if results.get("key_functions"):
        print("\n🔧 Key Functions:")
        for func in results["key_functions"]:
            print(f"  - {func}")


if __name__ == "__main__":
    results = validate_accordo_package()
    print_validation_results(results)
