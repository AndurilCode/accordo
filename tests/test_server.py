"""Tests for the main server module."""

import sys
from unittest.mock import Mock, call, patch

import pytest

from src.accordo_workflow_mcp.server import create_arg_parser, main


class TestArgumentParsing:
    """Test command-line argument parsing."""

    def test_create_arg_parser(self):
        """Test that argument parser is created correctly."""
        parser = create_arg_parser()

        # Test help message
        help_text = parser.format_help()
        assert "Development Workflow MCP Server" in help_text
        assert "--repository-path" in help_text

    def test_arg_parser_default_values(self):
        """Test argument parser with default values."""
        parser = create_arg_parser()
        args = parser.parse_args([])

        assert args.repository_path is None

    def test_arg_parser_with_repository_path(self):
        """Test argument parser with repository path specified."""
        parser = create_arg_parser()
        args = parser.parse_args(["--repository-path", "/some/path"])

        assert args.repository_path == "/some/path"


class TestMainFunction:
    """Test main function."""

    @patch("src.accordo_workflow_mcp.server.FastMCP")
    @patch("src.accordo_workflow_mcp.server.initialize_configuration_service")
    @patch("src.accordo_workflow_mcp.server.register_phase_prompts")
    @patch("src.accordo_workflow_mcp.server.register_discovery_prompts")
    def test_main_with_default_args(
        self,
        mock_register_discovery,
        mock_register_phase,
        mock_init_config,
        mock_fastmcp,
    ):
        """Test main function with default arguments."""
        # Mock FastMCP instance
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Mock configuration service
        mock_config_service = Mock()
        mock_legacy_config = Mock()
        mock_config_service.to_legacy_server_config.return_value = mock_legacy_config
        mock_init_config.return_value = mock_config_service

        # Mock sys.argv to provide no arguments
        test_args = ["server.py"]
        with patch.object(sys, "argv", test_args):
            result = main()

        # Verify configuration service was initialized
        mock_init_config.assert_called_once()

        # Verify FastMCP was created
        mock_fastmcp.assert_called_once_with("Development Workflow")

        # Verify registration functions were called with legacy config
        mock_register_phase.assert_called_once_with(
            mock_mcp_instance, mock_legacy_config
        )
        mock_register_discovery.assert_called_once_with(
            mock_mcp_instance, mock_legacy_config
        )

        # Verify mcp.run was called
        mock_mcp_instance.run.assert_called_once_with(transport="stdio")

        # Verify successful return
        assert result == 0

    @patch("src.accordo_workflow_mcp.server.FastMCP")
    @patch("src.accordo_workflow_mcp.server.initialize_configuration_service")
    @patch("src.accordo_workflow_mcp.server.register_phase_prompts")
    @patch("src.accordo_workflow_mcp.server.register_discovery_prompts")
    def test_main_with_repository_path(
        self,
        mock_register_discovery,
        mock_register_phase,
        mock_init_config,
        mock_fastmcp,
    ):
        """Test main function with repository path specified."""
        # Mock FastMCP instance
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Mock configuration service
        mock_config_service = Mock()
        mock_legacy_config = Mock()
        mock_config_service.to_legacy_server_config.return_value = mock_legacy_config
        mock_init_config.return_value = mock_config_service

        # Mock sys.argv to provide repository path
        test_args = ["server.py", "--repository-path", "/test/path"]
        with patch.object(sys, "argv", test_args):
            result = main()

        # Verify configuration service was initialized
        mock_init_config.assert_called_once()

        # Verify other calls
        mock_fastmcp.assert_called_once_with("Development Workflow")
        mock_register_phase.assert_called_once_with(
            mock_mcp_instance, mock_legacy_config
        )
        mock_register_discovery.assert_called_once_with(
            mock_mcp_instance, mock_legacy_config
        )
        mock_mcp_instance.run.assert_called_once_with(transport="stdio")

        assert result == 0

    @patch("src.accordo_workflow_mcp.server.initialize_configuration_service")
    @patch("builtins.print")
    def test_main_with_invalid_repository_path(self, mock_print, mock_init_config):
        """Test main function with invalid repository path."""
        # Mock configuration service to raise validation error
        from src.accordo_workflow_mcp.services.config_service import (
            ConfigurationValidationError,
        )

        mock_init_config.side_effect = ConfigurationValidationError(
            "Configuration validation failed: ['Repository path does not exist: /invalid/path']"
        )

        # Mock sys.argv to provide invalid path
        test_args = ["server.py", "--repository-path", "/invalid/path"]
        with patch.object(sys, "argv", test_args):
            result = main()

        # Verify error handling
        mock_init_config.assert_called_once()

        # Verify both deprecation warning and error message are printed
        expected_calls = [
            call(
                "⚠️  WARNING: --repository-path is deprecated. Use --global or --local instead."
            ),
            call(
                "Error: Configuration validation failed: ['Repository path does not exist: /invalid/path']"
            ),
        ]
        mock_print.assert_has_calls(expected_calls)

        # Verify error return code
        assert result == 1


class TestServerIntegration:
    """Test server integration and tool registration."""

    @pytest.mark.asyncio
    async def test_server_creation_and_tool_registration(self):
        """Test that server can be created and tools registered correctly."""
        from fastmcp import FastMCP

        from src.accordo_workflow_mcp.config import ServerConfig
        from src.accordo_workflow_mcp.prompts.discovery_prompts import (
            register_discovery_prompts,
        )
        from src.accordo_workflow_mcp.prompts.phase_prompts import (
            register_phase_prompts,
        )

        # Create a test config with current directory
        config = ServerConfig(".")

        # Create MCP server
        mcp = FastMCP("Test Development Workflow")

        # Register tools with config
        register_phase_prompts(mcp, config)
        register_discovery_prompts(mcp, config)

        # Verify tools are registered
        tools = await mcp.get_tools()

        expected_tools = [
            "workflow_guidance",
            "workflow_state",
            "workflow_discovery",
            "workflow_creation_guidance",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not found in registered tools"

    @pytest.mark.asyncio
    async def test_workflow_discovery_with_config(self):
        """Test that workflow_discovery works with server config."""
        from fastmcp import FastMCP

        from src.accordo_workflow_mcp.config import ServerConfig
        from src.accordo_workflow_mcp.prompts.discovery_prompts import (
            register_discovery_prompts,
        )

        # Create config and server
        config = ServerConfig(".")
        mcp = FastMCP("Test")
        register_discovery_prompts(mcp, config)

        # Get and test the workflow_discovery tool
        tools = await mcp.get_tools()
        discovery_tool = tools["workflow_discovery"]

        # Call the discovery function (should now use server-side discovery)
        result = discovery_tool.fn(task_description="Test task")

        # Verify it returns discovery results instead of agent instructions
        assert isinstance(result, dict)
        assert "status" in result
        # Should be either "workflows_discovered", "no_workflows_found", "discovery_error", or "session_conflict_detected"
        assert result["status"] in [
            "workflows_discovered",
            "no_workflows_found",
            "discovery_error",
            "session_conflict_detected",
        ]


class TestToolStructures:
    """Test tool registration and structure after refactoring."""

    @pytest.mark.asyncio
    async def test_workflow_guidance_tool_structure(self):
        """Test workflow_guidance tool structure."""
        from fastmcp import FastMCP

        from src.accordo_workflow_mcp.config import ServerConfig
        from src.accordo_workflow_mcp.prompts.phase_prompts import (
            register_phase_prompts,
        )

        config = ServerConfig(".")
        mcp = FastMCP("Test")
        register_phase_prompts(mcp, config)

        tools = await mcp.get_tools()
        assert "workflow_guidance" in tools
        workflow_tool = tools["workflow_guidance"]

        # Verify tool structure
        assert workflow_tool.name == "workflow_guidance"
        assert "Pure schema-driven workflow guidance" in workflow_tool.description
        assert "task_description" in workflow_tool.parameters["properties"]
        assert "action" in workflow_tool.parameters["properties"]
        assert "task_description" in workflow_tool.parameters["required"]

    @pytest.mark.asyncio
    async def test_workflow_discovery_tool_structure(self):
        """Test workflow_discovery tool structure after modification."""
        from fastmcp import FastMCP

        from src.accordo_workflow_mcp.config import ServerConfig
        from src.accordo_workflow_mcp.prompts.discovery_prompts import (
            register_discovery_prompts,
        )

        config = ServerConfig(".")
        mcp = FastMCP("Test")
        register_discovery_prompts(mcp, config)

        tools = await mcp.get_tools()
        assert "workflow_discovery" in tools
        discovery_tool = tools["workflow_discovery"]

        # Verify tool structure
        assert discovery_tool.name == "workflow_discovery"
        assert "Discover available workflows" in discovery_tool.description
        assert "task_description" in discovery_tool.parameters["properties"]
        assert "workflows_dir" in discovery_tool.parameters["properties"]
        assert "client_id" in discovery_tool.parameters["properties"]
        assert "task_description" in discovery_tool.parameters["required"]


class TestAutomaticCacheRestoration:
    """Test automatic cache restoration functionality."""

    def setup_method(self):
        """Set up test environment."""
        # FIX: Ensure services are properly initialized before tests
        # This addresses the SessionSyncService registration issues
        from src.accordo_workflow_mcp.services import (
            initialize_session_services,
            reset_session_services,
        )

        # Reset any existing services to ensure clean state
        reset_session_services()

        # Initialize all services including SessionSyncService
        initialize_session_services()

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up services after tests
        from src.accordo_workflow_mcp.services import reset_session_services

        reset_session_services()

    @patch("src.accordo_workflow_mcp.server.FastMCP")
    @patch("src.accordo_workflow_mcp.server.initialize_configuration_service")
    @patch("src.accordo_workflow_mcp.server.register_phase_prompts")
    @patch("src.accordo_workflow_mcp.server.register_discovery_prompts")
    @patch("src.accordo_workflow_mcp.services.get_session_sync_service")
    @patch("builtins.print")
    def test_main_with_cache_enabled_successful_restoration(
        self,
        mock_print,
        mock_get_session_sync_service,
        mock_register_discovery,
        mock_register_phase,
        mock_init_config,
        mock_fastmcp,
    ):
        """Test main function with cache enabled and successful restoration."""
        # Mock FastMCP instance
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Mock configuration service
        mock_config_service = Mock()
        mock_legacy_config = Mock()
        mock_config_service.to_legacy_server_config.return_value = mock_legacy_config
        mock_init_config.return_value = mock_config_service

        # FIX: Mock the SessionSyncService and its auto_restore method
        mock_session_sync_service = Mock()
        mock_session_sync_service.auto_restore_sessions_on_startup.return_value = 3
        mock_get_session_sync_service.return_value = mock_session_sync_service

        # Mock sys.argv with cache enabled
        test_args = ["server.py", "--enable-cache-mode"]
        with patch.object(sys, "argv", test_args):
            result = main()

        # Verify cache restoration was called
        mock_session_sync_service.auto_restore_sessions_on_startup.assert_called_once()

        # Verify success message was printed
        mock_print.assert_called_with(
            "Info: Automatically restored 3 workflow session(s) from cache"
        )

        # Verify server started normally
        mock_mcp_instance.run.assert_called_once_with(transport="stdio")
        assert result == 0

    @patch("src.accordo_workflow_mcp.server.FastMCP")
    @patch("src.accordo_workflow_mcp.server.initialize_configuration_service")
    @patch("src.accordo_workflow_mcp.server.register_phase_prompts")
    @patch("src.accordo_workflow_mcp.server.register_discovery_prompts")
    @patch("src.accordo_workflow_mcp.services.get_session_sync_service")
    @patch("builtins.print")
    def test_main_with_cache_enabled_no_sessions_to_restore(
        self,
        mock_print,
        mock_get_session_sync_service,
        mock_register_discovery,
        mock_register_phase,
        mock_init_config,
        mock_fastmcp,
    ):
        """Test main function with cache enabled but no sessions to restore."""
        # Mock FastMCP instance
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Mock configuration service
        mock_config_service = Mock()
        mock_legacy_config = Mock()
        mock_config_service.to_legacy_server_config.return_value = mock_legacy_config
        mock_init_config.return_value = mock_config_service

        # FIX: Mock the SessionSyncService and its auto_restore method
        mock_session_sync_service = Mock()
        mock_session_sync_service.auto_restore_sessions_on_startup.return_value = 0
        mock_get_session_sync_service.return_value = mock_session_sync_service

        # Mock sys.argv with cache enabled
        test_args = ["server.py", "--enable-cache-mode"]
        with patch.object(sys, "argv", test_args):
            result = main()

        # Verify cache restoration was called
        mock_session_sync_service.auto_restore_sessions_on_startup.assert_called_once()

        # FIX: Verify no SUCCESS message was printed for 0 restored sessions,
        # but allow debug messages that are part of the server startup process
        success_message_calls = [
            call
            for call in mock_print.call_args_list
            if call[0] and "Automatically restored" in str(call[0][0])
        ]
        assert len(success_message_calls) == 0, (
            "No success message should be printed for 0 restored sessions"
        )

        # The test can still have debug output - that's fine and expected now

        # Verify server started normally
        mock_mcp_instance.run.assert_called_once_with(transport="stdio")
        assert result == 0

    @patch("src.accordo_workflow_mcp.server.FastMCP")
    @patch("src.accordo_workflow_mcp.server.initialize_configuration_service")
    @patch("src.accordo_workflow_mcp.server.register_phase_prompts")
    @patch("src.accordo_workflow_mcp.server.register_discovery_prompts")
    @patch("src.accordo_workflow_mcp.services.get_session_sync_service")
    @patch("builtins.print")
    def test_main_with_cache_enabled_restoration_failure(
        self,
        mock_print,
        mock_get_session_sync_service,
        mock_register_discovery,
        mock_register_phase,
        mock_init_config,
        mock_fastmcp,
    ):
        """Test main function with cache enabled but restoration failure."""
        # Mock FastMCP instance
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Mock configuration service
        mock_config_service = Mock()
        mock_legacy_config = Mock()
        mock_config_service.to_legacy_server_config.return_value = mock_legacy_config
        mock_init_config.return_value = mock_config_service

        # FIX: Mock the SessionSyncService and its auto_restore method to throw exception
        mock_session_sync_service = Mock()
        mock_session_sync_service.auto_restore_sessions_on_startup.side_effect = (
            Exception("Cache connection failed")
        )
        mock_get_session_sync_service.return_value = mock_session_sync_service

        # Mock sys.argv with cache enabled
        test_args = ["server.py", "--enable-cache-mode"]
        with patch.object(sys, "argv", test_args):
            result = main()

        # Verify cache restoration was attempted
        mock_session_sync_service.auto_restore_sessions_on_startup.assert_called_once()

        # Verify error message was printed
        mock_print.assert_called_with(
            "Info: Automatic cache restoration skipped: Cache connection failed"
        )

        # Verify server started normally despite restoration failure
        mock_mcp_instance.run.assert_called_once_with(transport="stdio")
        assert result == 0

    @patch("src.accordo_workflow_mcp.server.FastMCP")
    @patch("src.accordo_workflow_mcp.server.initialize_configuration_service")
    @patch("src.accordo_workflow_mcp.server.register_phase_prompts")
    @patch("src.accordo_workflow_mcp.server.register_discovery_prompts")
    def test_main_with_cache_disabled_no_restoration(
        self,
        mock_register_discovery,
        mock_register_phase,
        mock_init_config,
        mock_fastmcp,
    ):
        """Test main function with cache disabled - no restoration should occur."""
        # Mock FastMCP instance
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Mock configuration service
        mock_config_service = Mock()
        mock_legacy_config = Mock()
        mock_config_service.to_legacy_server_config.return_value = mock_legacy_config
        mock_init_config.return_value = mock_config_service

        # Mock sys.argv without cache enabled
        test_args = ["server.py"]
        with (
            patch.object(sys, "argv", test_args),
            patch(
                "src.accordo_workflow_mcp.utils.session_manager.auto_restore_sessions_on_startup"
            ) as mock_auto_restore,
        ):
            result = main()

            # Verify cache restoration was NOT called
            mock_auto_restore.assert_not_called()

        # Verify server started normally
        mock_mcp_instance.run.assert_called_once_with(transport="stdio")
        assert result == 0

    def test_auto_restore_sessions_on_startup_function_exists(self):
        """Test that the auto_restore_sessions_on_startup function exists and is importable."""
        try:
            from src.accordo_workflow_mcp.utils.session_manager import (
                auto_restore_sessions_on_startup,
            )

            # Verify it's callable
            assert callable(auto_restore_sessions_on_startup)

            # Verify function signature (should return int)
            import inspect

            sig = inspect.signature(auto_restore_sessions_on_startup)
            assert len(sig.parameters) == 0  # No parameters expected

        except ImportError:
            pytest.fail(
                "auto_restore_sessions_on_startup function should be importable"
            )
