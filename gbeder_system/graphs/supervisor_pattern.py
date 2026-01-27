"""
Hierarchical Supervisor Pattern (Refactored)
Supervisor with message summarization and structured routing decisions using schemas.
"""
import json
import asyncio
from typing import Dict, Any, Literal, List
from langsmith import traceable
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from client_factory import create_client
from prompt import Prompt
from gbeder_system.state import GBederState
from gbeder_system.config import AGENT_MODELS, SYSTEM_PROMPTS, MAX_ITERATIONS
from gbeder_system.agents import create_researcher, create_analyst, create_synthesizer, create_reviewer
from gbeder_system.mcp_client import MCPClient
from gbeder_system.schemas import SupervisorDecision, MessageSummary


MESSAGE_SUMMARIZATION_THRESHOLD = 5  # Summarize when more than N messages


def _serialize_messages(messages: List[Any]) -> List[Dict[str, Any]]:
    """Helper to convert mixed message types (Dict, AIMessage) to serializable list."""
    serializable = []
    for msg in messages:
        if isinstance(msg, dict):
            serializable.append(msg)
        elif hasattr(msg, 'model_dump'):  # Pydantic v2 / LangChain
            serializable.append(msg.model_dump())
        elif hasattr(msg, 'dict'):  # Pydantic v1
            serializable.append(msg.dict())
        else:
            # Fallback for AIMessage/HumanMessage objects without clear dict methods
            serializable.append({
                "type": getattr(msg, "type", "message"),
                "content": getattr(msg, "content", str(msg)),
                "role": getattr(msg, "role", "unknown"),
                # Extract agent from additional_kwargs if present
                "agent": getattr(msg, "additional_kwargs", {}).get("agent", "unknown")
            })
    return serializable


@traceable(name="summarize_messages")
def summarize_messages(state: GBederState, client) -> MessageSummary:
    """
    Summarize message history to keep context manageable.
    
    Args:
        state: Current state with message history
        client: LLM client for summarization
        
    Returns:
        MessageSummary schema with condensed information
    """
    messages = state.get("messages", [])
    
    if len(messages) <= MESSAGE_SUMMARIZATION_THRESHOLD:
        # No need to summarize yet
        return None
    
    # Build context from recent messages
    message_summaries = []
    for m in messages[-10:]:  # Last 10 messages
        # Handle both dict and AIMessage objects
        if isinstance(m, dict):
            agent = m.get('agent', 'unknown')
            content = m.get('content', '')[:200]
        else:
            # AIMessage or other LangChain message objects
            agent = getattr(m, 'additional_kwargs', {}).get('agent', 'unknown')
            content = str(getattr(m, 'content', ''))[:200]
        
        message_summaries.append(f"Agent: {agent}\nContent: {content}")
    
    context = "\n---\n".join(message_summaries)
    
    prompt = (Prompt()
        .set_system("""You are an expert at summarizing multi-agent workflows.
Condense the conversation history into key points while preserving important information.

Return JSON with:
- summary: Overall progress summary
- key_decisions: List of important decisions made
- current_state: Current workflow state
- message_count_summarized: Number of messages summarized
""")
        .set_user_input(f"""Summarize this multi-agent workflow:

{context}

Provide a concise summary focusing on progress, decisions, and current state.""")
    )
    
    response, usage = client.get_response(prompt)
    
    # Track tokens (note: state not directly available in this helper, would need to pass)
    # Token tracking handled in main supervisor node
    
    # Parse
    try:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response
        data = json.loads(json_str)
        return MessageSummary(**data)
    except:
        # Fallback
        return MessageSummary(
            summary=f"Workflow in progress. {len(messages)} messages exchanged.",
            key_decisions=["Research initiated", "Analysis complete"],
            current_state=f"Current agent: {state.get('current_agent', 'unknown')}",
            message_count_summarized=len(messages)
        )


def create_supervisor_node(mcp_client=None):
    """Create supervisor node with structured routing and message management."""
    
    client = create_client("gemini", langsmith=True)
    client.select_model("gemini-2.0-flash")

    clientSummary = create_client("gemini", langsmith=True)
    clientSummary.select_model("gemini-2.0-flash-exp")
    
    @traceable(name="supervisor_node")
    def supervisor(state: GBederState) -> Dict[str, Any]:
        """
        Supervisor with message summarization and structured output.
        """
        messages = state.get("messages", [])
        current_agent = state.get("current_agent", "")
        iteration_count = state.get("iteration_count", 0)
        
        # Check if we need message summarization
        summary = None
        if len(messages) > MESSAGE_SUMMARIZATION_THRESHOLD:
            summary = summarize_messages(state, clientSummary)
        
        # Build context - use summary if available
        if summary:
            # === FIX APPLIED HERE: Serialize the specific slice of messages ===
            recent_msgs_serializable = _serialize_messages(messages[-3:])
            
            context_text = f"""Message Summary:
- {summary.summary}
- Key Decisions: {', '.join(summary.key_decisions)}
- Current State: {summary.current_state}

Latest Messages:
{json.dumps(recent_msgs_serializable, indent=2)}"""
        else:
            # === FIX APPLIED HERE: Use helper for consistency ===
            serializable_messages = _serialize_messages(messages[-5:])
            
            context_text = f"""Recent Activity:
{json.dumps(serializable_messages, indent=2) if serializable_messages else 'No messages yet'}"""
        
        # Add iteration urgency message if approaching limit
        iteration_urgency = ""
        iterations_remaining = MAX_ITERATIONS['supervisor'] - iteration_count
        if iterations_remaining <= 3:
            iteration_urgency = f"\n⚠️ URGENCY: Only {iterations_remaining} iterations remaining! Prioritize completion over perfection."
        
        # Build routing prompt
        prompt = (Prompt()
            .set_system(SYSTEM_PROMPTS["supervisor"])
            .set_user_input(f"""Current Workflow State:
- Current Agent: {current_agent}
- Iteration: {iteration_count}/{MAX_ITERATIONS['supervisor']}{iteration_urgency}
- Has Research: {len(state.get('retrieved_context', [])) > 0}
- Has Analysis: {bool(state.get('analysis'))}
- Has Draft: {bool(state.get('draft'))}
- Is Complete: {state.get('is_complete', False)}
- Needs More Data: {state.get('needs_more_data', False)}

{context_text}

Query: {state['query']}

Make a routing decision. Return JSON:
{{
    "next_agent": "researcher|analyst|synthesizer|reviewer|END",
    "reasoning": str,
    "progress_assessment": str,
    "estimated_completion": float (0-1)
}}""")
        )
        prompt.set_output_schema(SupervisorDecision)
        response, usage = client.get_response(prompt)
        print(response)
        
        # Initialize updated_state early to ensure it exists for fallback exception block
        updated_state = state.copy()
        next_agent = "end" # Default safety
        
        # Track tokens for cost calculation
        if "input_tokens" not in updated_state:
            updated_state["input_tokens"] = {}
        if "output_tokens" not in updated_state:
            updated_state["output_tokens"] = {}
        if "total_tokens" not in updated_state:
            updated_state["total_tokens"] = {}
        
        model = client.current_model
        updated_state["input_tokens"][model] = updated_state["input_tokens"].get(model, 0) + usage.prompt_tokens
        updated_state["output_tokens"][model] = updated_state["output_tokens"].get(model, 0) + usage.completion_tokens
        updated_state["total_tokens"][model] = updated_state["total_tokens"].get(model, 0) + usage.total_tokens
        
        # Parse structured response
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response
            
            data = json.loads(json_str)
            decision = SupervisorDecision(**data)
            next_agent = decision.next_agent.lower()
            reasoning = decision.reasoning
            print(f"🎯 SUPERVISOR: Setting next_agent in state = '{next_agent}'")
            print(f"🎯 SUPERVISOR: Reasoning = {reasoning}")
            
        except (json.JSONDecodeError, Exception) as e:
            # Fallback logic
            if state.get("needs_more_data"):
                next_agent = "researcher"
                reasoning = "More data required (fallback)"
            elif not state.get("retrieved_context"):
                next_agent = "researcher"
                reasoning = "No research data (fallback)"
            elif not state.get("analysis"):
                next_agent = "analyst"
                reasoning = "Need analysis (fallback)"
            elif not state.get("draft"):
                next_agent = "synthesizer"
                reasoning = "Need draft (fallback)"
            elif not state.get("scores"):
                next_agent = "reviewer"
                reasoning = "Need review (fallback)"
            else:
                next_agent = "end"
                reasoning = "Process complete (fallback)"
            
            decision = SupervisorDecision(
                next_agent=next_agent,
                reasoning=reasoning,
                progress_assessment="Fallback routing",
                estimated_completion=0.5
            )

        # If we summarized, replace messages with summary + recent
        if summary:
            # Ensure the recent messages are kept, but we might want to keep them as objects 
            # in the state if that's what LangGraph expects, or serialize them.
            # Usually LangGraph state prefers the original objects.
            updated_state["messages"] = [
                {"role": "system", "content": f"SUMMARY: {summary.summary}", "agent": "summarizer"}
            ] + messages[-3:]  # Keep only last 3 messages
        
        # Add supervisor decision
        updated_state["messages"] = updated_state["messages"] + [
            {
                "role": "assistant",
                "content": f"Routing to {next_agent}: {reasoning}",
                "agent": "supervisor",
                "structured_output": decision.dict()
            }
        ]
        
        updated_state["iteration_count"] = iteration_count + 1
        updated_state["next_agent"] = next_agent
        
        print(f"\n🎯 SUPERVISOR: Setting next_agent in state = '{updated_state['next_agent']}'")
        return updated_state
    
    return supervisor


@traceable(name="route_supervisor")
def route_supervisor(state: GBederState) -> Literal["researcher", "analyst", "synthesizer", "reviewer", "END"]:
    """Route based on structured supervisor decision."""
    # print(state) # Removed huge print for clarity
    next_agent = state.get("next_agent", "END")
    iteration_count = state.get("iteration_count", 0)
    
    print(f"\n🔀 ROUTE_SUPERVISOR: next_agent from state = '{next_agent}'")
    print(f"🔀 ROUTE_SUPERVISOR: iteration_count = {iteration_count}/{MAX_ITERATIONS['supervisor']}")
    
    # Safety: prevent infinite loops
    if iteration_count > MAX_ITERATIONS["supervisor"]:
        print(f"🔀 ROUTE_SUPERVISOR: Max iterations reached, returning END")
        return "END"
    
    if next_agent in ["researcher", "analyst", "synthesizer", "reviewer"]:
        print(f"🔀 ROUTE_SUPERVISOR: Valid agent, returning '{next_agent}'")
        return next_agent
    
    print(f"🔀 ROUTE_SUPERVISOR: Invalid or END agent '{next_agent}', returning END")
    return "END"


def create_supervisor_graph():
    """
    Create supervisor pattern graph (no MCP client needed).
    
    Returns:
        Compiled LangGraph workflow
    """
    from gbeder_system.agents import create_researcher, create_analyst, create_synthesizer, create_reviewer
    
    # Create agents (ResearcherAgent now uses DirectTavilyClient internally)
    researcher = create_researcher()
    analyst = create_analyst()
    synthesizer = create_synthesizer()
    reviewer = create_reviewer()
    supervisor_node = create_supervisor_node()
    
    # Async wrapper for researcher
    async def researcher_wrapper(state):
        return await researcher.execute(state)
    
    def researcher_sync(state):
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
    
    # Create graph
    workflow = StateGraph(GBederState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", researcher_sync)
    workflow.add_node("analyst", analyst.execute)
    workflow.add_node("synthesizer", synthesizer.execute)
    workflow.add_node("reviewer", reviewer.execute)
    
    # Entry point
    workflow.set_entry_point("supervisor")
    
    # Conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "researcher": "researcher",
            "analyst": "analyst",
            "synthesizer": "synthesizer",
            "reviewer": "reviewer",
            "END": END
        }
    )
    
    # All agents return to supervisor
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("analyst", "supervisor")
    workflow.add_edge("synthesizer", "supervisor")
    workflow.add_edge("reviewer", "supervisor")
    
    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


if __name__ == "__main__":
    # Test
    import asyncio
    
    async def test_supervisor():
        """Test supervisor pattern."""
        # No MCP client needed - ResearcherAgent uses DirectTavilyClient internally
        graph = create_supervisor_graph()
        
        initial_state: GBederState = {
            "messages": [],
            "query": "What are the latest developments in AI agents?",
            "retrieved_context": [],
            "analysis": "",
            "draft": "",
            "feedback": "",
            "scores": {},
            "iteration_count": 0,
            "pattern_name": "supervisor",
            "current_agent": "",
            "total_tokens": {},
            "total_cost": 0.0,
            "is_complete": False,
            "needs_more_data": False
        }
        
        config = {"configurable": {"thread_id": "test_supervisor"}}
        result = await graph.ainvoke(initial_state, config)
        
        print("\n=== Supervisor Pattern Test ===")
        print(f"Final Draft Length: {len(result.get('draft', ''))}")
        print(f"Iterations: {result.get('iteration_count')}")
        print(f"Complete: {result.get('is_complete')}")
        print(f"Messages: {len(result.get('messages', []))}")
        
    asyncio.run(test_supervisor())