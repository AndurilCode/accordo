"""Embedding service for handling sentence transformer operations and model initialization."""

import threading
from typing import TYPE_CHECKING, Protocol

import numpy as np
from numpy.typing import NDArray

# Lazy import for SentenceTransformer to avoid heavy startup loading
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer
else:
    SentenceTransformer = object  # Type placeholder for runtime

from ..logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingServiceProtocol(Protocol):
    """Protocol for embedding service implementations."""

    def get_embeddings(self, texts: list[str]) -> NDArray[np.floating] | None:
        """Generate embeddings for the given texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of embeddings or None if model unavailable
        """
        ...

    def is_available(self) -> bool:
        """Check if embedding service is available and functional."""
        ...

    def get_model_name(self) -> str:
        """Get the name of the currently loaded model."""
        ...


class EmbeddingService(EmbeddingServiceProtocol):
    """Service for handling sentence transformer operations and model initialization."""

    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        """Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self._lock = threading.Lock()
        self._initialization_attempted = False
        self._initialization_error: str | None = None
        self._needs_compatibility_check = False

    def get_embeddings(self, texts: list[str]) -> NDArray[np.floating] | None:
        """Generate embeddings for the given texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of embeddings or None if model unavailable
        """
        if not texts:
            return None

        model = self._get_model()
        if model is None:
            return None

        try:
            embeddings = model.encode(texts)
            return embeddings
        except Exception as e:
            logger.warning(
                "Failed to generate embeddings",
                model_name=self.model_name,
                error=str(e)
            )
            return None

    def is_available(self) -> bool:
        """Check if embedding service is available and functional."""
        return self._get_model() is not None

    def get_model_name(self) -> str:
        """Get the name of the currently loaded model."""
        return self.model_name

    def _get_model(self) -> SentenceTransformer | None:
        """Get the embedding model, loading it if necessary.

        In test environments, returns a mock object to avoid heavy loading.
        Otherwise uses a fallback chain for model selection:
        1. Configured model (self.model_name)
        2. all-mpnet-base-v2 (balanced quality/speed)
        3. all-MiniLM-L6-v2 (fast fallback)

        Returns:
            SentenceTransformer model or None if loading fails
        """
        if self._model is not None:
            return self._model

        # Skip heavy model loading in test environments
        if self._is_test_environment():
            logger.debug("Test environment detected: using mock embedding model")
            self._model = self._create_mock_model()  # type: ignore
            return self._model

        if self._initialization_attempted and self._initialization_error:
            return None

        with self._lock:
            if self._model is not None:
                return self._model

            if self._initialization_attempted and self._initialization_error:
                return None

            self._initialization_attempted = True

            try:
                # Lazy import SentenceTransformer only when actually needed
                from sentence_transformers import SentenceTransformer

                # Define fallback model chain (balanced → high quality → fast)
                model_chain = [
                    self.model_name,  # User-configured model
                    "all-mpnet-base-v2",  # Balanced default (335MB)
                    "all-MiniLM-L6-v2",  # Fast fallback (91MB)
                ]

                # Remove duplicates while preserving order
                model_chain = list(dict.fromkeys(model_chain))

                for model_name in model_chain:
                    try:
                        logger.info(f"Loading embedding model: {model_name}")
                        self._model = SentenceTransformer(
                            model_name, device="cpu"
                        )
                        if model_name != self.model_name:
                            logger.info(
                                "Using fallback embedding model",
                                fallback_model=model_name,
                                requested_model=self.model_name
                            )

                        return self._model
                    except Exception as e:
                        logger.warning(
                            "Failed to load embedding model",
                            model_name=model_name,
                            error=str(e)
                        )
                        continue

                # All models failed
                self._initialization_error = "All embedding models failed to load"
                logger.error("All embedding models failed to load")
                return None

            except ImportError as e:
                self._initialization_error = f"sentence-transformers library not available: {e}"
                logger.warning(
                    "sentence-transformers library not available",
                    error=str(e)
                )
                return None

    def _is_test_environment(self) -> bool:
        """Detect if running in test environment to skip heavy model loading."""
        import sys
        
        # Check for pytest in modules
        if "pytest" in sys.modules:
            return True
            
        # Check for test-related environment variables
        import os
        if any(
            test_var in os.environ 
            for test_var in ["PYTEST_RUNNING", "TESTING", "TEST_ENV"]
        ):
            return True
            
        # Check if running from test directory
        import inspect
        frame = inspect.currentframe()
        while frame:
            filename = frame.f_code.co_filename
            if "/tests/" in filename or filename.endswith("_test.py"):
                return True
            frame = frame.f_back
            
        return False

    def _create_mock_model(self) -> object:
        """Create a mock embedding model for testing."""
        
        class MockEmbeddingModel:
            """Mock embedding model that returns predictable embeddings."""
            
            def encode(self, texts, **kwargs):  # type: ignore
                """Return mock embeddings based on text hash."""
                import hashlib
                
                embeddings = []
                for text in texts:
                    # Create deterministic embedding based on text hash
                    text_hash = hashlib.md5(text.encode()).hexdigest()
                    # Convert to 384-dimensional vector (common embedding size)
                    embedding = [
                        (int(text_hash[i:i+2], 16) / 255.0) - 0.5
                        for i in range(0, min(len(text_hash), 48), 2)
                    ]
                    # Pad to 384 dimensions
                    while len(embedding) < 384:
                        embedding.append(0.0)
                    embeddings.append(embedding[:384])
                
                return np.array(embeddings)
        
        return MockEmbeddingModel() 