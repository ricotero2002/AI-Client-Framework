"""
Tavily MCP Server using FastMCP
Provides tavily_search and tavily_extract tools via MCP protocol.
"""
import os
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient

# Initialize FastMCP server
mcp = FastMCP("tavily")

# Initialize Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY environment variable not set")

tavily_client = TavilyClient(api_key=tavily_api_key)


@mcp.tool()
async def tavily_search(
    query: str,
    search_depth: str = "basic",
    max_results: int = 5,
    include_answer: bool = True,
    include_raw_content: bool = True,
    include_images: bool = False,
    topic: str = "general"
) -> dict:
    """
    Search for information using Tavily API.
    
    Args:
        query: The search query
        search_depth: Search depth - "basic", "advanced", "fast", or "ultra-fast"
        max_results: Maximum number of results (0-20)
        include_answer: Include LLM-generated answer
        include_raw_content: Include full content from sources
        include_images: Include image results
        topic: Topic category - "general", "news", or "finance"
    
    Returns:
        Search results with sources, answer, and metadata
    """
    try:
        response = tavily_client.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
            topic=topic
        )
        return response
    except Exception as e:
        return {"error": str(e), "results": []}


@mcp.tool()
async def tavily_extract(
    urls: list[str],
    extract_depth: str = "advanced",
    format: str = "markdown"
) -> dict:
    """
    Extract content from URLs using Tavily API.
    
    Args:
        urls: List of URLs to extract content from
        extract_depth: Extraction depth - "basic" or "advanced"
        format: Output format - "markdown" or "text"
    
    Returns:
        Extracted content from the URLs
    """
    try:
        # Tavily extract API
        response = tavily_client.extract(urls=urls)
        return response
    except Exception as e:
        return {"error": str(e), "results": []}


if __name__ == "__main__":
    # Run the MCP server with stdio transport
    mcp.run(transport="stdio")
