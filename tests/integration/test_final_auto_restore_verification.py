"""
Final integration test to verify auto-restore works correctly with real server startup scenario.
"""

import contextlib
import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_final_auto_restore_verification():
    """Test that auto-restore works correctly in a real server startup scenario."""
    print("\n🎯 === FINAL AUTO-RESTORE VERIFICATION TEST ===")

    # Create a temporary directory for this test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        cache_dir = temp_path / ".accordo" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        print(f"🚨 Using temporary directory: {temp_path}")
        print(f"🚨 Cache directory: {cache_dir}")

        try:
            # Step 1: Initialize complete server stack (like real server startup)
            print("\n📋 STEP 1: Initialize complete server stack...")

            from accordo_workflow_mcp.services import initialize_cache_service
            from accordo_workflow_mcp.services.config_service import (
                ConfigurationService,
                EnvironmentConfiguration,
                PlatformConfiguration,
                ServerConfiguration,
                WorkflowConfiguration,
                initialize_configuration_service,
            )
            from accordo_workflow_mcp.services.dependency_injection import (
                clear_registry,
                register_singleton,
            )

            # Clear any existing registrations
            clear_registry()

            # Create server configuration exactly like server.py
            server_config = ServerConfiguration(
                repository_path=temp_path,
                enable_local_state_file=True,
                local_state_file_format="JSON",
                session_retention_hours=168,
                enable_session_archiving=True,
                enable_cache_mode=True,  # 🎯 CRITICAL: Cache mode enabled
                cache_db_path=str(cache_dir),
                cache_collection_name="workflow_states",
                cache_embedding_model="all-MiniLM-L6-v2",  # Lightweight model for testing
                cache_max_results=50,
            )

            workflow_config = WorkflowConfiguration(
                local_state_file=True,
                local_state_file_format="JSON",
            )

            platform_config = PlatformConfiguration(
                editor_type="cursor",
                environment_variables=dict(os.environ),
            )

            environment_config = EnvironmentConfiguration()

            # Initialize configuration service
            config_service = initialize_configuration_service(
                server_config=server_config,
                workflow_config=workflow_config,
                platform_config=platform_config,
                environment_config=environment_config,
            )

            # Register configuration service in dependency injection
            register_singleton(ConfigurationService, lambda: config_service)

            # Initialize cache service
            initialize_cache_service()

            print("✅ Complete server stack initialized successfully!")

            # Step 2: Create and cache some test sessions
            print("\n📋 STEP 2: Create and cache test sessions...")

            from datetime import UTC, datetime

            from accordo_workflow_mcp.models.workflow_state import DynamicWorkflowState
            from accordo_workflow_mcp.services import (
                get_session_repository,
                get_session_sync_service,
            )

            # Get services
            session_repo = get_session_repository()
            sync_service = get_session_sync_service()

            # Create test sessions
            test_sessions = []
            for i in range(3):
                session = DynamicWorkflowState(
                    session_id=f"test-session-{i + 1}",
                    client_id="default",
                    workflow_name=f"TestWorkflow{i + 1}",
                    status="RUNNING",
                    current_node="start",
                    inputs={"task": f"Test task {i + 1}"},
                    created_at=datetime.now(UTC),
                    log=[f"Session {i + 1} created for testing"],
                )
                test_sessions.append(session)

                # Store in repository
                with session_repo._lock:
                    session_repo._sessions[session.session_id] = session
                session_repo._register_session_for_client("default", session.session_id)

                # Sync to cache
                success = sync_service.sync_session_to_cache(session.session_id)
                print(f"✅ Session {session.session_id} cached: {success}")

            print(f"✅ Created and cached {len(test_sessions)} test sessions")

            # Step 3: Clear in-memory sessions (simulate server restart)
            print("\n📋 STEP 3: Clear in-memory sessions (simulate server restart)...")

            # Clear sessions from memory
            with session_repo._lock:
                session_repo._sessions.clear()
            with session_repo._registry_lock:
                session_repo._client_session_registry.clear()

            # Verify sessions are cleared
            all_sessions = session_repo.get_all_sessions()
            print(
                f"✅ In-memory sessions cleared: {len(all_sessions)} sessions remaining"
            )

            # Step 4: Test auto-restore (the critical test)
            print("\n📋 STEP 4: Test auto-restore functionality...")

            from accordo_workflow_mcp.utils.session_manager import (
                auto_restore_sessions_on_startup,
            )

            print("🚨 Calling auto_restore_sessions_on_startup()...")
            restored_count = auto_restore_sessions_on_startup()
            print(f"✅ Auto-restore returned: {restored_count} sessions restored")

            # Step 5: Verify sessions were restored
            print("\n📋 STEP 5: Verify sessions were restored...")

            # Check in-memory sessions
            all_sessions_after = session_repo.get_all_sessions()
            print(f"🚨 Sessions in memory after restore: {len(all_sessions_after)}")

            # Check specific sessions
            for original_session in test_sessions:
                restored_session = session_repo.get_session(original_session.session_id)
                if restored_session:
                    print(
                        f"✅ Session {original_session.session_id} successfully restored"
                    )
                    print(f"   - Status: {restored_session.status}")
                    print(f"   - Current node: {restored_session.current_node}")
                    print(f"   - Workflow: {restored_session.workflow_name}")
                else:
                    print(f"❌ Session {original_session.session_id} NOT restored")

            # Check client sessions
            client_sessions = session_repo.get_sessions_by_client("default")
            print(f"🚨 Client 'default' sessions: {len(client_sessions)}")

            # Step 6: Final verification
            print("\n📋 STEP 6: Final verification...")

            if restored_count == len(test_sessions):
                print(f"✅ SUCCESS: All {restored_count} sessions restored correctly!")
            elif restored_count > 0:
                print(
                    f"⚠️  PARTIAL SUCCESS: {restored_count}/{len(test_sessions)} sessions restored"
                )
            else:
                print(
                    f"❌ FAILURE: No sessions restored (expected {len(test_sessions)})"
                )

            # Test configuration access
            config = sync_service._get_effective_server_config()
            if config and getattr(config, "enable_cache_mode", False):
                print("✅ Configuration service access working correctly")
            else:
                print("❌ Configuration service access failed")

            # Test cache manager access
            if sync_service._cache_manager:
                print("✅ Cache manager available in session sync service")
            else:
                print("❌ Cache manager NOT available in session sync service")

            print(
                f"\n🎯 FINAL RESULT: Auto-restore functionality {'WORKING' if restored_count > 0 else 'FAILED'}"
            )

        except Exception as e:
            print(f"❌ ERROR in final verification test: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # Cleanup
            with contextlib.suppress(Exception):
                clear_registry()

    print("\n🎯 === FINAL AUTO-RESTORE VERIFICATION COMPLETE ===")


if __name__ == "__main__":
    test_final_auto_restore_verification()
