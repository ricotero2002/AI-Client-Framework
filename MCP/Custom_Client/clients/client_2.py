import asyncio
import json
import os
from typing import TypedDict, List
from dotenv import load_dotenv, find_dotenv

# FastMCP Client - API Moderna
from fastmcp import Client

# LangGraph y LangChain Core
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import Tool

load_dotenv(find_dotenv())

# --- CONFIGURACIÓN LLM ---
class MyCustomLLM:
    def __init__(self):
        from langchain_google_genai import ChatGoogleGenerativeAI
        self._internal_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )

    async def ainvoke(self, prompt: str):
        response = await self._internal_model.ainvoke(prompt)
        return response.content

# --- ADAPTADOR (EL PUENTE QUE FALTABA) ---
class FastMCPToLangChainAdapter:
    """Convierte una herramienta de FastMCP Client a algo ejecutable por el agente."""
    def __init__(self, client: Client, tool_info):
        self.client = client
        self.name = tool_info.name
        self.description = tool_info.description or "Sin descripción"
        # Guardamos el esquema para que el prompt sepa qué argumentos pedir
        self.args = tool_info.inputSchema 

    async def ainvoke(self, args: dict):
        """Ejecuta la herramienta usando el cliente moderno."""
        # fastmcp.Client.call_tool devuelve un objeto Result
        result = await self.client.call_tool(self.name, args)
        
        # Extraemos el texto del resultado (puede venir en varios bloques)
        output_text = []
        if hasattr(result, 'content'):
            for content in result.content:
                if hasattr(content, 'text'):
                    output_text.append(content.text)
        
        return "\n".join(output_text) if output_text else str(result)

# --- ESTADO DEL GRAFO ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    tools_map: dict 

# --- PROMPTING ---
def construct_system_prompt(tools_wrappers):
    """Genera el prompt usando nuestros adaptadores manuales."""
    # Extraemos info de los wrappers
    tools_desc = []
    for t in tools_wrappers:
        # Formateamos argumentos de forma simple para el LLM
        schema_str = json.dumps(t.args.get("properties", {}))
        tools_desc.append(f"- {t.name}: {t.description} (Args: {schema_str})")
    
    tools_block = "\n".join(tools_desc)
    
    prompt = f"""
    Eres un asistente inteligente conectado a herramientas matemáticas.
    DEBES responder SIEMPRE en el idioma en que el usuario te hable.
    
    HERRAMIENTAS DISPONIBLES:
    {tools_block}

    FORMATO OBLIGATORIO:
    Para usar una herramienta, responde SOLO con JSON puro (SIN bloques de código markdown):
    {{
        "action": "nombre_herramienta",
        "action_input": {{ "arg1": valor1, "arg2": valor2 }}
    }}

    IMPORTANTE: 
    - NO uses ```json ni ningún otro formato markdown. Solo el JSON directo.
    - Cuando recibas un resultado de una herramienta, presenta el resultado de forma clara y concisa en ESPAÑOL.
    - Si no necesitas herramienta, responde con texto normal.
    """
    return prompt

# --- NODOS DEL GRAFO ---
async def node_call_llm(state: AgentState):
    messages = state["messages"]
    conversation_history = "\n".join([f"{m.type.upper()}: {m.content}" for m in messages])
    
    my_llm = MyCustomLLM()
    response_text = await my_llm.ainvoke(conversation_history)
    
    # Limpiar markdown si el LLM lo agregó
    cleaned_response = response_text.strip()
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
    elif cleaned_response.startswith("```"):
        cleaned_response = cleaned_response.replace("```", "").strip()
    
    return {"messages": [AIMessage(content=cleaned_response)]}

async def node_execute_tool(state: AgentState):
    last_message = state["messages"][-1]
    content = last_message.content.strip()
    try:
        tool_call = json.loads(content)
        tool_name = tool_call.get("action")
        tool_args = tool_call.get("action_input", {})
        
        print(f"\n⚙️ Ejecutando herramienta: {tool_name} con {tool_args}")
        tools_map = state["tools_map"]
        
        if tool_name in tools_map:
            # Aquí llamamos al método .ainvoke de nuestro Adaptador
            result = await tools_map[tool_name].ainvoke(tool_args)
            return {"messages": [HumanMessage(content=f"RESULTADO: {result}")]}
        else:
            return {"messages": [HumanMessage(content=f"Error: Herramienta {tool_name} no encontrada.")]}
    except json.JSONDecodeError:
        return {"messages": [HumanMessage(content="Error: Formato JSON inválido.")]}
    except Exception as e:
         return {"messages": [HumanMessage(content=f"Error ejecutando herramienta: {str(e)}")]}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    content = last_message.content.strip()
    if content.startswith("{") and '"action":' in content:
        return "tools"
    return "end"

# --- MAIN ---
async def main():
    # 1. URL CORRECTA: Debe terminar en /sse
    SERVER_URL = "http://localhost:8000/math/mcp"
    
    print(f"🔌 Conectando a {SERVER_URL}...")
    
    # Usamos el cliente moderno de FastMCP
    client = Client(SERVER_URL)
    
    async with client:
        # 2. CARGA DE HERRAMIENTAS MANUAL
        # Obtenemos la lista cruda de herramientas
        mcp_tools_info = await client.list_tools()
        
        # Creamos nuestros adaptadores y el mapa
        tools_map = {}
        tool_wrappers = []
        
        for info in mcp_tools_info:
            adapter = FastMCPToLangChainAdapter(client, info)
            tools_map[info.name] = adapter
            tool_wrappers.append(adapter)
            
        print(f"🛠️ Tools cargadas: {list(tools_map.keys())}")

        # 3. DEFINIR GRAFO
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", node_call_llm)
        workflow.add_node("tools", node_execute_tool)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
        workflow.add_edge("tools", "agent")
        
        app = workflow.compile()
        
        # 4. LOOP DE CHAT
        sys_prompt = construct_system_prompt(tool_wrappers)
        chat_history = [SystemMessage(content=sys_prompt)]
        
        print("✅ Agente listo. Escribe 'salir' para terminar.")
        
        while True:
            user_input = input("\nUsuario: ")
            if user_input.lower() in ["salir", "exit"]: break
            
            chat_history.append(HumanMessage(content=user_input))
            
            async for event in app.astream({"messages": chat_history, "tools_map": tools_map}, config={"recursion_limit": 10}):
                pass 
            
            final_state = event[list(event.keys())[0]]
            last_response = final_state["messages"][-1]
            print(f"🤖 Agente: {last_response.content}")
            chat_history.append(last_response)

if __name__ == "__main__":
    asyncio.run(main())