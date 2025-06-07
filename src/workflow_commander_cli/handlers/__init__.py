"""Platform-specific configuration handlers."""

from .base import BaseConfigHandler
from .claude import (  # ClaudeHandler is backward compatibility alias
    ClaudeCodeHandler,
    ClaudeDesktopHandler,
    ClaudeHandler,
)
from .cursor import CursorHandler
from .vscode import VSCodeHandler

__all__ = [
    "BaseConfigHandler",
    "CursorHandler",
    "ClaudeDesktopHandler",
    "ClaudeCodeHandler",
    "ClaudeHandler",  # Backward compatibility
    "VSCodeHandler",
]
