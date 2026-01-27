"""
Direct Tavily Client (without MCP)
Simple wrapper around tavily-python for direct API calls.
"""
import os
from typing import Dict, Any, Optional


class DirectTavilyClient:
    """
    Direct Tavily API client without MCP overhead.
    Simpler and more reliable for production use.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize direct Tavily client.
        
        Args:
            api_key: Tavily API key (reads from env if not provided)
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY not set")
        
        # Import tavily here to avoid import errors if not installed
        try:
            from tavily import TavilyClient
            self.client = TavilyClient(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "tavily-python is required. Install it with: pip install tavily-python"
            )
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Tavily tool directly.
        
        Args:
            tool_name: 'tavily_search' or 'tavily_extract'
            arguments: Tool arguments
            
        Returns:
            Tool response
        """
        if tool_name == "tavily_search":
            return self._search(arguments)
        elif tool_name == "tavily_extract":
            return self._extract(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Tavily search."""
        # Extract parameters
        query = args.get("query")
        search_depth = args.get("search_depth", "basic")
        max_results = args.get("max_results", 5)
        include_answer = args.get("include_answer", True)
        include_raw_content = args.get("include_raw_content", True)
        
        # Call Tavily API
        response = self.client.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_answer=include_answer,
            include_raw_content=include_raw_content
        )
        
        return response
    
    def _extract(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Tavily extract."""
        urls = args.get("urls", [])
        if isinstance(urls, str):
            urls = [urls]
        
        # Call Tavily extract API
        response = self.client.extract(urls=urls)
        
        return response
    
    async def connect(self):
        """No-op for compatibility with MCP client interface."""
        pass
    
    async def disconnect(self):
        """No-op for compatibility with MCP client interface."""
        pass
