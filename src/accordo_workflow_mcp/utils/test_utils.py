"""Test utilities for validating accordo package functionality."""

from typing import Dict, Any, List
import importlib


def validate_accordo_package() -> Dict[str, Any]:
    """
    Validate accordo package functionality by testing key imports and components.
    
    Returns:
        Dict containing validation results with status and details
    """
    results = {
        "status": "success",
        "package_name": "accordo-workflow-mcp",
        "validated_modules": [],
        "errors": [],
        "timestamp": None
    }
    
    # Core modules to validate
    core_modules = [
        "accordo_workflow_mcp.server",
        "accordo_workflow_mcp.models.workflow_state", 
        "accordo_workflow_mcp.utils.session_manager",
        "accordo_workflow_mcp.prompts.phase_prompts",
        "accordo_workflow_mcp.services.config_service"
    ]
    
    try:
        from datetime import datetime, timezone
        results["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Test core module imports
        for module_name in core_modules:
            try:
                module = importlib.import_module(module_name)
                results["validated_modules"].append({
                    "name": module_name,
                    "status": "success",
                    "has_main": hasattr(module, "main") if "server" in module_name else None
                })
            except ImportError as e:
                results["errors"].append(f"Failed to import {module_name}: {e}")
                results["status"] = "partial"
        
        # Test if we can access key functions  
        try:
            from accordo_workflow_mcp.utils import session_manager
            if hasattr(session_manager, "get_session"):
                results["key_functions"] = ["get_session: available"]
        except Exception as e:
            results["errors"].append(f"Key function import failed: {e}")
            
    except Exception as e:
        results["status"] = "error"
        results["errors"].append(f"Validation failed: {e}")
    
    return results


def print_validation_results(results: Dict[str, Any]) -> None:
    """Print formatted validation results."""
    print(f"\n🧪 Accordo Package Validation Results")
    print(f"Status: {results['status'].upper()}")
    print(f"Package: {results['package_name']}")
    print(f"Timestamp: {results.get('timestamp', 'N/A')}")
    
    if results["validated_modules"]:
        print(f"\n✅ Validated Modules ({len(results['validated_modules'])}):")
        for module in results["validated_modules"]:
            print(f"  - {module['name']}: {module['status']}")
    
    if results.get("key_functions"):
        print(f"\n🔧 Key Functions:")
        for func in results["key_functions"]:
            print(f"  - {func}")
    
    if results["errors"]:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"  - {error}")
    
    print()


if __name__ == "__main__":
    """Run validation when script is executed directly."""
    validation_results = validate_accordo_package()
    print_validation_results(validation_results) 