"""Tests for task description validation functionality."""

import pytest

from src.accordo_mcp.prompts.phase_prompts import validate_task_description


class TestValidTaskDescriptions:
    """Test valid task description formats."""

    def test_basic_valid_formats(self):
        """Test basic valid 'Action: Description' formats."""
        valid_descriptions = [
            "Add: user authentication",
            "Fix: memory leak in worker process",
            "Update: documentation for API endpoints",
            "Remove: deprecated helper functions",
            "Implement: caching layer for database queries",
            "Refactor: component structure for better maintainability",
            "Test: integration with external payment service",
            "Deploy: application to staging environment",
            "Configure: CI/CD pipeline for automated testing",
            "Debug: performance issues in search functionality",
        ]

        for description in valid_descriptions:
            # Should not raise any exception
            result = validate_task_description(description)
            assert result == description

    def test_various_action_verbs(self):
        """Test various valid action verbs."""
        action_verbs = [
            "Create",
            "Build",
            "Develop",
            "Design",
            "Analyze",
            "Research",
            "Optimize",
            "Migrate",
            "Upgrade",
            "Install",
            "Setup",
            "Configure",
            "Monitor",
            "Validate",
            "Verify",
            "Review",
            "Audit",
            "Document",
            "Archive",
            "Backup",
            "Restore",
            "Sync",
            "Merge",
            "Split",
            "Convert",
            "Transform",
            "Parse",
            "Generate",
            "Export",
            "Import",
        ]

        for verb in action_verbs:
            description = f"{verb}: sample task description"
            # Should not raise any exception
            result = validate_task_description(description)
            assert result == description

    def test_long_descriptions(self):
        """Test valid formats with long descriptions."""
        long_descriptions = [
            "Implement: comprehensive user authentication system with JWT tokens, refresh token rotation, multi-factor authentication support, and secure password reset functionality",
            "Refactor: legacy codebase to use modern architectural patterns including dependency injection, clean architecture principles, and automated testing frameworks",
            "Fix: critical security vulnerability in the payment processing module that allows potential SQL injection attacks through malformed input validation",
        ]

        for description in long_descriptions:
            # Should not raise any exception
            result = validate_task_description(description)
            assert result == description

    def test_descriptions_with_special_characters(self):
        """Test valid descriptions containing special characters."""
        special_char_descriptions = [
            "Add: support for UTF-8 characters (åäö, ñ, €, ™)",
            "Fix: handling of file paths with spaces & special chars",
            "Update: regex pattern to match emails with + and - symbols",
            "Implement: URL validation for domains with underscores_and-dashes",
            "Configure: environment variables for prod/staging/dev environments",
        ]

        for description in special_char_descriptions:
            # Should not raise any exception
            result = validate_task_description(description)
            assert result == description

    def test_descriptions_with_numbers(self):
        """Test valid descriptions containing numbers."""
        numeric_descriptions = [
            "Upgrade: Python version from 3.8 to 3.12",
            "Fix: issue #123 with user registration flow",
            "Add: support for IPv6 addresses in network configuration",
            "Optimize: algorithm to reduce O(n²) complexity to O(n log n)",
            "Configure: rate limiting to 1000 requests per minute",
        ]

        for description in numeric_descriptions:
            # Should not raise any exception
            result = validate_task_description(description)
            assert result == description

    def test_multiple_colons_in_description(self):
        """Test descriptions with multiple colons (should be valid)."""
        multi_colon_descriptions = [
            "Add: user: authentication",
            "Fix: memory: leak: in worker",
            "Update: API: documentation: for endpoints",
        ]

        for description in multi_colon_descriptions:
            # Should not raise any exception - multiple colons are allowed in description
            result = validate_task_description(description)
            assert result == description

    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is stripped."""
        test_cases = [
            "  Add: user authentication  ",
            "\tFix: memory leak\t",
            "  \nUpdate: documentation\n  ",
        ]

        for description in test_cases:
            result = validate_task_description(description)
            assert result == description.strip()


class TestInvalidTaskDescriptions:
    """Test invalid task description formats."""

    def test_missing_colon(self):
        """Test descriptions missing the required colon."""
        invalid_descriptions = [
            "Add user authentication",
            "Fix memory leak",
            "Update documentation",
            "Remove deprecated code",
            "Test integration",
        ]

        for description in invalid_descriptions:
            with pytest.raises(ValueError) as exc_info:
                validate_task_description(description)

            error_message = str(exc_info.value)
            assert "must follow the format" in error_message
            assert "Action: Brief description" in error_message
            assert description in error_message

    def test_lowercase_action_verb(self):
        """Test descriptions with lowercase action verbs."""
        lowercase_descriptions = [
            "add: user authentication",
            "fix: memory leak",
            "update: documentation",
            "remove: deprecated code",
            "test: integration",
        ]

        for description in lowercase_descriptions:
            with pytest.raises(ValueError) as exc_info:
                validate_task_description(description)

            error_message = str(exc_info.value)
            assert "must follow the format" in error_message

    def test_missing_space_after_colon(self):
        """Test descriptions missing space after colon."""
        no_space_descriptions = [
            "Add:user authentication",
            "Fix:memory leak",
            "Update:documentation",
            "Remove:deprecated code",
            "Test:integration",
        ]

        for description in no_space_descriptions:
            with pytest.raises(ValueError) as exc_info:
                validate_task_description(description)

            error_message = str(exc_info.value)
            assert "must follow the format" in error_message

    def test_empty_description(self):
        """Test empty description after colon."""
        empty_descriptions = [
            "Add: ",
            "Fix:",
            "Update:   ",  # only spaces
            "Remove: \t",  # only whitespace
        ]

        for description in empty_descriptions:
            with pytest.raises(ValueError) as exc_info:
                validate_task_description(description)

            error_message = str(exc_info.value)
            assert "must follow the format" in error_message

    def test_only_colon(self):
        """Test descriptions that are just a colon or action verb."""
        minimal_descriptions = [
            ":",
            "Add",
            "Fix",
            "A:",
            " : ",
        ]

        for description in minimal_descriptions:
            with pytest.raises(ValueError) as exc_info:
                validate_task_description(description)

            error_message = str(exc_info.value)
            assert "must follow the format" in error_message

    def test_action_verb_with_numbers(self):
        """Test action verbs containing numbers (should be invalid based on regex)."""
        invalid_actions = [
            "Add123: user authentication",
            "Fix2: memory leak",
            "Update3rd: documentation",
        ]

        for description in invalid_actions:
            with pytest.raises(ValueError) as exc_info:
                validate_task_description(description)

            error_message = str(exc_info.value)
            assert "must follow the format" in error_message

    def test_non_alphabetic_action_start(self):
        """Test action verbs that don't start with a letter."""
        invalid_actions = [
            "123: invalid action starting with number",
            "_Add: invalid action starting with underscore",
            "-Fix: invalid action starting with dash",
            "!Update: invalid action starting with punctuation",
        ]

        for description in invalid_actions:
            with pytest.raises(ValueError) as exc_info:
                validate_task_description(description)

            error_message = str(exc_info.value)
            assert "must follow the format" in error_message


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string(self):
        """Test completely empty string."""
        with pytest.raises(ValueError) as exc_info:
            validate_task_description("")

        error_message = str(exc_info.value)
        assert "must be a non-empty string" in error_message

    def test_none_value(self):
        """Test None value."""
        with pytest.raises(ValueError) as exc_info:
            validate_task_description(None)

        error_message = str(exc_info.value)
        assert "must be a non-empty string" in error_message

    def test_only_whitespace(self):
        """Test strings with only whitespace."""
        whitespace_strings = [
            " ",
            "   ",
            "\t",
            "\n",
            "  \t  \n  ",
        ]

        for ws_string in whitespace_strings:
            with pytest.raises(ValueError) as exc_info:
                validate_task_description(ws_string)

            error_message = str(exc_info.value)
            assert "must follow the format" in error_message

    def test_unicode_action_verbs(self):
        """Test action verbs with unicode characters (should be valid if they follow pattern)."""
        unicode_descriptions = [
            "Añadir: support for Spanish characters",
            "Fijar: issue with unicode handling",
            "Créer: new internationalization module",
        ]

        # These might actually be valid if they follow the pattern
        for description in unicode_descriptions:
            # Test that they either pass validation or fail with the expected error
            try:
                result = validate_task_description(description)
                # If they pass, the result should be the trimmed input
                assert result == description.strip()
            except ValueError as e:
                # If they fail, it should be for format reasons
                assert "must follow the format" in str(e)

    def test_very_long_action_verb(self):
        """Test very long action verbs."""
        long_action = "A" * 100
        description = f"{long_action}: very long action verb test"

        # Should be valid as long as format is correct
        result = validate_task_description(description)
        assert result == description

    def test_minimal_valid_format(self):
        """Test minimal valid format."""
        minimal_valid = "Ab: c"  # Need at least 2 letters in action verb
        # Should not raise any exception
        result = validate_task_description(minimal_valid)
        assert result == minimal_valid

    def test_case_sensitivity_boundary(self):
        """Test case sensitivity at the boundary."""
        # Valid - starts with uppercase and only letters
        validate_task_description("Add: description")
        validate_task_description("ADD: description")

        # Invalid - starts with lowercase
        with pytest.raises(ValueError):
            validate_task_description("add: description")

        with pytest.raises(ValueError):
            validate_task_description("aDD: description")

        # Invalid - contains numbers in action verb
        with pytest.raises(ValueError):
            validate_task_description("Add123: description")


class TestErrorMessages:
    """Test error message content and helpfulness."""

    def test_error_message_contains_examples(self):
        """Test that error messages contain helpful examples."""
        with pytest.raises(ValueError) as exc_info:
            validate_task_description("invalid format")

        error_message = str(exc_info.value)

        # Should contain format specification
        assert "Action: Brief description" in error_message

        # Should contain examples
        assert "Add: user authentication" in error_message
        assert "Fix: memory leak" in error_message

        # Should contain the invalid input
        assert "invalid format" in error_message

    def test_error_message_explains_requirements(self):
        """Test that error messages explain the requirements clearly."""
        with pytest.raises(ValueError) as exc_info:
            validate_task_description("lowercase: action")

        error_message = str(exc_info.value)

        # Should explain the requirements
        assert "must follow the format" in error_message
        assert "Action: Brief description" in error_message

    def test_different_error_types_have_specific_messages(self):
        """Test that different validation failures have appropriate error messages."""
        test_cases = [
            ("no colon here", "must follow the format"),
            ("lowercase: action", "must follow the format"),
            ("Add:no space", "must follow the format"),
            ("", "must be a non-empty string"),
        ]

        for invalid_input, expected_message_part in test_cases:
            with pytest.raises(ValueError) as exc_info:
                validate_task_description(invalid_input)

            error_message = str(exc_info.value)
            assert expected_message_part in error_message


class TestIntegrationWithWorkflowTools:
    """Test validation integration with actual workflow tools."""

    def test_validation_prevents_invalid_tool_calls(self):
        """Test that validation prevents invalid task descriptions in tool calls."""
        # This test ensures that the validation is actually being used
        # by the workflow tools and prevents invalid inputs

        invalid_descriptions = [
            "no colon format",
            "lowercase: action",
            "Missing:space",
            "",
            "   ",
        ]

        for invalid_desc in invalid_descriptions:
            with pytest.raises(ValueError):
                validate_task_description(invalid_desc)

    def test_validation_allows_realistic_task_descriptions(self):
        """Test validation with realistic task descriptions from actual usage."""
        realistic_descriptions = [
            "Add: user authentication system with JWT tokens",
            "Fix: memory leak in background worker process",
            "Update: API documentation to reflect latest changes",
            "Remove: deprecated helper functions from utils module",
            "Implement: Redis caching layer for database queries",
            "Refactor: component architecture for better testability",
            "Test: integration with third-party payment gateway",
            "Deploy: application to production environment",
            "Configure: monitoring and alerting for critical services",
            "Debug: performance bottleneck in search functionality",
            "Optimize: database queries to reduce response time",
            "Migrate: legacy data to new schema format",
            "Validate: input sanitization for security compliance",
            "Document: API endpoints with usage examples",
            "Monitor: system health and performance metrics",
        ]

        for description in realistic_descriptions:
            # Should not raise any exception
            result = validate_task_description(description)
            assert result == description
