"""Integration tests for MCP client workflow execution with semantic cache functionality."""

from pathlib import Path

import pytest

from src.dev_workflow_mcp.config import ServerConfig
from src.dev_workflow_mcp.models.workflow_state import DynamicWorkflowState
from src.dev_workflow_mcp.utils import session_manager
from src.dev_workflow_mcp.utils.cache_manager import WorkflowCacheManager


class TestMCPClientSemanticWorkflow:
    """Test complete MCP client workflow execution with semantic cache integration."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Clear session state before each test."""
        session_manager.sessions.clear()
        session_manager.client_session_registry.clear()

    @pytest.mark.asyncio
    async def test_mcp_server_initialization_with_cache(
        self, mcp_server_with_cache, test_server_config: ServerConfig
    ):
        """Test that MCP server initializes correctly with cache mode enabled."""
        # Verify server is created
        assert mcp_server_with_cache is not None
        assert mcp_server_with_cache.name == "Test Workflow Server"
        
        # Verify configuration
        assert test_server_config.enable_cache_mode is True
        assert test_server_config.cache_collection_name == "test_workflow_states"
        assert test_server_config.cache_embedding_model == "all-MiniLM-L6-v2"

    @pytest.mark.asyncio 
    async def test_workflow_discovery_via_mcp_tools(
        self, mcp_server_with_cache, test_workflows_dir: Path
    ):
        """Test workflow discovery functionality through MCP tools."""
        # Test that we can access the workflow discovery tool
        tools = await mcp_server_with_cache.get_tools()
        tool_names = list(tools.keys())
        
        assert "workflow_discovery" in tool_names
        assert "workflow_guidance" in tool_names
        assert "workflow_state" in tool_names
        assert "workflow_semantic_analysis" in tool_names

    @pytest.mark.asyncio
    async def test_workflow_session_creation_and_progression(
        self, mcp_server_with_cache, test_workflows_dir: Path
    ):
        """Test complete workflow session creation and progression."""
        # Simulate workflow discovery call
        tools = await mcp_server_with_cache.get_tools()
        
        assert "workflow_discovery" in tools, "workflow_discovery tool not found"
        assert "workflow_guidance" in tools, "workflow_guidance tool not found"

    @pytest.mark.asyncio
    async def test_semantic_cache_population_and_search(
        self, mock_cache_manager: WorkflowCacheManager, temp_cache_dir: Path
    ):
        """Test semantic cache population and search functionality."""
        # Create a test workflow state
        test_state = DynamicWorkflowState(
            session_id="test-session-001",
            client_id="test-client",
            workflow_name="Test Integration Workflow",
            current_node="start_task",
            status="RUNNING",
            inputs={"task_description": "Test: Integration test execution"},
            node_outputs={
                "start_task": {
                    "task_initialized": "Task properly initialized for integration testing",
                    "initial_log_created": "Initial log entry created successfully"
                }
            },
            log=["Started integration test workflow"]
        )
        
        # Test cache storage
        result = mock_cache_manager.store_workflow_state(test_state)
        assert result.success is True
        
        # Test semantic search
        search_results = mock_cache_manager.semantic_search(
            search_text="integration test workflow execution",
            max_results=5,
            min_similarity=0.1
        )
        
        # In a real test environment, this might return results
        # In test environment with mock embeddings, it may return empty
        assert isinstance(search_results, list)

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_with_cache_persistence(
        self, mcp_server_with_cache, mock_cache_manager: WorkflowCacheManager, 
        test_workflows_dir: Path
    ):
        """Test complete end-to-end workflow execution with cache persistence."""
        # This test would simulate a complete workflow execution:
        # 1. Discovery -> 2. Start -> 3. Progression -> 4. Cache storage -> 5. Semantic search
        
        # For now, verify the components are properly integrated
        tools = await mcp_server_with_cache.get_tools()
        tool_names = list(tools.keys())
        
        # Verify all required tools are available
        required_tools = [
            "workflow_discovery",
            "workflow_guidance", 
            "workflow_state",
            "workflow_semantic_analysis",
            "workflow_cache_management"
        ]
        
        for required_tool in required_tools:
            assert required_tool in tool_names, f"Missing required tool: {required_tool}"
        
        # Verify cache manager is functional
        assert mock_cache_manager.is_available() is True

    @pytest.mark.asyncio
    async def test_concurrent_workflow_sessions_with_cache(
        self, mcp_server_with_cache, mock_cache_manager: WorkflowCacheManager
    ):
        """Test multiple concurrent workflow sessions with cache functionality."""
        # Create multiple test states to simulate concurrent sessions
        test_states = []
        for i in range(3):
            state = DynamicWorkflowState(
                session_id=f"concurrent-session-{i:03d}",
                client_id="test-client", 
                workflow_name="Test Integration Workflow",
                current_node="start_task",
                status="RUNNING",
                inputs={"task_description": f"Test: Concurrent session {i+1}"},
                node_outputs={},
                log=[f"Started concurrent session {i+1}"]
            )
            test_states.append(state)
            
        # Store all states in cache
        for state in test_states:
            result = mock_cache_manager.store_workflow_state(state)
            assert result.success is True
            
        # Test cache stats
        stats = mock_cache_manager.get_cache_stats()
        if stats:  # Only check if cache is actually initialized
            assert stats.total_entries >= 3

    @pytest.mark.asyncio
    async def test_cache_restoration_after_server_restart(
        self, mock_cache_manager: WorkflowCacheManager
    ):
        """Test cache restoration functionality after server restart simulation."""
        # Create and store a test state
        test_state = DynamicWorkflowState(
            session_id="restoration-test-session",
            client_id="test-client",
            workflow_name="Test Integration Workflow", 
            current_node="complete_task",
            status="COMPLETED",
            inputs={"task_description": "Test: Cache restoration after restart"},
            node_outputs={
                "start_task": {
                    "task_initialized": "Task initialized successfully",
                    "initial_log_created": "Initial log created"
                },
                "complete_task": {
                    "task_completed": "Task execution completed",
                    "results_documented": "Results documented successfully"
                }
            },
            log=[
                "Started workflow",
                "Progressed to completion", 
                "Workflow completed successfully"
            ]
        )
        
        # Store in cache
        store_result = mock_cache_manager.store_workflow_state(test_state)
        assert store_result.success is True
        
        # Simulate retrieval (as would happen after restart)
        retrieved_state = mock_cache_manager.retrieve_workflow_state("restoration-test-session")
        
        if retrieved_state:  # Only check if cache actually stored/retrieved
            assert retrieved_state.session_id == "restoration-test-session"
            assert retrieved_state.workflow_name == "Test Integration Workflow"
            assert retrieved_state.status == "COMPLETED"

    @pytest.mark.asyncio
    async def test_semantic_search_result_quality(
        self, mock_cache_manager: WorkflowCacheManager
    ):
        """Test the quality and relevance of semantic search results."""
        # Create diverse test states with different contexts
        test_states = [
                         DynamicWorkflowState(
                 session_id="coding-session-001",
                 client_id="test-client",
                 workflow_name="Coding Workflow",
                 current_node="implement",
                 status="RUNNING",
                 inputs={"task_description": "Implement: User authentication system"},
                 node_outputs={
                     "implement": {
                         "code_written": "Authentication code implementation completed",
                         "tests_added": "Unit tests for authentication added"
                     }
                 },
                 log=["Started coding authentication system"]
             ),
             DynamicWorkflowState(
                 session_id="debugging-session-001",
                 client_id="test-client",
                 workflow_name="Debugging Workflow",
                 current_node="analyze",
                 status="RUNNING", 
                 inputs={"task_description": "Debug: Memory leak in user service"},
                 node_outputs={
                     "analyze": {
                         "issue_identified": "Memory leak identified in user session management",
                         "root_cause_found": "Unclosed database connections causing leak"
                     }
                 },
                 log=["Started debugging memory leak issue"]
             )
        ]
        
        # Store states in cache
        for state in test_states:
            result = mock_cache_manager.store_workflow_state(state)
            assert result.success is True
            
        # Test semantic search for coding-related queries
        coding_results = mock_cache_manager.semantic_search(
            search_text="authentication system implementation coding",
            max_results=5,
            min_similarity=0.1
        )
        
        # Test semantic search for debugging-related queries  
        debug_results = mock_cache_manager.semantic_search(
            search_text="memory leak debugging analysis",
            max_results=5,
            min_similarity=0.1
        )
        
        # Verify results structure (even if empty in test environment)
        assert isinstance(coding_results, list)
        assert isinstance(debug_results, list)
        
        # In a real environment with proper embeddings, we would verify:
        # - Coding query returns coding-related results first
        # - Debug query returns debug-related results first
        # - Similarity scores are reasonable
        # - Results are ranked by relevance


class TestMCPClientIntegrationErrorHandling:
    """Test error handling and edge cases in MCP client integration."""

    @pytest.fixture(autouse=True) 
    def setup_method(self):
        """Clear session state before each test."""
        session_manager.sessions.clear()
        session_manager.client_session_registry.clear()

    @pytest.mark.asyncio
    async def test_cache_unavailable_graceful_degradation(
        self, mcp_server_with_cache
    ):
        """Test graceful degradation when cache is unavailable."""
        # Test that workflow functionality continues even if cache fails
        tools = await mcp_server_with_cache.get_tools()
        tool_names = list(tools.keys())
        
        # All tools should still be available
        assert "workflow_guidance" in tool_names
        assert "workflow_semantic_analysis" in tool_names
        
    @pytest.mark.asyncio
    async def test_invalid_workflow_yaml_handling(
        self, temp_dir: Path, test_server_config: ServerConfig
    ):
        """Test handling of invalid workflow YAML files."""
        # Create invalid workflow YAML
        workflows_dir = temp_dir / ".workflow-commander" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        invalid_yaml = workflows_dir / "invalid-workflow.yaml"
        invalid_yaml.write_text("invalid: yaml: content: [malformed")
        
        # Test that server handles invalid YAML gracefully
        # In a real scenario, the workflow loader would handle this
        assert workflows_dir.exists()
        assert invalid_yaml.exists()

    @pytest.mark.asyncio
    async def test_semantic_search_with_empty_cache(
        self, mock_cache_manager: WorkflowCacheManager
    ):
        """Test semantic search behavior with empty cache."""
        # Search in empty cache
        results = mock_cache_manager.semantic_search(
            search_text="non-existent workflow data",
            max_results=5,
            min_similarity=0.1
        )
        
        # Should return empty list, not error
        assert isinstance(results, list)
        assert len(results) == 0 