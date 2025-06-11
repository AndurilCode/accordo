"""Tests for markdown generator functionality."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from src.accordo_workflow_mcp.models.workflow_state import (
    WorkflowItem,
    WorkflowState,
)
from src.accordo_workflow_mcp.utils.markdown_generator import (
    export_session_report,
    format_workflow_state_for_display,
    generate_summary_markdown,
    generate_workflow_markdown,
)


class TestMarkdownGenerator:
    """Test markdown generator functions."""

    @pytest.fixture
    def mock_workflow_state(self):
        """Create a mock WorkflowState for testing."""
        state = Mock(spec=WorkflowState)
        state.client_id = "test_client"
        state.phase = "BLUEPRINT"
        state.status = "RUNNING"
        state.current_item = "Test task"
        state.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        state.last_updated = datetime(2024, 1, 1, 13, 30, 0, tzinfo=UTC)
        state.log = "Sample log content"
        state.archive_log = "Sample archive log"

        # Mock items
        completed_item = Mock(spec=WorkflowItem)
        completed_item.description = "Completed task"
        completed_item.status = "completed"

        pending_item = Mock(spec=WorkflowItem)
        pending_item.description = "Pending task"
        pending_item.status = "pending"

        state.items = [completed_item, pending_item]

        # Mock to_markdown method
        state.to_markdown.return_value = """📊 **DYNAMIC WORKFLOW STATE**

**Workflow:** Test Workflow
**Current Node:** test_node 
**Status:** RUNNING
**→ Next:** End of workflow

**Current Goal:** Loading...

**Progress:** test_node

---

## Detailed Session State
_Last updated: 2024-01-01_

### Plan
Test plan content

### ArchiveLog
Sample archive content"""

        return state

    def test_generate_workflow_markdown(self, mock_workflow_state):
        """Test generate_workflow_markdown function."""
        result = generate_workflow_markdown(mock_workflow_state)

        # Verify the function delegates to state.to_markdown()
        mock_workflow_state.to_markdown.assert_called_once()
        assert result == mock_workflow_state.to_markdown.return_value
        assert "📊 **DYNAMIC WORKFLOW STATE**" in result

    def test_format_workflow_state_for_display_without_metadata(
        self, mock_workflow_state
    ):
        """Test format_workflow_state_for_display without metadata."""
        result = format_workflow_state_for_display(
            mock_workflow_state, include_metadata=False
        )

        # Should just return the base markdown
        mock_workflow_state.to_markdown.assert_called_once()
        assert result == mock_workflow_state.to_markdown.return_value
        assert "## Metadata" not in result

    def test_format_workflow_state_for_display_with_metadata(self, mock_workflow_state):
        """Test format_workflow_state_for_display with metadata."""
        result = format_workflow_state_for_display(
            mock_workflow_state, include_metadata=True
        )

        # Should include metadata section
        assert "## Metadata" in result
        assert "test_client" in result
        assert "2024-01-01 12:00:00" in result  # Created date
        assert "2024-01-01 13:30:00" in result  # Last updated date
        assert "Items Count**: 2" in result
        assert "Log Length**: 18" in result  # Length of "Sample log content"
        assert "Archive Log Length**: 18" in result  # Length of "Sample archive log"

    def test_format_workflow_state_for_display_with_metadata_no_archivelog(
        self, mock_workflow_state
    ):
        """Test format_workflow_state_for_display with metadata when no ArchiveLog section exists."""
        # Mock to_markdown to return content without ArchiveLog section
        mock_workflow_state.to_markdown.return_value = """📊 **DYNAMIC WORKFLOW STATE**

**Workflow:** Test Workflow
**Status:** RUNNING"""

        result = format_workflow_state_for_display(
            mock_workflow_state, include_metadata=True
        )

        # Should append metadata at the end
        assert "## Metadata" in result
        assert "- **Client ID**: test_client" in result
        assert "- **Created**: 2024-01-01 12:00:00" in result
        assert "- **Last Updated**: 2024-01-01 13:30:00" in result
        assert "- **Items Count**: 2" in result
        assert "- **Log Length**: 18 characters" in result
        assert "- **Archive Log Length**: 18 characters" in result

    def test_generate_summary_markdown_with_items(self, mock_workflow_state):
        """Test generate_summary_markdown with items."""
        result = generate_summary_markdown(mock_workflow_state)

        assert "# Workflow Summary" in result
        assert "**Client**: test_client" in result
        assert "**Phase**: BLUEPRINT" in result
        assert "**Status**: RUNNING" in result
        assert "**Current Item**: Test task" in result

        # Progress section
        assert "**Total Items**: 2" in result
        assert "**Completed**: 1" in result
        assert "**Pending**: 1" in result
        assert "**Progress**: 1/2 (50.0%)" in result

        # Recent activity
        assert "Sample log content" in result

        # Next steps
        assert "Next item: Pending task" in result

    def test_generate_summary_markdown_no_items(self, mock_workflow_state):
        """Test generate_summary_markdown with no items."""
        mock_workflow_state.items = []

        result = generate_summary_markdown(mock_workflow_state)

        assert "**Total Items**: 0" in result
        assert "**Completed**: 0" in result
        assert "**Pending**: 0" in result
        assert "**Progress**: 0/0 (0.0%)" in result
        assert "All items completed" in result

    def test_generate_summary_markdown_no_current_item(self, mock_workflow_state):
        """Test generate_summary_markdown with no current item."""
        mock_workflow_state.current_item = None

        result = generate_summary_markdown(mock_workflow_state)

        assert "**Current Item**: None" in result

    def test_generate_summary_markdown_no_log(self, mock_workflow_state):
        """Test generate_summary_markdown with no log."""
        mock_workflow_state.log = ""

        result = generate_summary_markdown(mock_workflow_state)

        assert "No recent activity" in result

    def test_generate_summary_markdown_long_log(self, mock_workflow_state):
        """Test generate_summary_markdown with long log (should truncate)."""
        # Create a log longer than 500 characters
        long_log = "x" * 600
        mock_workflow_state.log = long_log

        result = generate_summary_markdown(mock_workflow_state)

        # Should only include last 500 characters
        assert long_log[-500:] in result
        assert (
            len(result.split("## Recent Activity")[1].split("## Next Steps")[0].strip())
            <= 520
        )  # Some buffer for formatting

    def test_generate_summary_markdown_all_completed_items(self, mock_workflow_state):
        """Test generate_summary_markdown when all items are completed."""
        # Mock all items as completed
        completed_item1 = Mock(spec=WorkflowItem)
        completed_item1.description = "Completed task 1"
        completed_item1.status = "completed"

        completed_item2 = Mock(spec=WorkflowItem)
        completed_item2.description = "Completed task 2"
        completed_item2.status = "completed"

        mock_workflow_state.items = [completed_item1, completed_item2]

        result = generate_summary_markdown(mock_workflow_state)

        assert "**Progress**: 2/2 (100.0%)" in result
        assert "All items completed" in result

    def test_export_session_report(self, mock_workflow_state):
        """Test export_session_report function."""
        result = export_session_report(mock_workflow_state)

        # Should include header with timestamp
        assert "# Workflow Session Report" in result
        assert "**Generated**: 2024-01-01 13:30:00" in result

        # Should include both workflow markdown and summary
        assert "📊 **DYNAMIC WORKFLOW STATE**" in result  # From workflow markdown
        assert "# Workflow Summary" in result  # From summary markdown

        # Should have separator
        assert "---" in result

    def test_format_workflow_state_metadata_calculation(self, mock_workflow_state):
        """Test metadata calculations in format_workflow_state_for_display."""
        # Test with specific log and archive_log lengths
        mock_workflow_state.log = "test log"  # 8 characters
        mock_workflow_state.archive_log = "archive"  # 7 characters
        mock_workflow_state.items = [
            Mock(spec=WorkflowItem),
            Mock(spec=WorkflowItem),
            Mock(spec=WorkflowItem),
        ]  # 3 items

        result = format_workflow_state_for_display(
            mock_workflow_state, include_metadata=True
        )

        assert "Items Count**: 3" in result
        assert "Log Length**: 8" in result
        assert "Archive Log Length**: 7" in result
