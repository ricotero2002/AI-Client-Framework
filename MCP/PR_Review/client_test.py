import asyncio
import sys
import os

# Add root directory to sys.path to allow importing from parent directories
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from client_factory import ClientFactory
from prompt import Prompt
# Define los argumentos de prueba aquí para no tocar el código cada vez
REPO_OWNER = "ricotero2002"
REPO_NAME = "AI-Client-Framework"
PR_NUMBER = 1
# --- Configuration ---
PROVIDER = 'gemini' 
MODEL = 'gemini-2.0-flash-exp'

# Initialize Client for agent
client = ClientFactory.create_client(PROVIDER, langsmith=False)
client.select_model(MODEL)

async def run_client():
    # 1. Configurar los parámetros para lanzar el servidor
    # Usamos sys.executable para asegurarnos de usar el mismo intérprete de Python
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["pr_analyzer.py"], # El archivo de tu servidor
        env=os.environ.copy() # Heredar variables de entorno (importante para el .env)
    )

    print(f"🔌 Conectando al servidor MCP en: {server_params.command} {server_params.args}...")

    try:
        # 2. Iniciar la conexión stdio y la sesión
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                
                # 3. Inicializar la sesión
                await session.initialize()
                print("✅ Sesión MCP inicializada correctamente.\n")

                # --- PRUEBA 1: Listar Herramientas Disponibles ---
                print("🛠️  Listando herramientas disponibles...")
                tools = await session.list_tools()
                for tool in tools.tools:
                    print(f"   - {tool.name}: {tool}")
                print("-" * 50)

                # --- PRUEBA 2: Ejecutar 'fetch_pr' ---
                print(f"📥 Probando herramienta 'fetch_pr' ({REPO_OWNER}/{REPO_NAME}#{PR_NUMBER})...")
                
                # Llamada a la herramienta
                result_pr = await session.call_tool(
                    "fetch_pr",
                    arguments={
                        "repo_owner": REPO_OWNER,
                        "repo_name": REPO_NAME,
                        "pr_number": PR_NUMBER
                    }
                )

                # Analizar resultado (mcp devuelve una lista de contenidos)
                if result_pr.content and len(result_pr.content) > 0:
                    pr_data = result_pr.content[0].text
                    print(f"📄 Resultado recibido (Primeros 200 caracteres):\n{pr_data[:200]}...")
                else:
                    print("⚠️ No se recibió contenido o hubo un error.")
                print("-" * 50)

                # --- PRUEBA 3: Ejecutar 'create_notion_page' ---
                # ¡OJO! Esto creará una página real en tu Notion si las credenciales son válidas.
                # Puedes comentar esta sección si solo quieres probar GitHub.
                
                page_title = f"Análisis PR #{PR_NUMBER} - Test MCP"
                print(f"📝 Probando herramienta 'create_notion_page' ('{page_title}')...")
                
                prompt = Prompt(use_delimiters=False)
                prompt.set_system("Sos un experto en análisis de pull requests. Analizá el siguiente pull request y generá un análisis detallado. Regla: el texto debe tener menos de `2000` caracteres")
                prompt.set_user_input(f"Data cruda a analizar: {pr_data}")
                response,_ = client.get_response(prompt)
                print(f"Respuesta del modelo: {response}")

                result_notion = await session.call_tool(
                    "create_notion_page",
                    arguments={
                        "title": page_title,
                        "content": f"Análisis automático generado por el cliente de prueba MCP.\nDatos crudos: {str(response)}"
                    }
                )

                if result_notion.content:
                    print(f"✅ Respuesta de Notion: {result_notion.content[0].text}")
                
    except Exception as e:
        print(f"\n❌ Error durante la ejecución del cliente: {str(e)}")

if __name__ == "__main__":
    # Ejecutar el loop asíncrono
    asyncio.run(run_client())