"""
State definitions for GBeder Multi-Agent System
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import add_messages


class GBederState(TypedDict):
    """
    Main state for GBeder multi-agent research system.
    
    This state is shared across all agents and patterns.
    """
    # Message history (using LangGraph's message accumulator)
    messages: Annotated[List[Dict[str, Any]], add_messages]
    
    # Research data
    query: str  # Original research query
    retrieved_context: List[Dict[str, Any]]  # Search results from Tavily
    
    # Analysis and synthesis
    analysis: str  # Analyst's output
    draft: str  # Synthesizer's draft
    
    # Evaluation and feedback
    feedback: str  # Reviewer's feedback
    scores: Dict[str, float]  # Evaluation scores (faithfulness, relevancy, etc.)
    
    # Metadata and control flow
    iteration_count: int  # Number of refinement iterations
    pattern_name: str  # Which pattern is being used
    current_agent: str  # Current agent in workflow
    next_agent: str  # Next agent to route to (supervisor pattern)
    
    # Cost tracking
    total_tokens: Dict[str, int]  # Token usage per model
    input_tokens: Dict[str, int]  # Input token usage per model
    output_tokens: Dict[str, int]  # Output token usage per model
    total_cost: float  # Estimated total cost in USD

    # Tavily API usage tracking
    tavily_api_calls: int  # Number of API calls made to Tavily
    tavily_total_searches: int  # Total number of searches executed (sum of queries per call)
    
    # Status flags
    is_complete: bool  # Whether the research is complete
    needs_more_data: bool  # Whether more research is needed


class SupervisorState(TypedDict):
    """State specifically for Supervisor pattern with routing decisions."""
    base_state: GBederState
    next_agent: str  # Supervisor's routing decision
    supervisor_reasoning: str  # Why this route was chosen


class ReflexionState(TypedDict):
    """State for Reflexion pattern with critique loop tracking."""
    base_state: GBederState
    critique_history: List[str]  # History of critiques
    refinement_count: int  # Number of refinement cycles
    quality_progression: List[float]  # Track quality scores over iterations
