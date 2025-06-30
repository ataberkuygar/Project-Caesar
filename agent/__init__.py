"""
Project Caesar Agent Package
AI Agent Core for in-car assistant simulation
"""

from .agent_core import AgentCore, AgentResponse
from .intent_router import IntentRouter, IntentType, IntentResult
from .tool_dispatcher import ToolDispatcher
from .dialogue_handler import DialogueHandler
from .state_tracker import StateTracker, EnvironmentState, UserPreferences

__version__ = "1.0.0"
__author__ = "Project Caesar Team"

__all__ = [
    "AgentCore",
    "AgentResponse", 
    "IntentRouter",
    "IntentType",
    "IntentResult",
    "ToolDispatcher",
    "DialogueHandler",
    "StateTracker",
    "EnvironmentState",
    "UserPreferences"
]
