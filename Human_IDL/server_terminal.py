import os
import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("terminal")

@mcp.tool()
async def run_server_command(command: str, path: str = ".") -> str:
    """
    Executes a shell command in the specified directory (Windows/PowerShell).
    Args:
        command: The command to execute (e.g., 'dir', 'Get-ChildItem').
        path: The target directory path.
    """
    if not os.path.exists(path):
        return f"Error: The path '{path}' does not exist."

    try:
        # Forzamos shell=True y powershell para consistencia en Windows
        # Usamos 'chcp 65001' para asegurar UTF-8 si es necesario, o decodificamos con cuidado
        result = subprocess.run(
            f"powershell -Command \"{command}\"", 
            cwd=path, 
            shell=True, 
            capture_output=True, 
            text=True,
            encoding='utf-8', # Importante para caracteres latinos
            errors='replace'
        )
        output = result.stdout.strip() or result.stderr.strip()
        if not output:
            return "Command executed successfully with no output."
        return output
    except Exception as e:
        return f"System Error executing command: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")