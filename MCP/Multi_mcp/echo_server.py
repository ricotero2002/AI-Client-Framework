from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="Echo Server")

@mcp.tool()
def eco(mensaje: str) -> str:
    """Repite el mensaje enviado"""
    return f"Eco: {mensaje}"

@mcp.tool()
def invertir_texto(texto: str) -> str:
    """Invierte el orden de una cadena de texto"""
    return texto[::-1]