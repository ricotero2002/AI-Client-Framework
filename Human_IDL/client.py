#!/usr/bin/env python
import asyncio
import os
import sys
import json
import uuid
import datetime
from typing import Annotated, List, Literal, TypedDict, Optional, Any
from contextlib import AsyncExitStack

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Librerías
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, Field

# Imports propios
from client_factory import create_client
from prompt import Prompt, convert_langchain_tool_to_gemini

# --- CONFIGURACIÓN ---
load_dotenv(find_dotenv())
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    sys.exit("❌ ERROR: GEMINI_API_KEY no encontrada.")

MAX_ITERATIONS = 25  # Aumentamos un poco para tareas largas como mover archivos

# --- DATA MODELS ---
class PlanResponse(BaseModel):
    plan: str = Field(description="The detailed step-by-step plan.")
    is_safe: bool = Field(description="True if read-only, False if modifies files.")
    reasoning: str = Field(description="Reasoning for safety.")

# --- GOLDEN DATASET MANAGER ---
class GoldenDatasetManager:
    def __init__(self, filepath="golden_dataset.json", max_items=20):
        self.filepath = filepath
        self.max_items = max_items
        self.data = self._load()
    def _load(self):
        if not os.path.exists(self.filepath): return []
        try:
            with open(self.filepath, 'r') as f: return json.load(f)
        except: return []
    def save_feedback(self, query, plan, rejection_reason):
        self.data.append({"query": query, "rejected_plan": plan, "reason": rejection_reason})
        with open(self.filepath, 'w') as f: json.dump(self.data, f, indent=2)
    def get_formatted_feedback(self):
        if not self.data: return ""
        prompt = "\n### 🧠 LEARNINGS FROM PAST MISTAKES:\n"
        for i, item in enumerate(self.data[-3:]):
            prompt += f"- Mistake: For '{item['query']}', plan rejected because: '{item['reason']}'.\n"
        return prompt

feedback_manager = GoldenDatasetManager()

# --- ESTADO DEL GRAFO ---
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    target_dir: str
    current_plan: str
    is_safe: bool
    loop_step: int

# --- LÓGICA DEL CLIENTE ---
async def run_client():
    if len(sys.argv) < 2:
        sys.exit("Uso: python client.py <path_to_server_script>")
    
    server_path = os.path.abspath(sys.argv[1])
    server_params = StdioServerParameters(command="python", args=[server_path], env=os.environ.copy())

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            lc_tools = await load_mcp_tools(session)
            gemini_tools = [convert_langchain_tool_to_gemini(t) for t in lc_tools]
            
            client = create_client(provider='gemini', api_key=api_key)
            client.select_model('gemini-2.5-flash') 

            # --- NODOS ---

            def planner_node(state: AgentState):
                messages = state["messages"]
                target_dir = state.get("target_dir", ".")
                learnings = feedback_manager.get_formatted_feedback()
                
                # Prompt del Planificador (MEJORADO)
                system_instruction = (
                    f"You are an expert DevOps Windows assistant in: {target_dir}.\n"
                    f"{learnings}\n"
                    "INSTRUCTIONS:\n"
                    "1. Analyze the request.\n"
                    "2. Create a STEP-BY-STEP execution plan.\n"
                    "3. **ASSUME** the provided directory is correct. Do NOT include steps to 'ask user for confirmation' or 'check directory'. Start executing immediately.\n"
                    "4. IMPORTANT: You are on Windows PowerShell. Avoid 'ls', 'grep'. Use 'dir', 'Select-String', 'Move-Item', 'New-Item'.\n"
                    "5. Determine if it requires file modification (UNSAFE) or just reading (SAFE)."
                )
                
                prompt = Prompt().set_system(system_instruction).set_output_schema(PlanResponse)
                prompt.add_user_message(messages[-1].content if messages else "")
                
                response_text, _ = client.get_response(prompt)
                _, plan_data, _ = prompt.validate_response(response_text)
                
                if not plan_data:
                    return {"current_plan": "Error parsing plan", "is_safe": False}

                print(f"\n📋 PLAN GENERADO ({'SAFE' if plan_data.is_safe else 'UNSAFE'}):")
                print(f"{plan_data.plan}\n")
                
                # Inyectamos el plan aprobado como contexto
                return {
                    "messages": [AIMessage(content=f"APPROVED PLAN (EXECUTE IMMEDIATELY): {plan_data.plan}")], 
                    "current_plan": plan_data.plan, 
                    "is_safe": plan_data.is_safe,
                    "loop_step": 0
                }

            def human_approval_node(state: AgentState):
                return {"messages": [HumanMessage(content="Plan verified and approved by user. Proceed to execute step 1 immediately without further questions.")]}

            def agent_orchestrator_node(state: AgentState):
                messages = state["messages"]
                target_dir = state.get("target_dir", ".")
                plan = state.get("current_plan", "")
                step = state.get("loop_step", 0)
                
                system = (
                    f"You are a DevOps ReAct agent working in {target_dir}.\n"
                    f"You are executing this plan: {plan}\n"
                    f"Current Step: {step}/{MAX_ITERATIONS}\n\n"
                    "ENVIRONMENT RULES:\n"
                    "1. **OS:** Windows 10/11 (PowerShell).\n"
                    "2. **FORBIDDEN:** 'ls', 'cat', 'grep'. Use 'dir', 'Get-Content'.\n\n"
                    "CRITICAL PROTOCOL:\n"
                    f"1. **MANDATORY PATH:** Always set `path='{target_dir}'` in `run_server_command` unless you are moving files to a subfolder.\n"
                    "2. **NO CHAT:** Do NOT ask the user for confirmation. The plan is already approved. Just generate the FUNCTION CALL.\n"
                    "3. **ANTI-LOOP:** If you have already run a command, process its output. Do NOT run the exact same command twice.\n"
                    "4. **FINISH:** When done, output a text summary."
                )
                
                prompt = Prompt().set_system(system).set_tools(gemini_tools)
                
                # --- LOGICA DE HISTORIAL Y ANTI-BUCLE ---
                last_tool_call = None
                
                for msg in messages:
                    if isinstance(msg, HumanMessage):
                        prompt.add_user_message(msg.content)
                    elif isinstance(msg, AIMessage):
                        if msg.tool_calls:
                            tc = msg.tool_calls[0]
                            last_tool_call = tc # Guardamos la última herramienta llamada por el AI
                            prompt.add_assistant_message(f"Thought: I executed '{tc['name']}' with args: {tc['args']}")
                        else:
                            prompt.add_assistant_message(msg.content)
                    elif isinstance(msg, ToolMessage):
                        prompt.add_tool_message(
                            tool_name=msg.name, 
                            output=str(msg.content), 
                            tool_call_id=msg.tool_call_id
                        )
                        print(f"🔧 Tool Output ({msg.name}): {str(msg.content)[:200]}...") # Log tool output

                response_text, _ = client.get_response(prompt)
                print("Respuesta del modelo, en iteracion",step," es: ",response_text)
                try:
                    data = json.loads(response_text)
                    if isinstance(data, dict) and "function_call" in data:
                        fc = data["function_call"]
                        
                        # === PROTECCIÓN ANTI-BUCLE ===
                        # Si la herramienta y los argumentos son IDÉNTICOS a la última vez
                        if last_tool_call and fc["name"] == last_tool_call["name"] and fc["args"] == last_tool_call["args"]:
                            print("🔄 Bucle detectado (Llamada repetida). Forzando corrección...")
                            return {
                                "messages": [
                                    # Mensaje de sistema falso para "despertar" al modelo
                                    HumanMessage(content=f"SYSTEM ALERT: You just executed '{fc['name']}' with args {fc['args']} and got the result. Do NOT repeat it. Analyze the output above or move to the next step of the plan.")
                                ],
                                "loop_step": step + 1
                            }
                        # ==============================

                        return {
                            "messages": [AIMessage(
                                content="", 
                                tool_calls=[{
                                    "name": fc["name"],
                                    "args": fc["args"],
                                    "id": str(uuid.uuid4()),
                                    "type": "tool_call"
                                }]
                            )],
                            "loop_step": step + 1
                        }
                except:
                    pass
                
                # Detección de "Falsa Ejecución" (Dice que hará algo pero no manda JSON)
                if "I will execute" in response_text or "I will run" in response_text:
                     return {
                        "messages": [
                            AIMessage(content=response_text),
                            HumanMessage(content="SYSTEM WARNING: Do not talk about actions. Return the JSON Function Call to execute them.")
                        ],
                        "loop_step": step + 1
                     }

                return {
                    "messages": [AIMessage(content=response_text)],
                    "loop_step": step + 1
                }

            tool_node = ToolNode(lc_tools)

            workflow = StateGraph(AgentState)
            workflow.add_node("planner", planner_node)
            workflow.add_node("human_approval", human_approval_node)
            workflow.add_node("agent", agent_orchestrator_node)
            workflow.add_node("tools", tool_node)

            workflow.add_edge(START, "planner")

            def route_safety(state):
                return "agent" if state["is_safe"] else "human_approval"

            workflow.add_conditional_edges("planner", route_safety)
            workflow.add_edge("human_approval", "agent")

            def should_continue(state):
                step = state.get("loop_step", 0)
                if step >= MAX_ITERATIONS: return END
                
                last_message = state["messages"][-1]
                # Si el último mensaje es Humano (Alerta de sistema), vuelve al agente para que corrija
                if isinstance(last_message, HumanMessage):
                    return "agent"
                
                if last_message.tool_calls: return "tools"
                return END

            workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "agent": "agent", END: END})
            workflow.add_edge("tools", "agent")

            checkpointer = MemorySaver()
            app = workflow.compile(checkpointer=checkpointer, interrupt_before=["human_approval"])

            print(f"✅ Cliente ReAct (Anti-Loop + No Confirm) Iniciado.")
            thread_id = "session_fixed_v4_2"
            config = {"configurable": {"thread_id": thread_id}}

            while True:
                user_input = input("\n👤 Query (o 'quit'): ")
                if user_input.lower() in ["quit", "exit"]: break
                
                target_dir = input("📂 Directorio (Enter actual): ").strip() or os.getcwd()
                
                initial_state = {
                    "messages": [HumanMessage(content=user_input)],
                    "target_dir": target_dir,
                }

                async for event in app.astream(initial_state, config=config):
                    if 'agent' in event:
                        msgs = event['agent']['messages']
                        for msg in msgs:
                            if isinstance(msg, AIMessage):
                                if msg.tool_calls:
                                    print(f"🤖 Agente decide: {msg.tool_calls[0]['name']} | Args: {msg.tool_calls[0]['args']}")
                                else:
                                    print(f"🤖 Agente piensa: {msg.content[:100]}...")
                            if isinstance(msg, HumanMessage):
                                print(f"⚠️ Sistema corrige: {msg.content[:100]}...") # Ver alertas del sistema
                                
                    if 'tools' in event:
                        print("⚡ Herramienta ejecutada.")

                snapshot = await app.aget_state(config)
                
                if snapshot.next:
                    plan = snapshot.values.get("current_plan", "")
                    print("\n⚠️  ALERTA DE SEGURIDAD")
                    print(f"Plan: {plan}")
                    if input("¿Autorizar? (s/n): ").lower() == 's':
                        print("🚀 Ejecutando...")
                        async for event in app.astream(None, config=config):
                            if 'agent' in event:
                                msgs = event['agent']['messages']
                                for msg in msgs:
                                    if isinstance(msg, AIMessage) and msg.tool_calls:
                                        print(f"🤖 Agente decide: {msg.tool_calls[0]['name']}")
                    else:
                        reason = input("❌ Razón: ")
                        feedback_manager.save_feedback(user_input, plan, reason)
                        continue 

                final_state = await app.aget_state(config)
                if final_state.values.get("loop_step", 0) >= MAX_ITERATIONS:
                     print("🚫 Limite de iteraciones alcanzado.")

                if final_state.values["messages"]:
                    last_msg = final_state.values["messages"][-1]
                    if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
                        print(f"\n🏁 RESULTADO FINAL:\n{last_msg.content}")

if __name__ == "__main__":
    asyncio.run(run_client())