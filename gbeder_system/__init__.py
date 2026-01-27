"""
GBeder Multi-Agent Research System
A production-ready multi-agent system using LangGraph with MCP integration.
"""

from .state import GBederState
from .config import AGENT_MODELS, MODEL_COSTS, EVAL_THRESHOLDS, MAX_ITERATIONS

__version__ = "1.0.0"
__all__ = [
    "GBederState",
    "AGENT_MODELS",
    "MODEL_COSTS",
    "EVAL_THRESHOLDS",
    "MAX_ITERATIONS",
]
