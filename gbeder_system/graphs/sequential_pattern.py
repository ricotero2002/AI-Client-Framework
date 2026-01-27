"""
Sequential with Feedback Pattern (Pattern A) - Refactored
Linear flow with conditional kickback, using refactored agents with structured schemas.
"""
from typing import Dict, Any, Literal
from langsmith import traceable
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gbeder_system.state import GBederState
from gbeder_system.config import MAX_ITERATIONS, EVAL_THRESHOLDS
from gbeder_system.agents import create_researcher, create_analyst, create_synthesizer, create_reviewer
from gbeder_system.mcp_client import MCPClient
from gbeder_system.schemas import ReviewOutput


@traceable(name="route_after_review")
def route_after_review(state: GBederState) -> Literal["synthesizer", "researcher", "END"]:
    """
    Route after review based on scores and feedback.
    
    Logic:
    - If complete → END
    - If low scores but has tried too many times → END
    - If needs major data changes →  back to researcher
    - If needs style/logic fixes → back to synthesizer
    """
    print(f"\n🎯 ROUTE_REVIEWER: Reviewer feedback: {state.get('feedback')}")
    print(f"🎯 ROUTE_REVIEWER: Scores: {state.get('scores')}")
    print(f"🎯 ROUTE_REVIEWER: Iteration: {state.get('iteration_count')}/{MAX_ITERATIONS['sequential_feedback']}")
    print(f"🎯 ROUTE_REVIEWER: Complete: {state.get('is_complete')}")
    print(f"🎯 ROUTE_REVIEWER: Needs more data: {state.get('needs_more_data')}")
    is_complete = state.get("is_complete", False)
    iteration_count = state.get("iteration_count", 0)
    scores = state.get("scores", {})
    needs_more_data = state.get("needs_more_data", False)
    
    # Check iteration limit
    if iteration_count >= MAX_ITERATIONS["sequential_feedback"]:
        return "END"
    
    # If approved, we're done
    if is_complete:
        return "END"
    
    # If explicitly needs more data, go back to researcher
    if needs_more_data:
        return "researcher"
    
    # If scores are very low (< 0.5), might need more data
    avg_score = sum(scores.values()) / len(scores) if scores else 0
    if avg_score <0.5:
        return "researcher"
    
    # Otherwise, go back to synthesizer for refinement
    return "synthesizer"


def create_sequential_graph(mcp_client=None):
    """
    Create the Sequential with Feedback graph pattern.
    
    Args:
        mcp_client: Optional MCP client for Researcher agent
        
    Returns:
        Compiled StateGraph
    """
    # Create agents
    researcher = create_researcher()  # No MCP client needed - uses DirectTavilyClient
    analyst = create_analyst()
    synthesizer = create_synthesizer()
    reviewer = create_reviewer()
    
    # Create wrapper for async researcher
    async def researcher_node(state: GBederState) -> Dict[str, Any]:
        """Wrapper for async researcher."""
        result = await researcher.execute(state)
        return result
    
    # Handle async execution
    import asyncio
    
    def researcher_sync(state: GBederState) -> Dict[str, Any]:
        """Sync wrapper for researcher."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # Create a task if loop is running
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, researcher.execute(state))
                return future.result()
        else:
            return loop.run_until_complete(researcher.execute(state))
    
    # Create graph
    workflow = StateGraph(GBederState)
    
    # Add nodes
    workflow.add_node("researcher", researcher_sync)
    workflow.add_node("analyst", analyst.execute)
    workflow.add_node("synthesizer", synthesizer.execute)
    workflow.add_node("reviewer", reviewer.execute)
    
    # Set entry point: always start with research
    workflow.set_entry_point("researcher")
    
    # Sequential edges
    workflow.add_edge("researcher", "analyst")
    workflow.add_edge("analyst", "synthesizer")
    workflow.add_edge("synthesizer", "reviewer")
    
    # Conditional edge from reviewer (kickback mechanism)
    workflow.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "researcher": "researcher",
            "synthesizer": "synthesizer",
            "END": END
        }
    )
    
    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def increment_iteration(state: GBederState) -> Dict[str, Any]:
    """Helper to increment iteration count."""
    updated = state.copy()
    updated["iteration_count"] = state.get("iteration_count", 0) + 1
    return updated


if __name__ == "__main__":
    # Test the sequential graph
    import asyncio
    
    async def test_sequential():
        """Test sequential pattern."""
        # Initialize MCP client
        server_path = os.path.join(os.path.dirname(__file__), "..", "tavily_mcp_server.py")
        mcp_client = MCPClient(server_path)
        await mcp_client.connect()
        
        # Create graph
        graph = create_sequential_graph(mcp_client)
        
        # Initial state
        initial_state: GBederState = {
            "messages": [],
            "query": "What are the main benefits of using LangGraph for multi-agent systems?",
            "retrieved_context": [],
            "analysis": "",
            "draft": "",
            "feedback": "",
            "scores": {},
            "iteration_count": 0,
            "pattern_name": "sequential",
            "current_agent": "",
            "total_tokens": {},
            "total_cost": 0.0,
            "is_complete": False,
            "needs_more_data": False
        }
        
        # Run graph
        config = {"configurable": {"thread_id": "test_sequential"}}
        result = await graph.ainvoke(initial_state, config)
        
        print("\n=== Sequential Pattern Test ===")
        print(f"Final Draft Length: {len(result.get('draft', ''))}")
        print(f"Iterations: {result.get('iteration_count')}")
        print(f"Complete: {result.get('is_complete')}")
        print(f"Scores: {result.get('scores')}")
        
        await mcp_client.disconnect()
    
    asyncio.run(test_sequential())
