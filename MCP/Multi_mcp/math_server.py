from mcp.server.fastmcp import FastMCP

# Usamos FastMCP pero prepararemos la instancia para ser importada
mcp = FastMCP(name="Math Server")

@mcp.tool()
def sumar(a: int, b: int) -> int:
    """Suma dos números"""
    return a + b

@mcp.tool()
def multiplicar(a: int, b: int) -> int:
    """Multiplica dos números"""
    return a * b