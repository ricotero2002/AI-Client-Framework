"""
Simple test script to verify MCP server connection.
"""
import asyncio
import sys
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gbeder_system.mcp_client import MCPClient


async def test_mcp():
    """Test MCP connection with official Tavily server."""
    print("Testing official Tavily MCP server via NPX...")
    print(f"TAVILY_API_KEY set: {'YES' if os.getenv('TAVILY_API_KEY') else 'NO'}")
    
    if not os.getenv('TAVILY_API_KEY'):
        print("\n❌ TAVILY_API_KEY not set. Please set it in your .env file.")
        return
    
    print("\n🔌 Attempting to connect to official Tavily MCP server...")
    
    try:
        # No server path needed - uses official NPX server
        client = MCPClient()
        await client.connect()
        
        print("✅ Connected successfully!")
        print(f"Available tools: {[t['name'] for t in client.tools_info]}")
        
        # Test a simple search
        print("\n🔍 Testing tavily_search...")
        result = await client.call_tool("tavily_search", {
            "query": "Boca juniors refuerzos 2026",
            "max_results": 1
        })
        
        print(f"✅ Search successful! Got {len(result.get('results', []))} results")
        print(result)
        await client.disconnect()
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp())
