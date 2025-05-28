"""Pytest configuration and fixtures."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from src.dev_workflow_mcp.models.workflow_state import (
    WorkflowItem,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_workflow_file(temp_dir: Path) -> Path:
    """Create a temporary workflow state file."""
    workflow_file = temp_dir / "workflow_state.md"
    return workflow_file


@pytest.fixture
def temp_project_config_file(temp_dir: Path) -> Path:
    """Create a temporary project config file."""
    config_file = temp_dir / "project_config.md"
    return config_file


@pytest.fixture
def sample_workflow_state() -> WorkflowState:
    """Create a sample WorkflowState for testing."""
    return WorkflowState(
        phase=WorkflowPhase.INIT,
        status=WorkflowStatus.READY,
        current_item="Test task",
        plan="Test plan",
        items=[
            WorkflowItem(id=1, description="First task", status="pending"),
            WorkflowItem(id=2, description="Second task", status="completed"),
        ],
        log="Test log entry",
        archive_log="Archived log",
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
def valid_workflow_state_content() -> str:
    """Create valid workflow state file content for testing."""
    return """# workflow_state.md
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
