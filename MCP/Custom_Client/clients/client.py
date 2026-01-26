#!/usr/bin/env python
import asyncio
import os
import sys
import json
from contextlib import AsyncExitStack

# Librerías de MCP y LangChain
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv, find_dotenv

# 1. CARGA ROBUSTA DE ENV VARS
# Busca el archivo .env automáticamente (subiendo directorios si es necesario)
env_file = find_dotenv()
if env_file:
    load_dotenv(env_file)
    print(f"✅ Archivo .env cargado desde: {env_file}")
else:
    print("⚠️ ADVERTENCIA: No se encontró archivo .env. Asegúrate de tener las API KEYS en el sistema.")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERROR CRÍTICO: GOOGLE_API_KEY no se encontró en las variables de entorno.")
    sys.exit(1)

class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "content"):
            return {"type": o.__class__.__name__, "content": o.content}
        return super().default(o)

# 2. INICIALIZACIÓN DEL MODELO
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    temperature=0,
    max_retries=2,
    google_api_key=api_key 
)

if len(sys.argv) < 2:
    print("Uso: python client.py <path_to_server_script>")
    sys.exit(1)

# 3. RUTAS ABSOLUTAS PARA EL SERVIDOR
# Convertimos la ruta relativa del servidor a absoluta para evitar errores en el subproceso
server_script_path = os.path.abspath(sys.argv[1])
server_dir = os.path.dirname(server_script_path)

if not os.path.exists(server_script_path):
    print(f"❌ Error: No se encuentra el archivo del servidor en: {server_script_path}")
    sys.exit(1)

print(f"🔌 Conectando al servidor en: {server_script_path}")

# Configuramos el servidor asegurando que herede las variables de entorno (API KEYS)
server_params = StdioServerParameters(
    command="python", # Asegúrate de que este python tenga las librerías del servidor instaladas
    args=[server_script_path],
    env=os.environ.copy() # Importante: Pasar las variables de entorno al servidor
)

async def run_agent():
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Cargar herramientas del servidor MCP
                tools = await load_mcp_tools(session)
                print(f"🛠️ Herramientas cargadas: {[t.name for t in tools]}")
                
                agent = create_react_agent(llm, tools)
                print("✅ Cliente MCP Iniciado. Escribe 'quit' para salir.")
                
                while True:
                    query = await asyncio.get_event_loop().run_in_executor(None, input, "\nQuery: ")
                    if query.strip().lower() in ["quit", "exit"]:
                        break
                    
                    try:
                        response = await agent.ainvoke({"messages": query})
                        # Intentar imprimir solo el contenido del último mensaje
                        last_message = response["messages"][-1]
                        print("\nRespuesta:")
                        print(last_message.content)
                    except Exception as e:
                        print(f"❌ Error procesando respuesta: {e}")

    except Exception as e:
        print(f"\n❌ Error de conexión con el servidor MCP: {e}")
        print("Tip: Verifica que 'terminal_server.py' no tenga errores de sintaxis y sus librerías estén instaladas.")

if __name__ == "__main__":
    asyncio.run(run_agent())