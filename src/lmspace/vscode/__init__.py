"""VS Code workspace agent management."""

from __future__ import annotations

from .agent_dispatch import dispatch_agent
from .provision import provision_subagents

__all__ = [
    "dispatch_agent",
    "provision_subagents",
]
