"""Platform-specific configuration handlers."""

from .base import BaseConfigHandler
from .claude import ClaudeDesktopHandler, ClaudeCodeHandler, ClaudeHandler  # ClaudeHandler is backward compatibility alias
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