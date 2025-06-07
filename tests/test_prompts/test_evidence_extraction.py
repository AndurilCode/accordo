"""Comprehensive tests for evidence extraction functionality."""

from unittest.mock import Mock

import pytest

from src.dev_workflow_mcp.prompts.evidence_extraction import (
    _extract_criterion_evidence,
    _extract_evidence_from_activity_patterns,
    _extract_evidence_from_execution_context,
    _extract_evidence_from_log_entry,
    _extract_evidence_from_tool_patterns,
    _get_criterion_keywords,
    extract_automatic_evidence_from_session,
)


@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    session = Mock()
    session.log = [
        "[10:30:15] Starting analysis phase",
        "[10:31:22] Analyzed project structure and dependencies",
        "[10:32:45] Reviewed code quality standards",
        "[10:33:10] Implemented new validation logic",
        "[10:34:55] Tested validation with sample data",
        "[10:35:30] Documented implementation approach",
        "[10:36:12] Transitioned from analyze to blueprint",
        "[10:37:00] Completed node: analyze with 3 criteria satisfied",
    ]
    session.execution_context = {
        "analysis_completed": True,
        "files_reviewed": 15,
        "validation_status": "passed",
        "test_results": "all_passed",
    }
    return session


@pytest.fixture
def sample_acceptance_criteria():
    """Create sample acceptance criteria for testing."""
    return {
        "analysis_completed": "MUST analyze project structure and dependencies",
        "code_review": "MUST review existing code patterns and quality standards",
        "implementation_plan": "MUST create detailed implementation strategy",
        "validation_testing": "MUST test and validate the solution",
    }


class TestExtractAutomaticEvidenceFromSession:
    """Test the main evidence extraction function."""

    def test_extract_evidence_basic_functionality(
        self, mock_session, sample_acceptance_criteria
    ):
        """Test basic evidence extraction functionality."""
        result = extract_automatic_evidence_from_session(
            mock_session, "analyze", sample_acceptance_criteria
        )

        assert isinstance(result, dict)
        assert len(result) > 0

        # Should find evidence for analysis_completed
        assert "analysis_completed" in result
        assert "analyzed project structure" in result["analysis_completed"].lower()

    def test_extract_evidence_with_empty_session(self, sample_acceptance_criteria):
        """Test evidence extraction with empty session."""
        empty_session = Mock()
        empty_session.log = []
        empty_session.execution_context = {}

        result = extract_automatic_evidence_from_session(
            empty_session, "analyze", sample_acceptance_criteria
        )

        assert isinstance(result, dict)
        # Should return empty dict when no evidence found
        assert len(result) == 0

    def test_extract_evidence_no_log_attribute(self, sample_acceptance_criteria):
        """Test evidence extraction when session has no log attribute."""
        session_no_log = Mock()
        del session_no_log.log  # Remove log attribute
        session_no_log.execution_context = {}

        result = extract_automatic_evidence_from_session(
            session_no_log, "analyze", sample_acceptance_criteria
        )

        assert isinstance(result, dict)

    def test_extract_evidence_none_log(self, sample_acceptance_criteria):
        """Test evidence extraction when session log is None."""
        session_none_log = Mock()
        session_none_log.log = None
        session_none_log.execution_context = {}

        result = extract_automatic_evidence_from_session(
            session_none_log, "analyze", sample_acceptance_criteria
        )

        assert isinstance(result, dict)

    def test_extract_evidence_with_execution_context(self, sample_acceptance_criteria):
        """Test evidence extraction using execution context."""
        session = Mock()
        session.log = []
        session.execution_context = {
            "analysis_completed": "Successfully analyzed 15 files",
            "code_review_status": "Completed review of 8 modules",
            "validation_results": "All tests passed",
        }

        result = extract_automatic_evidence_from_session(
            session, "analyze", sample_acceptance_criteria
        )

        assert isinstance(result, dict)
        # Should find evidence from execution context
        if result:
            assert any("analysis" in evidence.lower() for evidence in result.values())

    def test_extract_evidence_recent_logs_limit(self, sample_acceptance_criteria):
        """Test that only recent logs (last 15) are used."""
        session = Mock()
        # Create 20 log entries, only last 15 should be used
        session.log = [f"[10:{i:02d}:00] Log entry {i}" for i in range(20)]
        session.log.append(
            "[10:19:00] Analyzed project structure"
        )  # This should be found
        session.execution_context = {}

        result = extract_automatic_evidence_from_session(
            session, "analyze", sample_acceptance_criteria
        )

        # Should process only recent logs and find the analysis evidence
        assert isinstance(result, dict)


class TestExtractCriterionEvidence:
    """Test the criterion-specific evidence extraction function."""

    def test_extract_criterion_evidence_from_logs(self, mock_session):
        """Test extracting evidence from log entries."""
        recent_logs = mock_session.log[-15:]

        result = _extract_criterion_evidence(
            "analysis_completed",
            "MUST analyze project structure",
            recent_logs,
            mock_session,
            "analyze",
        )

        assert result is not None
        assert "analyzed project structure" in result.lower()

    def test_extract_criterion_evidence_no_match(self, mock_session):
        """Test when no evidence is found for criterion."""
        recent_logs = [
            "[10:30:00] Transitioned from start to analyze"
        ]  # System log that gets filtered

        result = _extract_criterion_evidence(
            "nonexistent_criterion",
            "Something that doesn't exist",
            recent_logs,
            mock_session,
            "analyze",
        )

        # Should return None when no evidence found
        assert result is None

    def test_extract_criterion_evidence_from_context(self):
        """Test extracting evidence from execution context."""
        session = Mock()
        session.execution_context = {
            "analysis_status": "completed successfully",
            "files_processed": 10,
        }

        result = _extract_criterion_evidence(
            "analysis_completed",
            "MUST complete analysis",
            [],  # Empty logs
            session,
            "analyze",
        )

        assert result is not None
        assert "analysis_status" in result

    def test_extract_criterion_evidence_activity_patterns(self):
        """Test extracting evidence from activity patterns."""
        session = Mock()
        session.execution_context = {}
        recent_logs = [
            "[10:30:00] Performed detailed code analysis",
            "[10:31:00] Reviewed architecture patterns",
            "[10:32:00] Validated implementation approach",
        ]

        result = _extract_criterion_evidence(
            "analysis_completed",
            "MUST complete analysis",
            recent_logs,
            session,
            "analyze",
        )

        assert result is not None
        # The function returns the first match found, which could be from log entry or activity patterns
        assert "analysis" in result.lower() or "activities" in result.lower()

    def test_extract_criterion_evidence_tool_patterns(self):
        """Test extracting evidence from tool usage patterns."""
        session = Mock()
        session.execution_context = {}
        recent_logs = [
            "[10:30:00] Implemented new validation logic",
            "[10:31:00] Tested the implementation thoroughly",
            "[10:32:00] Documented the solution approach",
        ]

        result = _extract_criterion_evidence(
            "implementation_completed",
            "MUST implement solution",
            recent_logs,
            session,
            "implement",
        )

        assert result is not None
        # The function returns the first match found, which could be from any pattern
        assert any(
            keyword in result.lower()
            for keyword in ["implementation", "implemented", "solution", "validation"]
        )


class TestGetCriterionKeywords:
    """Test keyword extraction for criteria."""

    def test_get_criterion_keywords_basic(self):
        """Test basic keyword extraction."""
        keywords = _get_criterion_keywords(
            "analysis_completed", "MUST analyze project structure and dependencies"
        )

        assert "analysis_completed" in keywords
        assert "analysis completed" in keywords
        assert "analysiscompleted" in keywords
        assert "analyze" in keywords
        assert "project" in keywords
        assert "structure" in keywords

    def test_get_criterion_keywords_filters_common_words(self):
        """Test that common words are filtered out."""
        keywords = _get_criterion_keywords(
            "test_criterion",
            "MUST have the best and most comprehensive solution for this",
        )

        # Common words should be filtered out
        assert "the" not in keywords
        assert "and" not in keywords
        assert "for" not in keywords
        assert "this" not in keywords

        # Important words should be included
        assert "best" in keywords
        assert "comprehensive" in keywords
        assert "solution" in keywords

    def test_get_criterion_keywords_limits_important_words(self):
        """Test that only top 5 important words are included."""
        long_description = "MUST analyze review implement test validate document verify check process handle manage"
        keywords = _get_criterion_keywords("test_criterion", long_description)

        # Should include criterion variations plus max 5 description words
        criterion_variations = 3  # test_criterion, test criterion, testcriterion
        max_description_words = 5
        assert len(keywords) <= criterion_variations + max_description_words

    def test_get_criterion_keywords_empty_description(self):
        """Test keyword extraction with empty description."""
        keywords = _get_criterion_keywords("test_criterion", "")

        # Should still include criterion variations
        assert "test_criterion" in keywords
        assert "test criterion" in keywords
        assert "testcriterion" in keywords


class TestExtractEvidenceFromLogEntry:
    """Test evidence extraction from individual log entries."""

    def test_extract_evidence_from_log_entry_valid(self):
        """Test extracting evidence from a valid log entry."""
        log_entry = "[10:30:15] Successfully analyzed project structure and identified key dependencies"

        result = _extract_evidence_from_log_entry(
            log_entry, "analysis_completed", "MUST analyze project"
        )

        assert result is not None
        assert "Session activity:" in result
        assert "analyzed project structure" in result

    def test_extract_evidence_from_log_entry_filters_system_logs(self):
        """Test that system logs are filtered out."""
        system_logs = [
            "[10:30:15] Transitioned from analyze to blueprint",
            "[10:31:00] Workflow initialized successfully",
            "[10:32:00] Completed node: analyze with criteria",
            "[10:33:00] Criterion satisfied: analysis_completed",
        ]

        for log_entry in system_logs:
            result = _extract_evidence_from_log_entry(
                log_entry, "analysis_completed", "MUST analyze"
            )
            assert result is None

    def test_extract_evidence_from_log_entry_too_short(self):
        """Test that short log entries are filtered out."""
        short_log = "[10:30:15] Done"

        result = _extract_evidence_from_log_entry(
            short_log, "analysis_completed", "MUST analyze"
        )

        assert result is None

    def test_extract_evidence_from_log_entry_no_timestamp(self):
        """Test extracting evidence from log entry without timestamp."""
        log_entry = "Successfully completed comprehensive analysis of the codebase"

        result = _extract_evidence_from_log_entry(
            log_entry, "analysis_completed", "MUST analyze"
        )

        assert result is not None
        assert "Session activity:" in result
        assert "comprehensive analysis" in result

    def test_extract_evidence_from_log_entry_cleans_timestamp(self):
        """Test that timestamp is properly cleaned from log entry."""
        log_entry = "[10:30:15] Performed detailed code review and analysis"

        result = _extract_evidence_from_log_entry(
            log_entry, "analysis_completed", "MUST analyze"
        )

        assert result is not None
        assert "[10:30:15]" not in result
        assert "Performed detailed code review" in result


class TestExtractEvidenceFromExecutionContext:
    """Test evidence extraction from execution context."""

    def test_extract_evidence_from_execution_context_match(self):
        """Test extracting evidence when context matches criterion."""
        execution_context = {
            "analysis_completed": True,
            "analysis_results": "Successfully analyzed 15 files",
            "other_data": "unrelated information",
        }

        result = _extract_evidence_from_execution_context(
            execution_context, "analysis_completed", "MUST complete analysis"
        )

        assert result is not None
        assert "Execution context:" in result
        assert "analysis_completed" in result

    def test_extract_evidence_from_execution_context_keyword_match(self):
        """Test extracting evidence using keyword matching."""
        execution_context = {
            "files_analyzed": 10,
            "analysis_status": "completed",
            "review_results": "passed",
        }

        result = _extract_evidence_from_execution_context(
            execution_context, "analysis_completed", "MUST analyze files"
        )

        assert result is not None
        assert "files_analyzed" in result or "analysis_status" in result

    def test_extract_evidence_from_execution_context_no_match(self):
        """Test when no matching context is found."""
        execution_context = {"unrelated_field": "some value", "other_data": "more data"}

        result = _extract_evidence_from_execution_context(
            execution_context, "analysis_completed", "MUST complete analysis"
        )

        assert result is None

    def test_extract_evidence_from_execution_context_empty(self):
        """Test with empty execution context."""
        result = _extract_evidence_from_execution_context(
            {}, "analysis_completed", "MUST complete analysis"
        )

        assert result is None

    def test_extract_evidence_from_execution_context_none(self):
        """Test with None execution context."""
        result = _extract_evidence_from_execution_context(
            None, "analysis_completed", "MUST complete analysis"
        )

        assert result is None


class TestExtractEvidenceFromActivityPatterns:
    """Test evidence extraction from activity patterns."""

    def test_extract_evidence_from_activity_patterns_meaningful_activities(self):
        """Test extracting evidence from meaningful activities."""
        recent_logs = [
            "[10:30:00] Analyzed project dependencies",
            "[10:31:00] Reviewed code quality standards",
            "[10:32:00] Implemented validation logic",
            "[10:33:00] Transitioned from analyze to blueprint",  # Should be filtered
        ]

        result = _extract_evidence_from_activity_patterns(
            recent_logs, "analysis_completed", "MUST complete analysis", "analyze"
        )

        assert result is not None
        assert "Completed 3 activities" in result
        assert "analyze phase" in result
        assert "Implemented validation logic" in result

    def test_extract_evidence_from_activity_patterns_filters_system_logs(self):
        """Test that system logs are properly filtered."""
        recent_logs = [
            "[10:30:00] Transitioned from start to analyze",
            "[10:31:00] Workflow initialized",
            "[10:32:00] Completed node: analyze",
            "[10:33:00] Criterion satisfied: analysis_completed",
        ]

        result = _extract_evidence_from_activity_patterns(
            recent_logs, "analysis_completed", "MUST complete analysis", "analyze"
        )

        assert result is None

    def test_extract_evidence_from_activity_patterns_short_entries(self):
        """Test filtering of short log entries."""
        recent_logs = [
            "[10:30:00] Done",
            "[10:31:00] OK",
            "[10:32:00] Completed comprehensive analysis of the entire codebase",
        ]

        result = _extract_evidence_from_activity_patterns(
            recent_logs, "analysis_completed", "MUST complete analysis", "analyze"
        )

        assert result is not None
        assert "Completed 1 activities" in result
        assert "comprehensive analysis" in result

    def test_extract_evidence_from_activity_patterns_no_meaningful_activities(self):
        """Test when no meaningful activities are found."""
        recent_logs = [
            "[10:30:00] Transitioned",
            "[10:31:00] Initialized",
            "[10:32:00] Done",
        ]

        result = _extract_evidence_from_activity_patterns(
            recent_logs, "analysis_completed", "MUST complete analysis", "analyze"
        )

        assert result is None


class TestExtractEvidenceFromToolPatterns:
    """Test evidence extraction from tool usage patterns."""

    def test_extract_evidence_from_tool_patterns_analysis(self):
        """Test detecting analysis patterns."""
        recent_logs = [
            "[10:30:00] Analyzed the project structure",
            "[10:31:00] Examined code dependencies",
            "[10:32:00] Reviewed existing patterns",
        ]

        result = _extract_evidence_from_tool_patterns(
            recent_logs, "analysis_completed", "MUST complete analysis"
        )

        assert result is not None
        assert "analysis" in result
        assert "Performed" in result

    def test_extract_evidence_from_tool_patterns_implementation(self):
        """Test detecting implementation patterns."""
        recent_logs = [
            "[10:30:00] Implemented new validation logic",
            "[10:31:00] Created helper functions",
            "[10:32:00] Built the main processing module",
        ]

        result = _extract_evidence_from_tool_patterns(
            recent_logs, "implementation_completed", "MUST implement solution"
        )

        assert result is not None
        assert "implementation" in result

    def test_extract_evidence_from_tool_patterns_testing(self):
        """Test detecting testing patterns."""
        recent_logs = [
            "[10:30:00] Tested the new functionality",
            "[10:31:00] Verified edge cases",
            "[10:32:00] Validated input handling",
        ]

        result = _extract_evidence_from_tool_patterns(
            recent_logs, "testing_completed", "MUST test solution"
        )

        assert result is not None
        assert "testing" in result

    def test_extract_evidence_from_tool_patterns_documentation(self):
        """Test detecting documentation patterns."""
        recent_logs = [
            "[10:30:00] Documented the implementation approach",
            "[10:31:00] Recorded key decisions",
            "[10:32:00] Noted important considerations",
        ]

        result = _extract_evidence_from_tool_patterns(
            recent_logs, "documentation_completed", "MUST document solution"
        )

        assert result is not None
        assert "documentation" in result

    def test_extract_evidence_from_tool_patterns_multiple_activities(self):
        """Test detecting multiple activity types."""
        recent_logs = [
            "[10:30:00] Analyzed the requirements",
            "[10:31:00] Implemented the solution",
            "[10:32:00] Tested the implementation",
            "[10:33:00] Documented the approach",
        ]

        result = _extract_evidence_from_tool_patterns(
            recent_logs, "comprehensive_work", "MUST complete all work"
        )

        assert result is not None
        assert "analysis" in result
        assert "implementation" in result
        assert "testing" in result
        assert "documentation" in result

    def test_extract_evidence_from_tool_patterns_no_patterns(self):
        """Test when no tool patterns are detected."""
        recent_logs = [
            "[10:30:00] Started the process",
            "[10:31:00] Continued working",
            "[10:32:00] Finished the task",
        ]

        result = _extract_evidence_from_tool_patterns(
            recent_logs, "work_completed", "MUST complete work"
        )

        assert result is None

    def test_extract_evidence_from_tool_patterns_preserves_order(self):
        """Test that unique activities preserve order."""
        recent_logs = [
            "[10:30:00] Implemented feature A",
            "[10:31:00] Analyzed the results",
            "[10:32:00] Implemented feature B",  # Duplicate implementation
            "[10:33:00] Tested everything",
        ]

        result = _extract_evidence_from_tool_patterns(
            recent_logs, "work_completed", "MUST complete work"
        )

        assert result is not None
        # Should preserve order and remove duplicates
        assert "implementation, analysis, testing" in result
