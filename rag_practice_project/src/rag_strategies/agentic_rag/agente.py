import os
import sys
from pathlib import Path

# Add project root to sys.path for framework imports
root_path = str(Path(__file__).parent.parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import json
import uuid
from typing import TypedDict, Annotated, List, Dict, Any, Optional

# Local imports (agentic_rag folder)
from tools import optimize_query, retrieve_documents, rerank_documents

# Framework imports (from IA root)
from prompt import Prompt
from client_factory import ClientFactory

# Definir estado
class AgenticRAGState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]



# --- Configuration ---
PROVIDER = 'gemini' 
MODEL = 'gemini-2.5-flash'
KEEP_COUNT = 6
# Initialize Client for agent
client = ClientFactory.create_client(PROVIDER, langsmith=True)
client.select_model(MODEL)

# definir tools
TOOL_MAP = {
    "optimize_query": optimize_query,
    "retrieve_documents": retrieve_documents,
    "rerank_documents": rerank_documents
}

# definir prompt del agente
SYSTEM_INSTRUCTIONS = """
You're an expert assistant in vegetarian recipes.
You have access to specific tools to help answer user queries.
RULES:
1.WORKFLOW:
    1. Call 'optimize_query' for new requests.
    2. Call 'retrieve_documents' after optimization.
    3. Call 'rerank_documents' after retrieval.
    4. Answer the user based on the ranked documents.

2.IMPORTANT:
    - You do NOT need to repeat the arguments for retrieve/rerank. Just call the tool name, and the system will auto-fill the data from the previous step.
    - If you need to search, just output: {"tool": "optimize_query", "arguments": {"query": "user request"}}
    - If optimization is done, output: {"tool": "retrieve_documents", "arguments": {}}
    - If retrieval is done, output: {"tool": "rerank_documents", "arguments": {}}
    - If retrieval is done but you didn't retrive any document don't do a rerank_documents but answer that you don't have any recipe of that type.
3. DATA FLOW:
   - Never make up data. Use exactly what the previous tool gave you.
4. FORMAT:
   Response must be ONLY a JSON object:
   { "tool": "tool_name", "arguments": { ... } }
   Or plain text if answering.
5. If the user asks about vegetarian recipes, USE THE TOOLS.
6. If the user greets you or asks general questions, answer directly without tools.
7. Always answer in the same language as the user (Spanish preferred).
8. If the user said that some ingredients don't need to be used all of them, if you can't find any recipe you can try using fewer ingredients or only the most important ones in the recipe.
AVAILABLE TOOLS:
- optimize_query(query: str): Optimizes the user's query, returns the optimized query for search in the database.
- retrieve_documents(query: str): Retrieves documents from the database using the optimized query.
- rerank_documents(query: str): Reranks documents by relevance to the user's query.

"""



# Funciones auxiliares para el agente
# =============================================================================
# --- HELPER: Find data in history ---
def get_last_tool_output(messages: List[BaseMessage], tool_name: str) -> Optional[Dict]:
    """Scans history backwards to find the last output of a specific tool."""
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == tool_name:
            try:
                # Try to parse content as JSON
                return json.loads(msg.content)
            except:
                # If it's a string, return as dict
                return {"raw_content": msg.content}
    return None

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
    """
    cleaned_response = response_text.strip()
    
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[7:]
    elif cleaned_response.startswith("```"):
        cleaned_response = cleaned_response[3:]
    
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3]
    
    cleaned_response = cleaned_response.strip()
    
    try:
        tool_data = json.loads(cleaned_response)
        if isinstance(tool_data, dict) and "tool" in tool_data and "arguments" in tool_data:
            return tool_data
    except json.JSONDecodeError:
        pass
    
    return None

# Agent node
def agent_node(state: AgenticRAGState):
    messages = state["messages"]
    
    # 1. Prompt Construction
    conversation_history = convert_messages_to_conversation_history(messages)
    prompt = Prompt(use_delimiters=False)
    prompt.set_system(SYSTEM_INSTRUCTIONS)
    prompt.set_conversation_context(conversation_history)
    
    # Check if we should inject a hint based on previous tool
    last_msg = messages[-1]
    user_input = last_msg.content if messages else ""
    
    if isinstance(last_msg, ToolMessage):
        if last_msg.name == "optimize_query":
            prompt.set_user_input(f"{user_input}\n\n[SYSTEM]: Optimization done. Now call 'retrieve_documents'.")
        elif last_msg.name == "retrieve_documents":
            prompt.set_user_input(f"{user_input}\n\n[SYSTEM]: Retrieval done. Now call 'rerank_documents'.")
        elif last_msg.name == "rerank_documents":
            prompt.set_user_input(f"{user_input}\n\n[SYSTEM]: Reranking done. Now answer the user.")
    else:
        prompt.set_user_input(user_input)

    # 2. LLM Call
    response_text, _ = client.get_response(prompt)
    tool_data = parse_tool_call_response(response_text)
    
    if tool_data:
        tool_name = tool_data.get("tool")
        tool_args = tool_data.get("arguments", {})
        
        print(f"--- 🤖 Agente quiere usar: {tool_name} ---")

        # --- AUTO-FETCH LOGIC (The Fix) ---
        
        # CASE A: RETRIEVE DOCUMENTS
        # Instead of trusting the LLM's args, we fetch the last 'optimize_query' output
        if tool_name == "retrieve_documents":
            print("   ↳ 🔄 Auto-fetching optimization data from history...")
            optimized_data = get_last_tool_output(messages, "optimize_query")
            
            if optimized_data:
                # We OVERWRITE the arguments with the correct data from history
                tool_args = optimized_data
                print(f"   ↳ ✅ Arguments injected: {list(tool_args.keys())}")
            else:
                return {"messages": [AIMessage(content="Error: I need to run 'optimize_query' before retrieving documents.")]}

        # CASE B: RERANK DOCUMENTS
        # Needs 'query' (from optimize) and 'retrieval_results_json' (from retrieve)
        elif tool_name == "rerank_documents":
            print("   ↳ 🔄 Auto-fetching retrieval data from history...")
            
            # 1. Get Query from Optimize Step
            opt_data = get_last_tool_output(messages, "optimize_query")
            query_str = opt_data.get("query") if opt_data else None
            
            # 2. Get Documents from Retrieve Step
            # Note: We retrieve the raw content string or dict to pass to reranker
            last_retrieval_msg = next((m for m in reversed(messages) if isinstance(m, ToolMessage) and m.name == "retrieve_documents"), None)
            
            if query_str and last_retrieval_msg:
                tool_args = {
                    "query": query_str,
                    "retrieval_results_json": last_retrieval_msg.content # Passing the raw JSON string content
                }
                print(f"   ↳ ✅ Arguments injected for Rerank.")
            else:
                return {"messages": [AIMessage(content="Error: Missing data flow. Need optimization and retrieval results first.")]}

        # Construct the final tool call with CORRECTED arguments
        return {
            "messages": [
                AIMessage(
                    content="",
                    additional_kwargs={
                        "tool_calls": [{
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "function": {
                                "name": tool_name,
                                # Here we dump the Python dict 'tool_args' which contains the injected data
                                "arguments": json.dumps(tool_args) 
                            },
                            "type": "function"
                        }]
                    }
                )
            ]
        }
    
    # If no tool call, return text
    return {"messages": [AIMessage(content=response_text)]}
    
# Tool execution node
tools_node = ToolNode(list(TOOL_MAP.values()))

# Routing
def should_continue(state: AgenticRAGState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "additional_kwargs") and last_message.additional_kwargs.get("tool_calls"):
        return "tools"
    return END
# Build graph
workflow = StateGraph(AgenticRAGState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")
# Checkpointer para persistencia
checkpointer = SqliteSaver(
    sqlite3.connect("agentic_rag_memory.sqlite", check_same_thread=False)
)
# Compile
app = workflow.compile(checkpointer=checkpointer)

# =============================================================================
# 4. LOOP DE CHAT (STATEFUL)
# =============================================================================
def run_chat_loop():
    print("\n🤖 --- Agente Persistente (LangGraph) Iniciado ---")
    
    # Identificador de sesión. Si cambias esto, el agente "olvida" lo anterior.
    # En una app real, esto vendría del login del usuario.
    thread_id = "session_agentic_rag_demo_11"
    
    # Configuración de ejecución
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"ID de Sesión: {thread_id} (El historial se guardará en 'agentic_rag_memory.sqlite')")

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