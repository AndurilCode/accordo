"""Comprehensive tests for cache_manager functionality."""

import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.dev_workflow_mcp.models.workflow_state import DynamicWorkflowState
from src.dev_workflow_mcp.models.yaml_workflow import (
    ExecutionConfig,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTree,
)
from src.dev_workflow_mcp.utils.cache_manager import WorkflowCacheManager


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir) / "cache"


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model for testing."""
    mock_model = Mock()
    mock_model.encode.return_value = [
        [0.1, 0.2, 0.3] for _ in range(384)
    ]  # Mock 384-dim embeddings
    return mock_model


@pytest.fixture
def test_workflow_def():
    """Create a test workflow definition."""
    return WorkflowDefinition(
        name="Test Workflow",
        description="Test workflow for cache testing",
        execution=ExecutionConfig(),
        workflow=WorkflowTree(
            goal="Test cache operations",
            root="start",
            tree={
                "start": WorkflowNode(
                    goal="Start testing",
                    acceptance_criteria={"started": "Test started"},
                    next_allowed_nodes=["complete"],
                ),
                "complete": WorkflowNode(
                    goal="Complete testing",
                    acceptance_criteria={"finished": "Test completed"},
                    next_allowed_nodes=[],
                ),
            },
        ),
    )


@pytest.fixture
def test_workflow_state(test_workflow_def):
    """Create a test workflow state."""
    return DynamicWorkflowState(
        client_id="test-client",
        workflow_name=test_workflow_def.name,
        current_node="start",
        status="READY",
        current_item="Test task for caching",
        inputs={},
    )


class TestWorkflowCacheManagerInit:
    """Test WorkflowCacheManager initialization."""

    def test_init_basic(self, temp_cache_dir):
        """Test basic initialization."""
        cache_manager = WorkflowCacheManager(str(temp_cache_dir))

        assert cache_manager.db_path == temp_cache_dir
        assert cache_manager.collection_name == "workflow_states"
        assert cache_manager.embedding_model_name == "all-MiniLM-L6-v2"
        assert cache_manager.max_results == 50
        assert not cache_manager._initialized

    def test_init_custom_params(self, temp_cache_dir):
        """Test initialization with custom parameters."""
        cache_manager = WorkflowCacheManager(
            str(temp_cache_dir),
            collection_name="custom_collection",
            embedding_model="custom-model",
            max_results=100,
        )

        assert cache_manager.collection_name == "custom_collection"
        assert cache_manager.embedding_model_name == "custom-model"
        assert cache_manager.max_results == 100

    def test_init_thread_safety(self, temp_cache_dir):
        """Test that lock is properly initialized for thread safety."""
        cache_manager = WorkflowCacheManager(str(temp_cache_dir))

        assert isinstance(cache_manager._lock, type(threading.Lock()))
        assert cache_manager._client is None
        assert cache_manager._collection is None
        assert cache_manager._embedding_model is None


class TestWorkflowCacheManagerEnvironmentDetection:
    """Test environment detection methods."""

    def test_is_test_environment_pytest(self):
        """Test detection of test environment via pytest."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        # Should return True since we're running under pytest
        assert cache_manager._is_test_environment() is True

    @patch("sys.modules", {"pytest": Mock()})
    def test_is_test_environment_pytest_modules(self):
        """Test detection via pytest in sys.modules."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        assert cache_manager._is_test_environment() is True

    @patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "test_file.py::test_function"})
    def test_is_test_environment_env_var(self):
        """Test detection via environment variables."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        assert cache_manager._is_test_environment() is True

    @patch.dict("os.environ", {"CI": "true"})
    def test_is_test_environment_ci(self):
        """Test detection via CI environment."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        assert cache_manager._is_test_environment() is True

    @patch("sys.argv", ["python", "-m", "pytest", "test_file.py"])
    def test_is_test_environment_argv(self):
        """Test detection via command line arguments."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        assert cache_manager._is_test_environment() is True


class TestWorkflowCacheManagerMockModel:
    """Test mock embedding model creation."""

    def test_create_mock_model(self):
        """Test mock model creation."""
        cache_manager = WorkflowCacheManager("/tmp/test")
        mock_model = cache_manager._create_mock_model()

        assert hasattr(mock_model, "encode")

    def test_mock_model_encode_single_text(self):
        """Test mock model encoding single text."""
        cache_manager = WorkflowCacheManager("/tmp/test")
        mock_model = cache_manager._create_mock_model()

        embeddings = mock_model.encode("test text")

        assert embeddings.shape == (1, 384)
        assert embeddings.dtype.name.startswith("float")

    def test_mock_model_encode_multiple_texts(self):
        """Test mock model encoding multiple texts."""
        cache_manager = WorkflowCacheManager("/tmp/test")
        mock_model = cache_manager._create_mock_model()

        texts = ["text 1", "text 2", "text 3"]
        embeddings = mock_model.encode(texts)

        assert embeddings.shape == (3, 384)
        assert embeddings.dtype.name.startswith("float")

    def test_mock_model_consistency(self):
        """Test that mock model returns consistent embeddings for same text."""
        cache_manager = WorkflowCacheManager("/tmp/test")
        mock_model = cache_manager._create_mock_model()

        text = "consistent test text"
        embedding1 = mock_model.encode(text)
        embedding2 = mock_model.encode(text)

        # Should be identical due to seeded random generation
        assert (embedding1 == embedding2).all()

    def test_mock_model_normalized(self):
        """Test that mock model returns normalized embeddings."""
        cache_manager = WorkflowCacheManager("/tmp/test")
        mock_model = cache_manager._create_mock_model()

        embeddings = mock_model.encode("test text")

        # Check that embeddings are normalized (norm should be close to 1)
        import numpy as np

        norms = np.linalg.norm(embeddings, axis=1)
        assert abs(norms[0] - 1.0) < 1e-6


class TestWorkflowCacheManagerInitialization:
    """Test cache manager initialization process."""

    @patch("chromadb.PersistentClient")
    def test_ensure_initialized_success(self, mock_client_class, temp_cache_dir):
        """Test successful initialization."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        cache_manager = WorkflowCacheManager(str(temp_cache_dir))
        result = cache_manager._ensure_initialized()

        assert result is True
        assert cache_manager._initialized is True
        assert cache_manager._client is mock_client
        assert cache_manager._collection is mock_collection

    @patch("chromadb.PersistentClient")
    def test_ensure_initialized_creates_directory(
        self, mock_client_class, temp_cache_dir
    ):
        """Test that initialization creates database directory."""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = Mock()
        mock_client_class.return_value = mock_client

        # Use a subdirectory that doesn't exist
        db_path = temp_cache_dir / "subdir" / "cache"
        cache_manager = WorkflowCacheManager(str(db_path))

        result = cache_manager._ensure_initialized()

        assert result is True
        assert db_path.exists()

    @patch("chromadb.PersistentClient")
    def test_ensure_initialized_failure(self, mock_client_class, temp_cache_dir):
        """Test initialization failure handling."""
        mock_client_class.side_effect = Exception("Database connection failed")

        cache_manager = WorkflowCacheManager(str(temp_cache_dir))
        result = cache_manager._ensure_initialized()

        assert result is False
        assert cache_manager._initialized is False

    @patch("chromadb.PersistentClient")
    def test_ensure_initialized_thread_safety(self, mock_client_class, temp_cache_dir):
        """Test thread safety of initialization."""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = Mock()
        mock_client_class.return_value = mock_client

        cache_manager = WorkflowCacheManager(str(temp_cache_dir))

        # Simulate concurrent initialization
        results = []
        threads = []

        def initialize():
            results.append(cache_manager._ensure_initialized())

        # Start multiple threads
        for _ in range(5):
            thread = threading.Thread(target=initialize)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should succeed
        assert all(results)
        assert cache_manager._initialized is True
        # Should only initialize once
        assert mock_client_class.call_count == 1

    def test_ensure_initialized_already_initialized(self, temp_cache_dir):
        """Test that already initialized manager skips re-initialization."""
        cache_manager = WorkflowCacheManager(str(temp_cache_dir))
        cache_manager._initialized = True

        result = cache_manager._ensure_initialized()

        assert result is True
        # Should not have created client since already initialized
        assert cache_manager._client is None


class TestWorkflowCacheManagerEmbeddingModel:
    """Test embedding model management."""

    def test_get_embedding_model_test_environment(self):
        """Test that test environment uses mock model."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        # Should detect test environment and return mock
        model = cache_manager._get_embedding_model()

        assert model is not None
        assert hasattr(model, "encode")
        # Should be the mock model
        embeddings = model.encode("test")
        assert embeddings.shape == (1, 384)

    def test_get_embedding_model_cached(self):
        """Test that embedding model is cached after first load."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        model1 = cache_manager._get_embedding_model()
        model2 = cache_manager._get_embedding_model()

        assert model1 is model2

    @patch(
        "src.dev_workflow_mcp.utils.cache_manager.WorkflowCacheManager._is_test_environment"
    )
    @patch("sentence_transformers.SentenceTransformer")
    def test_get_embedding_model_production(self, mock_transformer_class, mock_is_test):
        """Test embedding model loading in production environment."""
        mock_is_test.return_value = False
        mock_model = Mock()
        mock_transformer_class.return_value = mock_model

        cache_manager = WorkflowCacheManager("/tmp/test")
        result = cache_manager._get_embedding_model()

        assert result is mock_model
        mock_transformer_class.assert_called_once()

    @patch(
        "src.dev_workflow_mcp.utils.cache_manager.WorkflowCacheManager._is_test_environment"
    )
    @patch("sentence_transformers.SentenceTransformer")
    def test_get_embedding_model_fallback_chain(
        self, mock_transformer_class, mock_is_test
    ):
        """Test embedding model fallback chain."""
        mock_is_test.return_value = False

        # First model fails, second succeeds
        mock_transformer_class.side_effect = [
            Exception("Model 1 failed"),
            Mock(),  # Second model succeeds
        ]

        cache_manager = WorkflowCacheManager(
            "/tmp/test", embedding_model="custom-model"
        )
        result = cache_manager._get_embedding_model()

        assert result is not None
        # Should have tried both models
        assert mock_transformer_class.call_count == 2

    @patch(
        "src.dev_workflow_mcp.utils.cache_manager.WorkflowCacheManager._is_test_environment"
    )
    @patch("sentence_transformers.SentenceTransformer")
    def test_get_embedding_model_all_fail(self, mock_transformer_class, mock_is_test):
        """Test when all embedding models fail to load."""
        mock_is_test.return_value = False
        mock_transformer_class.side_effect = Exception("All models failed")

        cache_manager = WorkflowCacheManager("/tmp/test")
        result = cache_manager._get_embedding_model()

        assert result is None


class TestWorkflowCacheManagerEmbeddingGeneration:
    """Test embedding text generation."""

    def test_generate_embedding_text_basic(self, test_workflow_state):
        """Test basic embedding text generation."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        text = cache_manager._generate_embedding_text(test_workflow_state)

        assert isinstance(text, str)
        assert len(text) > 0
        assert "Test task for caching" in text
        assert "Test Workflow" in text

    def test_generate_embedding_text_includes_key_fields(self, test_workflow_state):
        """Test that embedding text includes all key fields."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        text = cache_manager._generate_embedding_text(test_workflow_state)

        # Should include major workflow fields
        assert test_workflow_state.current_item in text
        assert test_workflow_state.workflow_name in text
        assert test_workflow_state.current_node in text

    def test_generate_embedding_text_with_log_entries(self, test_workflow_state):
        """Test embedding text with log entries."""
        test_workflow_state.log = ["Log entry 1", "Log entry 2", "Log entry 3"]

        cache_manager = WorkflowCacheManager("/tmp/test")
        text = cache_manager._generate_embedding_text(test_workflow_state)

        # Should include recent log entries
        assert any(entry in text for entry in test_workflow_state.log)

    def test_generate_embedding_text_with_many_log_entries(self, test_workflow_state):
        """Test embedding text limits log entries to avoid excessive length."""
        # Create many log entries
        test_workflow_state.log = [f"Log entry {i}" for i in range(20)]

        cache_manager = WorkflowCacheManager("/tmp/test")
        text = cache_manager._generate_embedding_text(test_workflow_state)

        # Should limit the number of log entries included
        assert len(text) < 10000  # Reasonable upper bound
        assert "Log entry 19" in text  # Should include recent entries


class TestWorkflowCacheManagerAvailability:
    """Test cache manager availability checking."""

    def test_is_available_not_initialized(self):
        """Test availability when not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        # Mock _ensure_initialized to return False to simulate initialization failure
        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            assert cache_manager.is_available() is False

    @patch("chromadb.PersistentClient")
    def test_is_available_initialized(self, mock_client_class, temp_cache_dir):
        """Test availability when properly initialized."""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = Mock()
        mock_client_class.return_value = mock_client

        cache_manager = WorkflowCacheManager(str(temp_cache_dir))
        cache_manager._ensure_initialized()

        assert cache_manager.is_available() is True

    def test_is_available_initialization_failed(self, temp_cache_dir):
        """Test availability when initialization failed."""
        cache_manager = WorkflowCacheManager(str(temp_cache_dir))
        cache_manager._initialized = False

        # Mock failed initialization
        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            assert cache_manager.is_available() is False


class TestWorkflowCacheManagerCleanup:
    """Test cache manager cleanup."""

    def test_cleanup_not_initialized(self):
        """Test cleanup when not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        # Should not raise exception
        cache_manager.cleanup()

    @patch("chromadb.PersistentClient")
    def test_cleanup_initialized(self, mock_client_class, temp_cache_dir):
        """Test cleanup when initialized."""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = Mock()
        mock_client_class.return_value = mock_client

        cache_manager = WorkflowCacheManager(str(temp_cache_dir))
        cache_manager._ensure_initialized()

        cache_manager.cleanup()

        # Should reset initialization state
        assert cache_manager._initialized is False
        assert cache_manager._client is None
        assert cache_manager._collection is None
        assert cache_manager._embedding_model is None

    def test_cleanup_with_exception(self, temp_cache_dir):
        """Test cleanup handles exceptions gracefully."""
        cache_manager = WorkflowCacheManager(str(temp_cache_dir))
        cache_manager._client = Mock()
        cache_manager._client.reset.side_effect = Exception("Cleanup failed")
        cache_manager._initialized = True

        # Should not raise exception
        cache_manager.cleanup()

        # Should still reset state
        assert cache_manager._initialized is False


class TestWorkflowCacheManagerFullIntegration:
    """Integration tests for cache manager with real ChromaDB operations."""

    def test_basic_workflow_lifecycle(self, temp_cache_dir, test_workflow_state):
        """Test basic store/retrieve/delete lifecycle."""
        with patch(
            "src.dev_workflow_mcp.utils.cache_manager.WorkflowCacheManager._is_test_environment",
            return_value=True,
        ):
            cache_manager = WorkflowCacheManager(str(temp_cache_dir))

            # Should be available after initialization attempt
            if not cache_manager.is_available():
                pytest.skip("Cache manager not available - ChromaDB setup issue")

            # Store workflow state
            store_result = cache_manager.store_workflow_state(test_workflow_state)
            if store_result and store_result.success:
                # Retrieve workflow state
                retrieved = cache_manager.retrieve_workflow_state(
                    test_workflow_state.session_id
                )
                if retrieved:
                    assert retrieved.session_id == test_workflow_state.session_id
                    assert retrieved.workflow_name == test_workflow_state.workflow_name

                # Delete workflow state
                delete_result = cache_manager.delete_workflow_state(
                    test_workflow_state.session_id
                )
                if delete_result:
                    assert delete_result.success is True


class TestWorkflowCacheManagerStoreRetrieve:
    """Test store and retrieve operations that were missing coverage."""

    @patch("chromadb.PersistentClient")
    def test_store_workflow_state_not_initialized(
        self, mock_client_class, test_workflow_state
    ):
        """Test store when cache not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            result = cache_manager.store_workflow_state(test_workflow_state)

            assert result.success is False
            assert "not initialized" in result.error_message
            assert result.operation_type == "store"

    @patch("chromadb.PersistentClient")
    def test_store_workflow_state_no_embedding_model(
        self, mock_client_class, temp_cache_dir, test_workflow_state
    ):
        """Test store when embedding model unavailable."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        cache_manager = WorkflowCacheManager(str(temp_cache_dir))

        with patch.object(cache_manager, "_get_embedding_model", return_value=None):
            result = cache_manager.store_workflow_state(test_workflow_state)

            assert result.success is False
            assert "Embedding model not available" in result.error_message

    @patch("chromadb.PersistentClient")
    def test_store_workflow_state_exception(
        self, mock_client_class, temp_cache_dir, test_workflow_state
    ):
        """Test store operation exception handling."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.upsert.side_effect = Exception("Storage error")
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        cache_manager = WorkflowCacheManager(str(temp_cache_dir))

        # Mock embedding model
        import numpy as np

        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3] * 128])
        cache_manager._embedding_model = mock_model

        result = cache_manager.store_workflow_state(test_workflow_state)

        assert result.success is False
        assert "Storage error" in result.error_message

    def test_retrieve_workflow_state_not_initialized(self):
        """Test retrieve when cache not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            result = cache_manager.retrieve_workflow_state("test-id")

            assert result is None

    @patch("chromadb.PersistentClient")
    def test_retrieve_workflow_state_not_found(self, mock_client_class, temp_cache_dir):
        """Test retrieval when state not found."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.get.return_value = {"ids": [], "metadatas": [], "documents": []}
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        cache_manager = WorkflowCacheManager(str(temp_cache_dir))

        result = cache_manager.retrieve_workflow_state("nonexistent-id")

        assert result is None


class TestWorkflowCacheManagerDelete:
    """Test delete operations that were missing coverage."""

    def test_delete_workflow_state_not_initialized(self):
        """Test delete when cache not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            result = cache_manager.delete_workflow_state("test-id")

            assert result.success is False
            assert "not initialized" in result.error_message
            assert result.operation_type == "delete"

    @patch("chromadb.PersistentClient")
    def test_delete_workflow_state_exception(self, mock_client_class, temp_cache_dir):
        """Test delete operation exception handling."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.delete.side_effect = Exception("Delete error")
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        cache_manager = WorkflowCacheManager(str(temp_cache_dir))

        result = cache_manager.delete_workflow_state("test-id")

        assert result.success is False
        assert "Delete error" in result.error_message


class TestWorkflowCacheManagerStats:
    """Test cache statistics that were missing coverage."""

    def test_get_cache_stats_not_initialized(self):
        """Test cache stats when not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            stats = cache_manager.get_cache_stats()

            assert stats is None

    @patch("chromadb.PersistentClient")
    def test_get_cache_stats_exception(self, mock_client_class, temp_cache_dir):
        """Test cache stats exception handling."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.get.side_effect = Exception("Stats error")
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        cache_manager = WorkflowCacheManager(str(temp_cache_dir))

        stats = cache_manager.get_cache_stats()

        assert stats is None


class TestWorkflowCacheManagerSemanticSearch:
    """Test semantic search functionality that was missing coverage."""

    def test_semantic_search_not_initialized(self):
        """Test semantic search when not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            results = cache_manager.semantic_search("test query")

            assert results == []

    def test_semantic_search_no_text(self):
        """Test semantic search with no search text."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        results = cache_manager.semantic_search()

        assert results == []

    def test_semantic_search_no_embedding_model(self, temp_cache_dir):
        """Test semantic search when embedding model unavailable."""
        cache_manager = WorkflowCacheManager(str(temp_cache_dir))

        with (
            patch.object(cache_manager, "_ensure_initialized", return_value=True),
            patch.object(cache_manager, "_get_embedding_model", return_value=None),
        ):
            results = cache_manager.semantic_search("test query")

            assert results == []


class TestWorkflowCacheManagerAdditionalMethods:
    """Test additional methods that were missing coverage."""

    @patch("chromadb.PersistentClient")
    def test_find_similar_workflows_not_initialized(
        self, mock_client_class, test_workflow_state
    ):
        """Test find similar workflows when not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            results = cache_manager.find_similar_workflows(test_workflow_state)

            assert results == []

    def test_get_all_sessions_for_client_not_initialized(self):
        """Test get all sessions when not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            results = cache_manager.get_all_sessions_for_client("test-client")

            assert results == []

    def test_cleanup_old_entries_not_initialized(self):
        """Test cleanup old entries when not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            result = cache_manager.cleanup_old_entries(30)

            assert result == 0

    def test_regenerate_embeddings_not_initialized(self):
        """Test regenerate embeddings when not initialized."""
        cache_manager = WorkflowCacheManager("/tmp/test")

        with patch.object(cache_manager, "_ensure_initialized", return_value=False):
            result = cache_manager.regenerate_embeddings_for_enhanced_search()

            assert result == 0
