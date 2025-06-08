"""Pytest configuration and fixtures."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from src.dev_workflow_mcp.config import ServerConfig
from src.dev_workflow_mcp.models.workflow_state import (
    WorkflowItem,
    WorkflowState,
)
from src.dev_workflow_mcp.utils.cache_manager import WorkflowCacheManager


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_project_config_file(temp_dir: Path) -> Path:
    """Create a temporary project config file in .workflow-commander directory."""
    workflow_dir = temp_dir / ".workflow-commander"
    workflow_dir.mkdir(exist_ok=True)
    config_file = workflow_dir / "project_config.md"
    return config_file


@pytest.fixture
def sample_workflow_state() -> WorkflowState:
    """Create a sample WorkflowState for testing."""
    return WorkflowState(
        phase="INIT",
        status="READY",
        current_item="Test task",
        plan="Test plan",
        items=[
            WorkflowItem(id=1, description="First task", status="pending"),
            WorkflowItem(id=2, description="Second task", status="completed"),
        ],
        log=["Test log entry"],
        archive_log=["Archived log"],
    )


@pytest.fixture
def sample_workflow_items() -> list[WorkflowItem]:
    """Create sample workflow items for testing."""
    return [
        WorkflowItem(id=1, description="Task 1", status="pending"),
        WorkflowItem(id=2, description="Task 2", status="completed"),
        WorkflowItem(id=3, description="Task 3", status="pending"),
    ]


@pytest.fixture
def sample_workflow_state_content() -> str:
    """Create sample workflow state content for testing (session-based)."""
    return """# Workflow State
_Last updated: 2024-12-19_

## State
Phase: INIT  
Status: READY  
CurrentItem: Test task  

## Plan
Test plan content

## Rules
Test rules content

## Items
| id | description | status |
|----|-------------|--------|
| 1 | Test task | pending |

## Log
Test log content

## ArchiveLog
Test archive content
"""


@pytest.fixture
def valid_project_config_content() -> str:
    """Create valid project config file content for testing."""
    return """# Project Configuration

## Project Info
- **Name**: Test Project
- **Version**: 1.0.0
- **Description**: Test project for validation

## Dependencies
- Python 3.12+

## Test Commands
```bash
python -m pytest
```

## Changelog
- Initial version
"""


@pytest.fixture
def invalid_workflow_state_content() -> str:
    """Create invalid workflow state file content for testing."""
    return """# workflow_state.md
_Last updated: 2024-12-19_

## State
Phase: INIT  
Status: READY  
# Missing CurrentItem field

## Plan
Test plan content

# Missing required sections
"""


@pytest.fixture
def temp_cache_dir(temp_dir: Path) -> Path:
    """Create a temporary directory for cache testing."""
    cache_dir = temp_dir / "cache_test"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


@pytest.fixture
def mock_cache_manager(temp_cache_dir: Path) -> WorkflowCacheManager:
    """Create a mock cache manager for testing."""
    cache_manager = WorkflowCacheManager(
        db_path=str(temp_cache_dir),
        collection_name="test_workflow_states",
        embedding_model="all-MiniLM-L6-v2",
        max_results=10
    )
    return cache_manager


@pytest.fixture
def test_server_config(temp_dir: Path, temp_cache_dir: Path) -> ServerConfig:
    """Create a test server configuration with cache enabled."""
    return ServerConfig(
        repository_path=str(temp_dir),
        enable_local_state_file=True,
        local_state_file_format="MD",
        session_retention_hours=1,
        enable_session_archiving=True,
        enable_cache_mode=True,
        cache_db_path=str(temp_cache_dir),
        cache_collection_name="test_workflow_states",
        cache_embedding_model="all-MiniLM-L6-v2",
        cache_max_results=10
    )


@pytest.fixture
def test_workflow_yaml_content() -> str:
    """Create a simple test workflow YAML content."""
    return """name: "Test Integration Workflow"
description: "Simple workflow for testing MCP client integration"
goal: "Validate basic workflow functionality with semantic cache"

inputs:
  task_description:
    description: "Task to be executed"
    type: "string"
    required: true

workflow:
  root: "start_task"
  tree:
    start_task:
      type: "execute"
      name: "Start Task"
      description: "Initialize the test task"
      guidance: "Begin task execution and log initial state"
      acceptance_criteria:
        task_initialized: "Task has been properly initialized"
        initial_log_created: "Initial log entry has been created"
      next_allowed_nodes:
        - complete_task

    complete_task:
      type: "execute"
      name: "Complete Task"  
      description: "Finish the test task"
      guidance: "Complete task execution and finalize results"
      acceptance_criteria:
        task_completed: "Task execution has been completed"
        results_documented: "Task results have been documented"
      next_allowed_nodes: []
"""


@pytest.fixture
def test_workflows_dir(temp_dir: Path, test_workflow_yaml_content: str) -> Path:
    """Create a temporary workflows directory with test YAML files."""
    workflows_dir = temp_dir / ".workflow-commander" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test workflow file
    test_workflow_file = workflows_dir / "test-integration-workflow.yaml"
    test_workflow_file.write_text(test_workflow_yaml_content)
    
    return workflows_dir


@pytest.fixture
async def mcp_server_with_cache(test_server_config: ServerConfig, test_workflows_dir: Path):
    """Create MCP server instance with cache mode enabled for testing."""
    from fastmcp import FastMCP

    from src.dev_workflow_mcp.prompts.discovery_prompts import (
        register_discovery_prompts,
    )
    from src.dev_workflow_mcp.prompts.phase_prompts import register_phase_prompts
    
    # Create MCP server instance
    mcp = FastMCP("Test Workflow Server")
    
    # Register the tools with our test configuration
    register_phase_prompts(mcp, test_server_config)
    register_discovery_prompts(mcp, test_server_config)
    
    yield mcp
    
    # Cleanup
    # Note: In real integration tests, we would need to properly handle
    # server lifecycle, but for this fixture we just yield the configured server
