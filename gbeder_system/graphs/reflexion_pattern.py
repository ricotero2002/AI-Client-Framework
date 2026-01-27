"""
Reflexion Pattern (Pattern C - Critic-Reviewer) - Refactored
Tight iterative loop between Synthesizer and Reviewer with structured schemas.
"""
from typing import Dict, Any, Literal
from langsmith import traceable
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gbeder_system.state import GBederState, ReflexionState
from gbeder_system.config import MAX_ITERATIONS, EVAL_THRESHOLDS
from gbeder_system.agents import create_researcher, create_analyst, create_synthesizer, create_reviewer
from gbeder_system.mcp_client import MCPClient


@traceable(name="route_after_critique")
def route_after_critique(state: GBederState) -> Literal["synthesizer", "END"]:
    """
    Route after critique in reflexion loop.
    
    Logic:
    - If quality threshold met → END
    - If max iterations reached → END
    - Otherwise → back to synthesizer for refinement
    """
    is_complete = state.get("is_complete", False)
    iteration_count = state.get("iteration_count", 0)
    
    # Check if we've reached max refinement cycles
    if iteration_count >= MAX_ITERATIONS["reflexion"]:
        return "END"
    
    # If quality threshold met, we're done
    if is_complete:
        return "END"
    
    # Continue refinement
    return "synthesizer"


@traceable(name="create_critique_tracker")
def create_critique_tracker(state: GBederState) -> Dict[str, Any]:
    """Add critique tracking to state."""
    feedback = state.get("feedback", "")
    scores = state.get("scores", {})
    
    # Track critique history
    critique_history = state.get("critique_history", [])
    if feedback:
        critique_history.append(feedback)
    
    # Track quality progression
    quality_progression = state.get("quality_progression", [])
    if scores:
        avg_score = sum(scores.values()) / len(scores)
        quality_progression.append(avg_score)
    
    updated = state.copy()
    updated["critique_history"] = critique_history
    updated["quality_progression"] = quality_progression
    updated["refinement_count"] = len(critique_history)
    updated["iteration_count"] = updated.get("iteration_count", 0) + 1
    
    return updated


def create_reflexion_graph(mcp_client=None):
    """
    Create the Reflexion (Critic-Reviewer) graph pattern.
    
    This pattern:
    1. Researcher gathers data (once)
    2. Analyst processes data (once)
    3. Synthesizer creates initial draft
    4. Tight Synthesizer ↔ Reviewer loop until quality threshold or max iterations
    
    Args:
        mcp_client: Optional MCP client for Researcher agent
        
    Returns:
        Compiled StateGraph
    """
    # Create agents
    researcher = create_researcher()  # No MCP client needed - uses DirectTavilyClient
    analyst = create_analyst()
    synthesizer = create_synthesizer()
    reviewer = create_reviewer()  # Acts as Critic in this pattern
    
    # Async wrapper for researcher
    import asyncio
    
    def researcher_sync(state: GBederState) -> Dict[str, Any]:
        """Sync wrapper for async researcher."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, researcher.execute(state))
                return future.result()
        else:
            return loop.run_until_complete(researcher.execute(state))
    
    # Enhanced reviewer for reflexion (provides detailed critique)
    def critic_node(state: GBederState) -> Dict[str, Any]:
        """Critic node - enhanced reviewer for reflexion."""
        result = reviewer.execute(state)
        
        # Add tracking
        tracked = create_critique_tracker(result)
        
        return tracked
    
    # Create graph
    workflow = StateGraph(GBederState)
    
    # Add nodes
    workflow.add_node("researcher", researcher_sync)
    workflow.add_node("analyst", analyst.execute)
    workflow.add_node("synthesizer", synthesizer.execute)
    workflow.add_node("critic", critic_node)  # Reviewer acting as Critic
    
    # Set entry point: start with research
    workflow.set_entry_point("researcher")
    
    # Initial sequential flow (happens once)
    workflow.add_edge("researcher", "analyst")
    workflow.add_edge("analyst", "synthesizer")
    
    # Reflexion loop: Synthesizer → Critic → (Synthesizer or END)
    workflow.add_edge("synthesizer", "critic")
    
    # Conditional edge from critic
    workflow.add_conditional_edges(
        "critic",
        route_after_critique,
        {
            "synthesizer": "synthesizer",  # Continue refinement
            "END": END
        }
    )
    
    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


if __name__ == "__main__":
    # Test the reflexion graph
    import asyncio
    
    async def test_reflexion():
        """Test reflexion pattern."""
        # Initialize MCP client
        server_path = os.path.join(os.path.dirname(__file__), "..", "tavily_mcp_server.py")
        mcp_client = MCPClient(server_path)
        await mcp_client.connect()
        
        # Create graph
        graph = create_reflexion_graph(mcp_client)
        
        # Initial state
        initial_state: GBederState = {
            "messages": [],
            "query": "Explain the concept of prompt caching in LLMs and its benefits",
            "retrieved_context": [],
            "analysis": "",
            "draft": "",
            "feedback": "",
            "scores": {},
            "iteration_count": 0,
            "pattern_name": "reflexion",
            "current_agent": "",
            "total_tokens": {},
            "total_cost": 0.0,
            "is_complete": False,
            "needs_more_data": False,
            "critique_history": [],
            "quality_progression": [],
            "refinement_count": 0
        }
        
        # Run graph
        config = {"configurable": {"thread_id": "test_reflexion"}}
        result = await graph.ainvoke(initial_state, config)
        
        print("\n=== Reflexion Pattern Test ===")
        print(f"Final Draft Length: {len(result.get('draft', ''))}")
        print(f"Refinement Cycles: {result.get('refinement_count')}")
        print(f"Complete: {result.get('is_complete')}")
        print(f"Scores: {result.get('scores')}")
        print(f"Quality Progression: {result.get('quality_progression')}")
        
        await mcp_client.disconnect()
    
    asyncio.run(test_reflexion())
