# server_terminal.py
import os
import subprocess
import sys
from mcp.server.fastmcp import FastMCP

# Inicializamos el servidor
mcp = FastMCP("terminal")


@mcp.tool()
async def run_server_command(command: str, path: str) -> str:
    """
    Executes a PowerShell command in the current directory.
    
    Args:
        command: The PowerShell command to execute. 
                 Example: 'Get-ChildItem', 'Remove-Item -Path ./imagen.png'
        path: The directory where the command will be executed.
    """
    print(f"DEBUG: Executing: {command[:50]}...", file=sys.stderr)

    try:
        # Usamos powershell explícitamente para evitar problemas de cmd.exe
        # encoding='cp850' o 'utf-8' suele ser necesario en Windows
        result = subprocess.run(
            ["powershell", "-Command", command],
            cwd=path,
            capture_output=True,
            text=True,
            encoding='utf-8', 
            errors='replace' # Evita crash por caracteres raros
        )
        
        # Combinamos stdout y stderr para que el modelo vea todo
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if output:
            return f"OUTPUT:\n{output}"
        if error:
            return f"ERROR:\n{error}"
        
        return "Command executed successfully (No output returned)."

    except Exception as e:
        return f"SYSTEM ERROR: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")