"""
Simple test script for GBeder system.
Tests each pattern individually with a basic query.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gbeder_system.state import GBederState
from gbeder_system.mcp_client import MCPClient


async def test_pattern(pattern_name: str, graph_func, mcp_client=None):
    """Test a single pattern."""
    print(f"\n{'='*60}")
    print(f"Testing {pattern_name.upper()} Pattern")
    print(f"{'='*60}")
    
    # Create graph
    graph = graph_func(mcp_client)
    
    # Simple test query
    query = "What is LangGraph and how does it help with multi-agent systems?"
    print(f"Query: {query}\n")
    
    # Initial state
    initial_state: GBederState = {
        "messages": [],
        "query": query,
        "retrieved_context": [],
        "analysis": "",
        "draft": "",
        "feedback": "",
        "scores": {},
        "iteration_count": 0,
        "pattern_name": pattern_name,
        "current_agent": "",
        "total_tokens": {},
        "total_cost": 0.0,
        "is_complete": False,
        "needs_more_data": False
    }
    
    # Run graph
    try:
        config = {"configurable": {"thread_id": f"test_{pattern_name}"}}
        result = await graph.ainvoke(initial_state, config)
        
        # Display results
        print(f"✓ Test completed successfully")
        print(f"  - Iterations: {result.get('iteration_count', 0)}")
        print(f"  - Complete: {result.get('is_complete', False)}")
        print(f"  - Quality Score: {sum(result.get('scores', {}).values()) / len(result.get('scores', {})) if result.get('scores') else 0:.3f}")
        print(f"  - Draft Length: {len(result.get('draft', ''))} characters")
        print(f"  - Total Tokens: {sum(result.get('total_tokens', {}).values()):,}")
        
        # Show a snippet of the draft
        draft = result.get('draft', '')
        if draft:
            snippet = draft[:200] + "..." if len(draft) > 200 else draft
            print(f"\n  Draft Preview:\n  {snippet}\n")
        
        return True
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all pattern tests."""
    print("\n" + "="*60)
    print("GBEDER SYSTEM - PATTERN TESTS")
    print("="*60)
    
    # Check for MCP
    use_mcp = bool(os.getenv("TAVILY_API_KEY"))
    
    mcp_client = None
    if use_mcp:
        try:
            server_path = os.path.join(os.path.dirname(__file__), "tavily_mcp_server.py")
            print(f"\n🔌 Connecting to Tavily MCP server...")
            mcp_client = MCPClient(server_path)
            await mcp_client.connect()
            print("✓ MCP client connected\n")
        except Exception as e:
            print(f"⚠️  MCP connection failed: {str(e)}")
            print("Running tests without MCP integration\n")
            mcp_client = None
    else:
        print("\n⚠️  TAVILY_API_KEY not set - running without MCP\n")
    
    # Import pattern builders
    from gbeder_system.graphs.supervisor_pattern import create_supervisor_graph
    from gbeder_system.graphs.sequential_pattern import create_sequential_graph
    from gbeder_system.graphs.reflexion_pattern import create_reflexion_graph
    
    # Test each pattern
    results = {}
    
    patterns = [
        ("supervisor", create_supervisor_graph),
        ("sequential", create_sequential_graph),
        ("reflexion", create_reflexion_graph)
    ]
    
    for pattern_name, graph_func in patterns:
        results[pattern_name] = await test_pattern(pattern_name, graph_func, mcp_client)
        await asyncio.sleep(1)  # Brief pause between tests
    
    # Disconnect MCP
    if mcp_client:
        await mcp_client.disconnect()
        print("\n✓ MCP client disconnected")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for pattern_name, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{pattern_name.upper():<15} {status}")
    
    print("="*60 + "\n")
    
    # Exit code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
