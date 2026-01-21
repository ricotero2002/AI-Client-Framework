import os
import sys
import random

from typing import Annotated, Literal, Optional, Type, Any, TypedDict, Union, Dict, List
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Importaciones de LangChain y Pydantic
from langchain_core.tools import tool
from langchain_core.messages import RemoveMessage, HumanMessage, AIMessage, ToolMessage, BaseMessage, SystemMessage
from pydantic import BaseModel, Field
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.utilities import OpenWeatherMapAPIWrapper  
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from langsmith import traceable
import operator
import json
import uuid
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
import uvicorn
from fastapi import FastAPI
from langserve import add_routes
# Importar el ClientFactory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import your custom classes
from client_factory import ClientFactory
from prompt import Prompt
from chat import ChatSession 

# --- Configuration ---
PROVIDER = 'gemini' 
MODEL = 'gemini-2.5-flash'
KEEP_COUNT = 6
# Initialize Client once
client = ClientFactory.create_client(PROVIDER, langsmith=True)
client.select_model(MODEL)


# Configuración opcional para Wikipedia (para que no traiga documentos enormes)
os.environ["WIKIPEDIA_TOP_K_RESULTS"] = "1"
os.environ["WIKIPEDIA_MAX_DOC_CONTENT_LENGTH"] = "2000"
os.environ["WIKIPEDIA_LANG"] = "es"  # Configurar Wikipedia en español

# =============================================================================
# DEFINICIÓN DE HERRAMIENTAS (TOOLS)
# =============================================================================



# --- 1. Esquemas Pydantic (El contrato estricto) ---

class WeatherInput(BaseModel):
    """Input para consultar el clima."""
    location: str = Field(
        ..., 
        description="Ciudad y país mencionados. Ej: 'Bogotá, CO' o 'Madrid, ES'. Si no hay país, solo la ciudad."
    )
    country_code: Optional[str] = Field(
        None, 
        description="Código ISO de 2 letras si se menciona explícitamente. Ej: 'AR' para Argentina."
    )

class MathInput(BaseModel):
    """Input para operaciones matemáticas exactas."""
    a: int = Field(..., description="El primer número entero para la operación.")
    b: int = Field(..., description="El segundo número entero para la operación.")

class WikiInput(BaseModel):
    """Input para búsqueda de información."""
    query: str = Field(
        ..., 
        description="El tema específico a buscar. Extrae solo el sujeto principal (ej: 'Albert Einstein' en vez de 'quien fue Albert Einstein')."
    )

class AgentState(TypedDict):
    # La magia de 'add_messages' es que si le pasas un mensaje nuevo, 
    # no borra los anteriores, los agrega a la lista (append).
    messages: Annotated[list[BaseMessage], add_messages]

# --- 2. Implementación de Herramientas ---

@tool("get_weather", args_schema=WeatherInput)
@traceable(name="tool_weather")
def get_weather(location: str, country_code: Optional[str] = None) -> str:
    """
    Obtiene el clima actual. Usa esta herramienta cuando el usuario pregunte por temperatura, lluvia o condiciones meteorológicas.
    """
    try:
        # Construcción segura de la query
        query = f"{location},{country_code}" if country_code else location        
        # En producción usarías OpenWeatherMapAPIWrapper().run(query)
        # Aquí simulamos para que funcione sin API Key real si no la tienes
        wrapper = OpenWeatherMapAPIWrapper()
        return wrapper.run(query)
        
    except Exception as e:
        # Retornamos el error como string para que el Agente sepa que falló y lo intente de nuevo o avise al usuario
        return f"Error al obtener clima: {str(e)}. Pide al usuario que verifique la ciudad."

@tool("add_integers", args_schema=MathInput)
@traceable(name="tool_calculator")
def add_integers(a: int, b: int) -> str:
    """
    Suma dos números enteros. Úsalo para cálculos matemáticos simples mencionados explícitamente.
    """
    result = a + b
    return f"El resultado matemático de la suma es: {result}"

@tool("search_wikipedia", args_schema=WikiInput)
@traceable(name="tool_wikipedia")
def search_wikipedia(query: str) -> str:
    """
    Busca en Wikipedia datos históricos, biografías o definiciones.
    """
    try:
        wiki = WikipediaAPIWrapper()
        res = wiki.run(query)
        if not res or "No good Wikipedia Search Result" in res:
            return "No encontré información en Wikipedia sobre eso."
        return res
    except Exception as e:
        return f"Error conectando con Wikipedia: {str(e)}"

# Map string names to actual functions for execution
TOOL_MAP = {
    "get_weather": get_weather,
    "add_integers": add_integers,
    "search_wikipedia": search_wikipedia
}


# =============================================================================
# Definicion de agente
# =============================================================================
# --- System Prompt ---
# Defines the Agent's personality and instructions on how to use tools.
SYSTEM_INSTRUCTIONS = """
You are a helpful and smart AI assistant named "Agustin's Assistant".
You have access to specific tools to help answer user queries.

RULES:
1. If the user asks about weather, math, or factual info, USE THE TOOLS.
2. If the user greets you or asks general questions, answer directly without tools.
3. When using tools, output valid JSON in your response to specify the tool call.
4. If a tool returns an error, try to explain it to the user or ask for clarification.
5. Always answer in the same language as the user (Spanish preferred).
6. TOOL OUTPUTS: When you see a message starting with "[System: Resultado de la herramienta...]", that is the FACTUAL DATA you requested. 
7. CRITICAL - HANDLING IRRELEVANT RESULTS:
   - If a tool returns information that is NOT relevant to the user's question, DO NOT repeat the same search.
   - Instead, try a MORE SPECIFIC search term (e.g., if "libros de fantasía" fails, try "fantasía" o "libros").
   - If you've already tried 2 different search terms and still no relevant results, ADMIT you don't have the information.
   - NEVER repeat the exact same search query twice.
8. If the tool output is long, READ IT and SYNTHESIZE the answer for the user.
AVAILABLE TOOLS:
- get_weather(location: str, country_code: str [optional]): Get current weather.
- add_integers(a: int, b: int): Sum two integers.
- search_wikipedia(query: str): Search for factual information.

FORMAT FOR TOOL CALLING:
To call a tool, your response must be ONLY a JSON object with this structure:
{
  "tool": "tool_name",
  "arguments": { "arg1": "value1", ... }
}

If you do not need a tool, just write your text response normally.
"""

# =============================================================================
# HELPER FUNCTIONS FOR AGENT
# =============================================================================

def convert_messages_to_conversation_history(messages: List[BaseMessage]) -> List[Dict[str, str]]:
    """
    Convert LangChain messages to conversation history format.
    
    Args:
        messages: List of LangChain BaseMessage objects
        
    Returns:
        List of dicts with 'role' and 'content' keys
    """
    conversation_history = []
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            conversation_history.append({"role": "user", "content": str(msg.content)})
        elif isinstance(msg, AIMessage):
            # Skip empty AI messages from tool calls
            if msg.content:
                conversation_history.append({"role": "assistant", "content": str(msg.content)})
        elif isinstance(msg, ToolMessage):
            # Tool results are presented as user messages
            conversation_history.append({
                "role": "user", 
                "content": f"[Tool Result from {msg.name}]: {msg.content}"
            })
    
    return conversation_history


def parse_tool_call_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse LLM response to check if it's a tool call.
    Handles both plain JSON and markdown-wrapped JSON.
    
    Args:
        response_text: Raw response from LLM
        
    Returns:
        Dict with tool call info if it's a tool call, None otherwise
        Format: {"tool": "tool_name", "arguments": {...}}
    """
    # Clean the response: remove markdown code blocks if present
    cleaned_response = response_text.strip()
    
    # Remove markdown code block markers
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[7:]  # Remove ```json
    elif cleaned_response.startswith("```"):
        cleaned_response = cleaned_response[3:]  # Remove ```
    
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3]  # Remove trailing ```
    
    cleaned_response = cleaned_response.strip()
    
    try:
        tool_data = json.loads(cleaned_response)
        
        # Validate it's a proper tool call
        if isinstance(tool_data, dict) and "tool" in tool_data and "arguments" in tool_data:
            return tool_data
    except json.JSONDecodeError:
        # Not JSON, it's a normal response
        pass
    
    return None


# =============================================================================
# NODOS DEL GRAFO
# =============================================================================

@traceable(name="node_agent")
def agent_node(state: MessagesState):
    """
    The Brain: Decides what to do based on conversation history.
    Uses Prompt class and client.get_response() for consistency with framework.
    """
    messages = state["messages"]
    
    # Convert LangChain messages to conversation context format
    conversation_history = convert_messages_to_conversation_history(messages)
    
    # Ensure we have at least one user message
    if not any(m["role"] == "user" for m in conversation_history):
        return {"messages": [AIMessage(content="Lo siento, no recibí ningún mensaje.")]}
    
    try:
        # Create Prompt object using the framework's Prompt class
        prompt = Prompt(use_delimiters=False)
        
    # --- 1. AJUSTE AL PROMPT ---
        # Reforzamos la instrucción para que sepa cuándo parar    
        enhanced_system_instructions = (
            f"{SYSTEM_INSTRUCTIONS}\n\n"
            "CRITICAL INSTRUCTION: Once you receive a '[System: Resultado de la herramienta...]', "
            "ANALYZE that information immediately. "
            "If the information is sufficient to answer the user, DO NOT call the tool again. "
            "Answer the user directly using the information provided."
        )
        prompt.set_system(enhanced_system_instructions)

        # Set system instructions
        
        # Set conversation context (all previous messages)
        prompt.set_conversation_context(conversation_history)
        
        # The last user message is the current input
        # Extract it from conversation history
        last_user_msg = None
        for msg in reversed(conversation_history):
            if msg["role"] == "user":
                last_user_msg = msg["content"]
                break
        
        if last_user_msg:
            prompt.set_user_input(last_user_msg)
        
        # Call the LLM using the client's get_response method
        response_text, token_usage = client.get_response(prompt)
        
        print(f"[AGENT] Tokens used - Prompt: {token_usage.prompt_tokens}, Completion: {token_usage.completion_tokens}")
        
        # Check if the response is a tool call
        tool_data = parse_tool_call_response(response_text)
        
        if tool_data:
            # Extract tool info
            new_tool = tool_data["tool"]
            new_args = tool_data.get("arguments", {})
            
            # --- DETECCIÓN DE BUCLES ---
            # Revisamos el historial reciente para ver si está repitiendo acción
            # Buscamos el último AIMessage que haya sido una llamada a herramienta
            is_duplicate = False
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.additional_kwargs.get("tool_calls"):
                    last_call = msg.additional_kwargs["tool_calls"][0]["function"]
                    last_tool_name = last_call["name"]
                    # Parseamos argumentos para comparar diccionarios (orden no importa)
                    try:
                        last_tool_args = json.loads(last_call["arguments"])
                        
                        # SI ES IDÉNTICO -> BLOQUEAMOS
                        if new_tool == last_tool_name and new_args == last_tool_args:
                            is_duplicate = True
                            print(f"[WARNING] Bucle detectado: Intento repetido de {new_tool} con args {new_args}")
                            break
                    except:
                        pass
                    # Solo revisamos el último tool call
                    break
            
            # Si detectamos duplicado, forzamos respuesta en lugar de llamar tool
            if is_duplicate:
                print(f"[AGENT] Bucle detectado - Analizando si la información obtenida es relevante...")
                
                # Creamos un prompt especial para analizar si la info es relevante
                analysis_prompt = Prompt(use_delimiters=False)
                analysis_prompt.set_system(
                    "Eres un asistente analítico. Tu tarea es determinar si la información obtenida es RELEVANTE a la pregunta del usuario.\n"
                    "IMPORTANTE:\n"
                    "- Si la información ES relevante, responde al usuario con esa información.\n"
                    "- Si la información NO ES relevante (habla de otra cosa), sugiere una búsqueda alternativa MÁS ESPECÍFICA.\n"
                    "- Si ya se intentaron 2+ búsquedas sin éxito, admite que no tienes la información disponible."
                )
                analysis_prompt.set_conversation_context(conversation_history)
                analysis_prompt.set_user_input(
                    "Analiza si la información obtenida responde la pregunta del usuario. "
                    "Si no es relevante, sugiere un término de búsqueda más específico o admite que no tienes la información."
                )
                
                forced_response, _ = client.get_response(analysis_prompt)
                return {"messages": [AIMessage(content=forced_response)]}
            
            # Si NO es duplicado, procedemos normalmente con el tool call
            print(f"[AGENT] Quiere usar herramienta: {tool_data['tool']}")
            return {
                "messages": [
                    AIMessage(
                        content="", 
                        additional_kwargs={
                            "tool_calls": [{
                                "id": f"call_{uuid.uuid4().hex[:8]}",
                                "function": {
                                    "name": tool_data["tool"],
                                    "arguments": json.dumps(tool_data["arguments"])
                                },
                                "type": "function"
                            }]
                        }
                    )
                ]
            }
        
        # Normal text response
        print(f"[AGENT] Respuesta: {response_text[:80]}...")
        return {"messages": [AIMessage(content=response_text)]}
        
    except Exception as e:
        error_msg = f"Error en el agente: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return {"messages": [AIMessage(content=f"Lo siento, hubo un error: {str(e)}")]}


@traceable(name="node_tools")
def tools_node(state: MessagesState):
    """
    The Executor: Runs the tool requested by the Agent.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # Extract tool call info from the special AIMessage we created
    tool_calls = last_message.additional_kwargs.get("tool_calls", [])
    
    outputs = []
    
    for tool_call in tool_calls:
        function_name = tool_call["function"]["name"]
        arguments_str = tool_call["function"]["arguments"]
        arguments = json.loads(arguments_str)
        
        print(f"--- Ejecutando Tool: {function_name} con args: {arguments} ---")
        
        # Security check
        if function_name not in TOOL_MAP:
            result = f"Error: Tool '{function_name}' not found."
        else:
            try:
                # Execute the actual Python function
                # Note: We use .invoke() because your tools are LangChain @tool decorated
                # but since we have the raw function in TOOL_MAP, we can call it directly 
                # or via invoke depending on how you imported them. 
                # Given your tools.py, .invoke(arguments) is the safest LangChain way.
                tool_instance = TOOL_MAP[function_name]
                result = tool_instance.invoke(arguments)
            except Exception as e:
                result = f"Error executing tool: {str(e)}"

        # Create the ToolMessage (The observation)
        outputs.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        ))
        
    return {"messages": outputs}


@traceable(name="summarize_node")
def summarize_node(state: MessagesState):
    """
    Resume la conversación y elimina los mensajes antiguos para ahorrar contexto.
    """
    messages = state["messages"]
    
    # 1. Identificar qué mensajes vamos a resumir y cuáles mantener
    # Mantenemos los últimos 2 mensajes (la interacción más reciente) para que el chat no pierda fluidez
    # El resto (excepto el SystemMessage inicial si existe) se irá al resumen.
    keep_count = 2
    
    # Si hay muy pocos mensajes, no hacemos nada (protección extra)
    if len(messages) <= keep_count:
        return {}
        
    # Mensajes a resumir (todos menos los últimos 2)
    messages_to_summarize = messages[:-keep_count]
    
    # 2. Preparar el contenido para el LLM
    # Convertimos los objetos Message a texto plano para el prompt
    conversation_text = ""
    for msg in messages_to_summarize:
        role = "User" if isinstance(msg, HumanMessage) else "AI"
        if isinstance(msg, ToolMessage): role = "Tool"
        conversation_text += f"{role}: {msg.content}\n"

    # 3. Crear el Prompt de Sumarización
    prompt = Prompt(use_delimiters=False)
    
    # Detectamos si ya existe un resumen previo (buscando un SystemMessage antiguo)
    # Esto es opcional, pero ayuda al modelo a "actualizar" en vez de "recrear".
    current_summary = "No hay resumen previo."
    for msg in messages:
        if isinstance(msg, SystemMessage) and "Resumen de la conversación" in str(msg.content):
            current_summary = msg.content
            break
            
    system_instructions = (
        "Eres un experto en gestión de memoria para IAs. "
        "Tu trabajo es crear un resumen conciso de la conversación progresiva."
        "\nReglas:"
        "\n1. Mantén entidades clave: Nombres, Fechas, Ubicaciones, Preferencias del usuario."
        "\n2. Si se usaron herramientas (Tools), menciona brevemente el resultado relevante."
        "\n3. El resumen debe permitir a otra IA continuar la charla sin leer el historial completo."
    )
    
    prompt.set_system(system_instructions)
    prompt.set_user_input(
        f"Resumen actual: {current_summary}\n\n"
        f"Nuevos mensajes a incorporar:\n{conversation_text}\n\n"
        "Genera un nuevo resumen actualizado que combine todo."
    )

    # 4. Invocar al LLM
    print("--- 🧠 Generando resumen de memoria... ---")
    summary_text, _ = client.get_response(prompt)

    # 5. Crear las instrucciones de borrado para LangGraph
    # RemoveMessage(id=...) indica al checkpointer que elimine esos mensajes de la DB
    delete_messages = [RemoveMessage(id=m.id) for m in messages_to_summarize]
    
    # 6. Retornar: Nuevo Resumen (SystemMessage) + Orden de borrar viejos
    return {
        "messages": [
            SystemMessage(content=f"Resumen de la conversación: {summary_text}")
        ] + delete_messages
    }
# --- Router Logic ---
def should_continue(state: MessagesState) -> Literal["node_tools", "summarize_node", "__end__"]:
    """
    Decide el siguiente paso: Herramientas, Resumir o Terminar.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # PRIORIDAD 1: Si hay Tool Calls, vamos a Tools (Obligatorio)
    if last_message.additional_kwargs.get("tool_calls"):
        return "node_tools"
    
    # PRIORIDAD 2: Condición de Sumarización
    # Si tenemos más de 6 mensajes en el historial, activamos el nodo de resumen
    # antes de terminar el turno.
    if len(messages) > 6:
        return "summarize_node"
    
    # Si no pasa nada especial, terminamos y esperamos input del usuario
    return "__end__"

# =============================================================================
# 3. CONSTRUCCIÓN DEL GRAFO CON CHECKPOINTER
# =============================================================================

# Configurar persistencia (SQLite local)
# check_same_thread=False es CRÍTICO para evitar errores de threading con LangGraph
checkpointer = SqliteSaver(sqlite3.connect("agente_memory.sqlite", check_same_thread=False))

workflow = StateGraph(MessagesState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_node)
workflow.add_node("summarize_node", summarize_node) # <--- NUEVO
workflow.set_entry_point("agent")

workflow.add_conditional_edges("agent", should_continue, {
    "node_tools": "tools", 
    "summarize_node": "summarize_node", # <--- NUEVO CAMINO
    "__end__": END
})
workflow.add_edge("tools", "agent")
workflow.add_edge("summarize_node", "agent") # <--- NUEVO CAMINO


# AQUI OCURRE LA MAGIA: Pasamos el checkpointer al compilar
app = workflow.compile(checkpointer=checkpointer)

# =============================================================================
# 4. LOOP DE CHAT (STATEFUL)
# =============================================================================
def run_chat_loop():
    print("\n🤖 --- Agente Persistente (LangGraph) Iniciado ---")
    
    # Identificador de sesión. Si cambias esto, el agente "olvida" lo anterior.
    # En una app real, esto vendría del login del usuario.
    thread_id = "sesion_usuario_demo_4Da"
    
    # Configuración de ejecución
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"ID de Sesión: {thread_id} (El historial se guardará en 'agente_memory.sqlite')")

    while True:
        try:
            user_input = input("\nUsuario: ")
            if user_input.lower() in ["quit", "exit", "salir"]:
                print("Guardando estado y saliendo...")
                break

            # Solo enviamos el mensaje NUEVO.
            # LangGraph carga automáticamente el historial previo usando el thread_id.
            inputs = {"messages": [HumanMessage(content=user_input)]}

            print("(Procesando...)")
            
            # Ejecutamos el grafo con la config
            for event in app.stream(inputs, config=config):
                for key, value in event.items():
                    # Opcional: Mostrar feedback de qué nodo se está ejecutando
                    if key == "tools":
                        print("  ⚙️  Herramientas procesadas...")
            
            # Obtener el estado final para mostrar la respuesta
            snapshot = app.get_state(config)
            if snapshot.values and snapshot.values["messages"]:
                last_msg = snapshot.values["messages"][-1]
                if isinstance(last_msg, AIMessage):
                    print(f"\nAgente: {last_msg.content}")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_chat_loop()
'''
server = FastAPI(
    title="Servidor de Agentes Corporativos",
    version="1.0",
    description="API REST para interactuar con agentes LangGraph"
)

# Función para asegurar que siempre haya un thread_id
def add_default_thread_id(config: dict, request) -> dict:
    """Inyecta un thread_id por defecto si no se proporciona."""
    if "configurable" not in config:
        config["configurable"] = {}
    if "thread_id" not in config["configurable"]:
        # Usar un thread_id por defecto si no se proporciona
        config["configurable"]["thread_id"] = "default_session"
    return config

# Añadir rutas del grafo a la aplicación FastAPI
# Esto genera automáticamente endpoints como:
# POST /agente/invoke
# POST /agente/stream (Server-Sent Events)
# POST /agente/batch
add_routes(
    server,
    app,
    path="/agente",
    config_keys=["configurable"],  # Permite pasar el thread_id desde el cliente
    per_req_config_modifier=add_default_thread_id,  # Inyecta thread_id por defecto
    playground_type="chat" # Habilita una UI de depuración tipo chat en /agente/playground
)

# Servir el HTML
@server.get("/")
async def get():
    from fastapi.responses import HTMLResponse
    html_path = os.path.join(os.path.dirname(__file__), "index_simple.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    # Ejecutar el servidor uvicorn
    uvicorn.run(server, host="0.0.0.0", port=8000)


app_graph = workflow.compile(checkpointer=checkpointer)

app = FastAPI(title="Agente de Agustin")

# Exponer el grafo a través de LangServe
add_routes(
    app,
    app_graph,
    path="/agente",
    config_keys=["configurable"] # Permite pasar el thread_id desde el cliente
)

# Servir el HTML
@app.get("/")
async def get():
    from fastapi.responses import HTMLResponse
    html_path = os.path.join(os.path.dirname(__file__), "index_simple.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

'''