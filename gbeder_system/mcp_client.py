"""
MCP Client for Tavily Integration (Fixed Version)
Uses proper async context managers based on working reference implementation.
"""
import asyncio
import os
import sys
from typing import Any, Dict, List, Optional
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_client")


class MCPClient:
    """
    MCP Client for Tavily integration.
    Fixed version using proper async context managers.
    """
    
    def __init__(self, server_script_path: Optional[str] = None):
        """
        Initialize MCP Client.
        
        Args:
            server_script_path: Optional path to custom server. Uses official Tavily NPX server if None.
        """
        self.server_script_path = server_script_path
        self.session: Optional[ClientSession] = None
        self.tools_info: List[Dict[str, Any]] = []
        self._stdio_context = None
        self._session_context = None
        
        # Only verify server exists if custom path provided
        if server_script_path and not os.path.exists(server_script_path):
            raise FileNotFoundError(f"MCP server script not found: {server_script_path}")
        
        # Verify API key
        if not os.getenv("TAVILY_API_KEY"):
            raise ValueError("TAVILY_API_KEY environment variable not set")
    
    async def connect(self):
        """Connect to the Tavily MCP server using official NPM package."""
        logger.info(f"Connecting to official Tavily MCP server via NPX...")
        
        # Verify API key
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        
        # Use official Tavily MCP server from NPM
        # Command: npx -y tavily-mcp@0.1.3
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "tavily-mcp@0.1.3"],
            env={
                **os.environ.copy(),
                "TAVILY_API_KEY": tavily_api_key
            }
        )
        
        # Create stdio client context (don't enter yet)
        self._stdio_context = stdio_client(server_params)
        read, write = await self._stdio_context.__aenter__()
        
        # Create session context
        self._session_context = ClientSession(read, write)
        self.session = await self._session_context.__aenter__()
        
        # Initialize session
        await self.session.initialize()
        
        # Load tools using langchain_mcp_adapters
        try:
            tools = await load_mcp_tools(self.session)
            self.tools_info = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": getattr(tool, 'args_schema', {})
                }
                for tool in tools
            ]
            logger.info(f"Connected. Available tools: {[t['name'] for t in self.tools_info]}")
        except Exception as e:
            logger.warning(f"Could not load tools via langchain adapter: {e}")
            # Fallback: list tools directly
            response = await self.session.list_tools()
            self.tools_info = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in response.tools
            ]
            logger.info(f"Connected. Available tools: {[t['name'] for t in self.tools_info]}")
    
    async def disconnect(self):
        """Disconnect from the MCP server properly."""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._stdio_context:
            await self._stdio_context.__aexit__(None, None, None)
        logger.info("Disconnected from MCP server")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool response
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        
        logger.info(f"Calling tool: {tool_name}")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            
            # Extract content from result
            if result.content:
                import json
                text_content = ""
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        text_content += content_item.text
                    else:
                        text_content += str(content_item)
                
                # Try to parse as JSON
                try:
                    return json.loads(text_content)
                except json.JSONDecodeError:
                    return text_content
            
            return None
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            raise
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Convenience function
async def create_mcp_client(server_script_path: str = None) -> MCPClient:
    """
    Create and connect to official Tavily MCP client.
    
    Args:
        server_script_path: Deprecated, kept for compatibility
        
    Returns:
        Connected MCPClient instance
    """
    client = MCPClient(server_script_path)
    await client.connect()
    return client
