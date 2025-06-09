"""
Integration test to debug server startup and auto-restore flow.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_server_startup_auto_restore_flow():
    """Test that server startup calls auto-restore properly."""
    print("\n🚨 === DEBUGGING SERVER STARTUP AUTO-RESTORE FLOW ===")

    # Test 1: Direct import and call of session_manager auto_restore
    print("\n1. Testing direct session_manager auto_restore import and call...")

    try:
        from accordo_workflow_mcp.utils.session_manager import auto_restore_sessions_on_startup

        print(
            "✅ Successfully imported auto_restore_sessions_on_startup from session_manager"
        )

        # Mock the config service to enable cache mode
        with patch(
            "accordo_mcp.utils.session_manager._get_effective_server_config"
        ) as mock_config:
            mock_config.return_value = MagicMock(enable_cache_mode=True)

            with patch(
                "accordo_mcp.utils.session_manager._ensure_services_initialized"
            ):
                with patch(
                    "accordo_mcp.services.get_session_sync_service"
                ) as mock_get_service:
                    # Mock the session sync service
                    mock_sync_service = MagicMock()
                    mock_sync_service.auto_restore_sessions_on_startup.return_value = 3
                    mock_get_service.return_value = mock_sync_service

                    print("🚨 Calling auto_restore_sessions_on_startup() directly...")
                    result = auto_restore_sessions_on_startup()
                    print(f"✅ Result: {result}")

                    # Verify delegation worked
                    mock_sync_service.auto_restore_sessions_on_startup.assert_called_once()
                    print("✅ Confirmed delegation to session sync service worked")

    except Exception as e:
        print(f"❌ Error in direct test: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Test session sync service auto_restore directly
    print("\n2. Testing session sync service auto_restore directly...")

    try:
        from accordo_workflow_mcp.services.session_sync_service import SessionSyncService

        # Create mock dependencies
        mock_session_repo = MagicMock()
        mock_cache_manager = MagicMock()

        # Create service instance
        sync_service = SessionSyncService(mock_session_repo, mock_cache_manager)

        # Mock the config to enable cache mode
        with patch.object(sync_service, "_get_effective_server_config") as mock_config:
            mock_config.return_value = MagicMock(enable_cache_mode=True)

            with patch.object(
                sync_service, "restore_sessions_from_cache"
            ) as mock_restore:
                mock_restore.return_value = 5

                print(
                    "🚨 Calling session sync service auto_restore_sessions_on_startup() directly..."
                )
                result = sync_service.auto_restore_sessions_on_startup()
                print(f"✅ Result: {result}")

                # Verify delegation worked
                mock_restore.assert_called_once()
                print(
                    "✅ Confirmed session sync service auto_restore delegates to restore_sessions_from_cache"
                )

    except Exception as e:
        print(f"❌ Error in session sync service test: {e}")
        import traceback

        traceback.print_exc()

    # Test 3: Test the actual server startup import path
    print("\n3. Testing actual server startup import path...")

    try:
        # This simulates exactly what the server does
        from accordo_workflow_mcp.utils.session_manager import auto_restore_sessions_on_startup

        print("✅ Server import path works")
        print(f"Function location: {auto_restore_sessions_on_startup.__module__}")
        print(f"Function file: {auto_restore_sessions_on_startup.__code__.co_filename}")

        # Check if this is the delegation function
        import inspect

        source = inspect.getsource(auto_restore_sessions_on_startup)
        print("Function source:")
        print(source)

        if "get_session_sync_service" in source:
            print(
                "✅ Confirmed this is the delegation function that calls session sync service"
            )
        else:
            print("❌ WARNING: This doesn't look like the delegation function!")

    except Exception as e:
        print(f"❌ Error in server import path test: {e}")
        import traceback

        traceback.print_exc()

    # Test 4: Test dependency injection and service initialization
    print("\n4. Testing dependency injection and service initialization...")

    try:
        from accordo_workflow_mcp.services import get_session_sync_service
        from accordo_workflow_mcp.utils.session_manager import _ensure_services_initialized

        print("🚨 Testing _ensure_services_initialized()...")
        _ensure_services_initialized()
        print("✅ Services initialized successfully")

        print("🚨 Testing get_session_sync_service()...")
        sync_service = get_session_sync_service()
        print(f"✅ Got session sync service: {type(sync_service)}")

        # Test if the service has the auto_restore method
        if hasattr(sync_service, "auto_restore_sessions_on_startup"):
            print("✅ Session sync service has auto_restore_sessions_on_startup method")
        else:
            print(
                "❌ WARNING: Session sync service missing auto_restore_sessions_on_startup method!"
            )

    except Exception as e:
        print(f"❌ Error in dependency injection test: {e}")
        import traceback

        traceback.print_exc()

    # Test 5: CRITICAL - Test actual auto_restore call without mocking
    print("\n5. 🚨 CRITICAL TEST: Calling actual auto_restore without mocking...")

    try:
        from accordo_workflow_mcp.utils.session_manager import auto_restore_sessions_on_startup

        print(
            "🚨 About to call auto_restore_sessions_on_startup() with real implementation..."
        )
        print("🚨 This should show us if it hangs or throws an exception...")

        import time

        start_time = time.time()

        result = auto_restore_sessions_on_startup()

        end_time = time.time()
        duration = end_time - start_time

        print(f"✅ SUCCESS: auto_restore_sessions_on_startup() returned {result}")
        print(f"✅ Duration: {duration:.2f} seconds")

    except Exception as e:
        print(f"❌ ERROR in real auto_restore call: {e}")
        import traceback

        traceback.print_exc()

    # Test 6: 🎯 FULL SERVER SIMULATION - Initialize complete server stack
    print("\n6. 🎯 FULL SERVER SIMULATION: Initialize complete server stack...")

    try:
        print("🚨 Simulating complete server initialization...")

        # Import server components
        from accordo_workflow_mcp.services import initialize_cache_service
        from accordo_workflow_mcp.services.config_service import (
            ConfigurationService,
            EnvironmentConfiguration,
            PlatformConfiguration,
            ServerConfiguration,
            WorkflowConfiguration,
            initialize_configuration_service,
        )
        from accordo_workflow_mcp.services.dependency_injection import register_singleton
        from accordo_workflow_mcp.utils.session_manager import auto_restore_sessions_on_startup

        # Create server configuration (simulating what server.py does)
        print("🚨 Creating server configuration with cache enabled...")
        server_config = ServerConfiguration(
            repository_path=Path.cwd(),
            enable_local_state_file=False,
            local_state_file_format="MD",
            session_retention_hours=168,
            enable_session_archiving=True,
            enable_cache_mode=True,  # 🎯 THIS IS THE KEY
            cache_db_path=str(Path.cwd() / ".accordo" / "cache"),
            cache_collection_name="workflow_states",
            cache_embedding_model="all-mpnet-base-v2",
            cache_max_results=50,
        )

        workflow_config = WorkflowConfiguration(
            local_state_file=False,
            local_state_file_format="MD",
        )

        platform_config = PlatformConfiguration(
            editor_type="cursor",
            environment_variables=dict(os.environ),
        )

        environment_config = EnvironmentConfiguration()

        # Initialize configuration service (like server.py does)
        print("🚨 Initializing configuration service...")
        config_service = initialize_configuration_service(
            server_config=server_config,
            workflow_config=workflow_config,
            platform_config=platform_config,
            environment_config=environment_config,
        )

        # Register configuration service in dependency injection
        print("🚨 Registering configuration service in DI...")
        register_singleton(ConfigurationService, lambda: config_service)

        # Initialize cache service
        print("🚨 Initializing cache service...")
        initialize_cache_service()

        print("🚨 Complete server stack initialized successfully!")
        print(f"🚨 Server config cache mode: {server_config.enable_cache_mode}")

        # NOW test auto_restore with full server stack
        print("🚨 Testing auto_restore with full server stack...")

        import time

        start_time = time.time()

        result = auto_restore_sessions_on_startup()

        end_time = time.time()
        duration = end_time - start_time

        print(f"✅ SUCCESS: auto_restore with full server stack returned {result}")
        print(f"✅ Duration: {duration:.2f} seconds")

        # Test configuration service access
        print("🚨 Testing configuration service access from session sync service...")
        from accordo_workflow_mcp.services import get_session_sync_service

        sync_service = get_session_sync_service()

        # Check if sync service can access config now
        config = sync_service._get_effective_server_config()
        print(f"🚨 Config from sync service: {config}")
        if config:
            print(
                f"🚨 Config enable_cache_mode: {getattr(config, 'enable_cache_mode', None)}"
            )

    except Exception as e:
        print(f"❌ ERROR in full server simulation: {e}")
        import traceback

        traceback.print_exc()

    print("\n🚨 === DEBUG TEST COMPLETE ===")


if __name__ == "__main__":
    test_server_startup_auto_restore_flow()
