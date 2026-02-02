#!/usr/bin/env python
import asyncio
import os
import sys
import json
import uuid
import datetime
import shutil
import tempfile
import traceback
from typing import Annotated, List, Literal, TypedDict, Optional, Union
from contextlib import AsyncExitStack

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Librerías
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage, RemoveMessage
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

MAX_ITERATIONS = 20
MAX_BACKUP_SIZE_MB = 500
AUDIT_LOG_FILE = "execution_audit.log"

# Ejemplos para el PLANNER (Input Usuario -> Output JSON esperado)
PLANNER_EXAMPLES = [
    {
        "user": "Busca la imagen más pesada y bórrala.",
        "assistant": json.dumps({
            "plan": "1. Identify and delete the largest image in one shot using PowerShell piping: `Get-ChildItem -Include *.png,*.jpg -Recurse | Sort-Object Length -Descending | Select-Object -First 1 | Remove-Item -Force -PassThru`.\n2. Verify deletion using `Test-Path`.\n3. Output the result.",
            "is_safe": False
        })
    },
    {
        "user": "Listame los 3 archivos más grandes.",
        "assistant": json.dumps({
            "plan": "1. Execute command: `Get-ChildItem -File -Recurse | Sort-Object Length -Descending | Select-Object -First 3 | Select-Object Name, @{Name='Size(MB)';Expression={$_.Length / 1MB}}`.\n2. Return the text output directly.",
            "is_safe": True
        })
    },
    {
        "user": "Crea una carpeta 'Logs' si no existe.",
        "assistant": json.dumps({
            "plan": "1. Check and create directory in one command: `if (-not (Test-Path 'Logs')) { New-Item -ItemType Directory -Path 'Logs' }`.\n2. Verify existence.",
            "is_safe": False
        })
    }
]

# Ejemplos para el AGENTE (Input Usuario -> Output ReAct/Tool Call)
AGENT_EXAMPLES = [
    {
        "user": "Borra el archivo 'error.log'.",
        "assistant": """Thought: User wants to delete a specific file. I will delete it and verify immediately in a single sequence if possible, or sequentially.
Tool Call: run_server_command(command="Remove-Item 'error.log' -Force; Write-Output 'Deleted'; Test-Path 'error.log'")"""
    },
    {
        "user": "¿Cual es el archivo más grande?",
        "assistant": """Thought: I should use PowerShell sorting to avoid listing all files to the LLM context.
Tool Call: run_server_command(command="Get-ChildItem -File | Sort-Object Length -Descending | Select-Object -First 1 | Select-Object Name, Length")"""
    }
]

# --- UTILIDAD DE DEBUG VISUAL ---
def print_debug_step(step_type: str, content: str, extra: str = ""):
    colors = {
        "PLAN": "\033[96m", "TOOL": "\033[93m", "OUTPUT": "\033[90m", 
        "ERROR": "\033[91m", "SUCCESS": "\033[92m", "RESET": "\033[0m",
        "AUDIT": "\033[95m"
    }
    clean_content = str(content)
    if step_type == "OUTPUT":
        try:
            import ast
            if clean_content.strip().startswith("[") and "type" in clean_content:
                data = ast.literal_eval(clean_content)
                if isinstance(data, list) and len(data) > 0 and 'text' in data[0]:
                    clean_content = data[0]['text']
        except: pass
        if len(clean_content) > 500: clean_content = clean_content[:500] + "... [truncado]"

    prefix = f"{colors.get(step_type, '')}[{step_type}]{colors['RESET']}"
    print(f"{prefix} {clean_content} {extra}")

# --- AUDIT LOGGER ---
class AuditLogger:
    @staticmethod
    def log(entry_type: str, content: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{entry_type}]\n{content}\n{'-'*80}\n"
        try:
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            print_debug_step("ERROR", f"No se pudo escribir en log: {e}")

# --- BACKUP MANAGER ---
class BackupManager:
    active_backups = set()
    @staticmethod
    def get_dir_size_mb(path):
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp): total += os.path.getsize(fp)
        return total / (1024 * 1024)
    @staticmethod
    def create_backup(target_dir):
        try:
            if not os.path.exists(target_dir): return None
            if BackupManager.get_dir_size_mb(target_dir) > MAX_BACKUP_SIZE_MB: return None
            backup_path = tempfile.mkdtemp(prefix="agent_backup_")
            import distutils.dir_util
            distutils.dir_util.copy_tree(target_dir, backup_path)
            print_debug_step("SUCCESS", f"Backup temporal creado en: {backup_path}")
            BackupManager.active_backups.add(backup_path)
            return backup_path
        except: return None
    @staticmethod
    def restore_backup(backup_path, target_dir):
        if not backup_path or not os.path.exists(backup_path): return False
        try:
            import distutils.dir_util
            # Limpiar directorio destino antes de restaurar para evitar archivos huerfanos mezclados
            # OJO: Esto puede ser peligroso si el backup falló. Haremos copy_tree con update=1 por seguridad basica,
            # pero idealmente deberíamos limpiar. Por ahora mantengo logica conservadora.
            distutils.dir_util.copy_tree(backup_path, target_dir, update=1)
            print_debug_step("SUCCESS", f"Backup restaurado desde: {backup_path}")
            return True
        except Exception as e:
            print_debug_step("ERROR", f"Fallo restaurando backup: {e}")
            return False
    @staticmethod
    def delete_backup(backup_path):
        if backup_path and os.path.exists(backup_path):
            try: shutil.rmtree(backup_path); BackupManager.active_backups.discard(backup_path)
            except: pass
    @staticmethod
    def cleanup_all():
        for path in list(BackupManager.active_backups): BackupManager.delete_backup(path)

# --- DATA MODELS ---
class PlanResponse(BaseModel):
    plan: str = Field(description="The detailed step-by-step plan.")
    is_safe: bool = Field(description="True if read-only, False if modifies files.")

# --- FEEDBACK MANAGER ---
class GoldenDatasetManager:
    def __init__(self, filepath="golden_dataset.json"):
        self.filepath = filepath
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
        for item in self.data[-3:]:
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
    backup_path: Optional[str]
    verification_status: Optional[str]  # "approved" | "rejected" | None
    user_feedback: Optional[str]

# --- CLIENTE ---
async def run_client():
    if len(sys.argv) < 2: sys.exit("Uso: python client.py <path_to_server_script>")
    server_path = os.path.abspath(sys.argv[1])
    server_params = StdioServerParameters(command="python", args=[server_path], env=os.environ.copy())

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            lc_tools = await load_mcp_tools(session)
            gemini_tools = [convert_langchain_tool_to_gemini(t) for t in lc_tools]
            client = create_client(provider='gemini', api_key=api_key)
            client.select_model('gemini-2.5-flash') 

            # --- PROMPT BLINDADO ---
            def get_planner_prompt(target_dir):
                return (
                    f"You are an expert DevOps Windows assistant. Your working directory is STRICTLY: {target_dir}.\n"
                    f"{feedback_manager.get_formatted_feedback()}\n"
                    "*** CRITICAL ARCHITECTURAL RULES ***:\n"
                    "1. **ATOMIC EXECUTION**: The terminal resets after every tool call. Variables ($x) are LOST..\n"
                    "2. **POWERSHELL SYNTAX**: Use `run_server_command` tool for executing commands.\n"
                    "3. **PATH STRICTNESS**: You MUST use exactly path='{target_dir}' for every tool call. Do NOT use the user query as a path.\n"
                    "4. Output a SAFE/UNSAFE assessment."
                    "5. If you need gather information you can use the run_server_command tool for reading files."
                )

# --- PROMPT BLINDADO Y CORREGIDO ---
            def get_agent_prompt(target_dir, step):
                return (
                    f"You are a DevOps ReAct agent acting on: {target_dir}.\n"
                    f"Current Step: {step}/{MAX_ITERATIONS}\n"
                    """You are an expert DevOps assistant running on Windows PowerShell.

CRITICAL RULES:
1. You have access to a terminal tool called 'run_server_command'.
2. DO NOT use 'Write-Host'. It is invisible to you. ALWAYS use 'Write-Output'.
3. **ONE-SHOT EXECUTION**: If the user asks for a specific SINGLE action (e.g., "delete the largest file"), find it, delete it, verify it is gone, and then **STOP**.
   - DO NOT loop to find the "next" largest file.
   - Once the original target is handled, the task is COMPLETE.
4. **VERIFICATION**: After deleting a file, run `Test-Path <file>` to confirm it is gone. If it returns False, you are DONE.
5. Your working directory is fixed. Do not CD.
6. **DEFINITION OF DONE**: If you have executed the plan and verified the result, output a text response (no tool calls) to finish the interaction.
"""
                )

            # --- NODOS ---
            def planner_node(state: AgentState):
                prompt = Prompt().set_system(get_planner_prompt(state.get("target_dir"))).set_output_schema(PlanResponse)
                for ex in PLANNER_EXAMPLES:
                    prompt.add_few_shot_example(ex['user'], ex['assistant'])
                # Obtener último mensaje humano real
                last_human = next((m for m in reversed(state["messages"]) if isinstance(m, HumanMessage) and not m.content.startswith("SYSTEM:")), None)
                if last_human: prompt.add_user_message(last_human.content)
                
                # Feedback loop
                if state.get("user_feedback") and state.get("verification_status") == "rejected":
                     prompt.add_user_message(f"⚠️ PREVIOUS ATTEMPT FAILED/REJECTED.\nREASON: {state.get('user_feedback')}\nTASK: Please create a NEW, CORRECTED plan avoiding previous mistakes.")

                try:
                    resp, _ = client.get_response(prompt)
                    _, plan_data, _ = prompt.validate_response(resp)
                    if not plan_data: return {"current_plan": "Error generating plan", "is_safe": False}
                    
                    AuditLogger.log("PLANNER", f"Proposed Plan: {plan_data.plan}\nSafe: {plan_data.is_safe}")
                    print(f"\n📋 PLAN ({'SAFE' if plan_data.is_safe else 'UNSAFE'}):\n{plan_data.plan}\n")
                    
                    return {
                        "messages": [AIMessage(content=f"APPROVED PLAN: {plan_data.plan}")], 
                        "current_plan": plan_data.plan, 
                        "is_safe": plan_data.is_safe, 
                        "loop_step": 0,
                        "verification_status": None, 
                        "user_feedback": None
                    }
                except Exception as e:
                    return {"current_plan": f"Error: {str(e)}", "is_safe": True}

            def agent_orchestrator_node(state: AgentState):
                prompt = Prompt().set_system(get_agent_prompt(state.get("target_dir"), state.get("loop_step"))).set_tools(gemini_tools)
                for ex in AGENT_EXAMPLES:
                    prompt.add_few_shot_example(ex['user'], ex['assistant'])
                for msg in state["messages"]:
                    if isinstance(msg, HumanMessage): prompt.add_user_message(msg.content)
                    elif isinstance(msg, AIMessage):
                        if msg.tool_calls: prompt.add_assistant_message(f"Thought: Executed tool.")
                        else: prompt.add_assistant_message(msg.content)
                    elif isinstance(msg, ToolMessage): 
                        prompt.add_tool_message(msg.name, str(msg.content)[:10000], msg.tool_call_id)
                        AuditLogger.log("TOOL_OUTPUT", f"Tool: {msg.name}\nOutput: {str(msg.content)[:500]}...")

                try:
                    resp, _ = client.get_response(prompt)
                    if not resp: return {"messages": [AIMessage(content="Task completed.")], "loop_step": state["loop_step"]+1}
                    
                    try:
                        data = json.loads(resp)
                        if "function_call" in data:
                            fc = data["function_call"]
                            
                            # --- PATH INJECTION FIX (STRICT) ---
                            # Middleware para forzar el path correcto y evitar alucinaciones.
                            if fc["name"] == "run_server_command":
                                correct_path = state["target_dir"]
                                current_path = fc["args"].get("path", "")
                                
                                # Si no coincide exactamente, lo sobrescribimos.
                                if current_path != correct_path:
                                    print_debug_step("FIX", f"Path Hallucination Detected: '{current_path}' -> Forces to: '{correct_path}'")
                                    fc["args"]["path"] = correct_path

                            AuditLogger.log("COMMAND_ATTEMPT", f"Tool: {fc['name']}\nArgs: {fc['args']}")
                            
                            return {
                                "messages": [AIMessage(content="", tool_calls=[{"name": fc["name"], "args": fc["args"], "id": str(uuid.uuid4()), "type": "tool_call"}])], 
                                "loop_step": state["loop_step"]+1
                            }
                    except: pass
                    return {"messages": [AIMessage(content=resp)], "loop_step": state["loop_step"]+1}
                except Exception as e: return {"messages": [HumanMessage(content=f"ERROR: {e}")], "loop_step": state["loop_step"]+1}

            def full_restore_node(state: AgentState):
                """Nodo dedicado a restaurar el backup y notificar al usuario/grafo."""
                print("\n🔄 REVERTING CHANGES via BackupManager...")
                success = BackupManager.restore_backup(state["backup_path"], state["target_dir"])
                msg = f"Restoration {'Successful' if success else 'Failed'}. User Feedback: {state.get('user_feedback')}"
                AuditLogger.log("ROLLBACK", msg)
                
                # Estrategia de limpieza: Borrar mensajes intermedios para no confundir al planner
                # Mantener solo el primer HumanMessage (Query original) y añadir el feedback de sistema.
                # return [RemoveMessage(id=m.id) for m in state["messages"] if ...] es complejo en LangGraph sin IDs claros.
                # En su lugar, añadiremos un mensaje de sistema fuerte.
                
                return {
                    "messages": [HumanMessage(content=f"SYSTEM ALERT: Changes were REJECTED by user.\nROLLBACK STATUS: {success}\nUSER FEEDBACK: {state.get('user_feedback')}\nACTION: Re-assess the situation and Generate a corrected plan using the feedback.")],
                    "loop_step": 0
                }

            def final_summary_node(state: AgentState):
                """Genera un resumen final post-aprobación."""
                print("\n📝 Generating Final Summary...")
                sys_prompt = "You are a reporter. Summarize the actions taken by the agent based on the conversation history. Be specific about files created/modified."
                prompt = Prompt().set_system(sys_prompt)
                
                # Filtrar mensajes para no sobrecargar
                relevant_msgs = [m for m in state["messages"] if (isinstance(m, AIMessage) and m.tool_calls) or isinstance(m, ToolMessage)]
                
                for m in relevant_msgs:
                    if isinstance(m, AIMessage) and m.tool_calls:
                        prompt.add_assistant_message(f"Tool Call: {m.tool_calls[0]['name']} Args: {m.tool_calls[0]['args']}")
                    elif isinstance(m, ToolMessage):
                        prompt.add_tool_message(m.name, str(m.content)[:1000], m.tool_call_id)
                
                try:
                    resp, _ = client.get_response(prompt)
                    AuditLogger.log("FINAL_SUMMARY", resp)
                    return {"messages": [AIMessage(content=f"\n📊 FINAL SUMMARY:\n{resp}")]}
                except:
                    return {"messages": [AIMessage(content="Task verified and completed (Summary generation failed).")]}

            # --- WORKFLOW ---
            workflow = StateGraph(AgentState)
            workflow.add_node("planner", planner_node)
            workflow.add_node("human_approval", lambda s: {}) # Placeholder
            workflow.add_node("create_backup", lambda s: {"backup_path": BackupManager.create_backup(s["target_dir"])} if not s.get("is_safe", True) else {})
            workflow.add_node("agent", agent_orchestrator_node)
            workflow.add_node("tools", ToolNode(lc_tools))
            workflow.add_node("user_verification", lambda s: {}) # Placeholder
            workflow.add_node("restore_backup", full_restore_node)
            workflow.add_node("final_summary", final_summary_node)

            workflow.add_edge(START, "planner")
            workflow.add_conditional_edges("planner", lambda s: "agent" if s["is_safe"] else "human_approval")
            workflow.add_edge("human_approval", "create_backup")
            workflow.add_edge("create_backup", "agent")
            
            def should_continue(state):
                if state.get("loop_step", 0) >= MAX_ITERATIONS: return "restore_backup"
                last_msg = state["messages"][-1]
                if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                    return "tools"
                if isinstance(last_msg, HumanMessage): 
                    # Si es un feedback de error o sistema, volver a agente
                    if "SYSTEM ALERT" in last_msg.content: return "planner" # Si viene de restore, ya fuimos a planner directo
                    return "agent"
                return "user_verification"

            workflow.add_conditional_edges("agent", should_continue, ["tools", "agent", "user_verification"])
            workflow.add_edge("tools", "agent")
            
            workflow.add_conditional_edges(
                "user_verification", 
                lambda s: "restore_backup" if s.get("verification_status") == "rejected" else "final_summary"
            )
            workflow.add_edge("restore_backup", "planner")
            workflow.add_edge("final_summary", END)

            app = workflow.compile(checkpointer=MemorySaver(), interrupt_before=["human_approval", "user_verification"])
            print("✅ Cliente Listo (Fix Critical + Path Injection).")
            
            # --- MAIN LOOP ---
            while True:
                try:
                    user_input = input("\n👤 Query (o 'quit'): ")
                    if user_input.lower() in ["quit", "exit"]: BackupManager.cleanup_all(); break
                    
                    target_dir = input("📂 Directorio: ").strip() or os.getcwd()
                    AuditLogger.log("USER_QUERY", f"Query: {user_input}\nContext: {target_dir}")

                    thread_id = str(uuid.uuid4())
                    config = {"configurable": {"thread_id": thread_id}}
                    
                    initial_state = {
                        "messages": [HumanMessage(content=user_input)], 
                        "target_dir": target_dir, 
                        "verification_status": None,
                        "is_safe": True
                    }

                    # Ejecución Inicial
                    current_state = initial_state
                    async for event in app.astream(current_state, config=config):
                        if 'agent' in event:
                            for msg in event['agent']['messages']:
                                if isinstance(msg, AIMessage) and msg.tool_calls: 
                                    print_debug_step("TOOL", msg.tool_calls[0]['name'])
                                elif isinstance(msg, AIMessage): 
                                    print_debug_step("PLAN", msg.content)
                        if 'tools' in event: 
                            print_debug_step("OUTPUT", event['tools']['messages'][0].content)
                        if 'final_summary' in event:
                            print(f"\n{event['final_summary']['messages'][-1].content}\n")

                    # Manejo de Interrupciones
                    while True:
                        snapshot = await app.aget_state(config)
                        if not snapshot.next:
                            print("✅ Proceso finalizado.")
                            break

                        next_node = snapshot.next[0]
                        
                        if next_node == "human_approval":
                            current_plan = snapshot.values.get('current_plan')
                            print(f"\n⚠️ PLAN PROPUESTO: {current_plan}")
                            decision = input("¿Aprobar ejecución? (s/n): ").lower()
                            AuditLogger.log("APPROVAL_DECISION", f"Plan: {current_plan}\nDecision: {decision}")
                            
                            if decision == 's':
                                async for e in app.astream(None, config=config): pass
                            else:
                                reason = input("Razón del rechazo: ")
                                feedback_manager.save_feedback(user_input, current_plan, reason)
                                print("❌ Cancelando y reiniciando...")
                                break 

                        elif next_node == "user_verification":
                            print(f"\n🤖 El agente indica que ha terminado.")
                            decision = input("¿Verificar cambios? (s = Aprobar / n = Rechazar y Restaurar): ").lower()
                            
                            if decision == 's':
                                AuditLogger.log("VERIFICATION", "User APPROVED changes.")
                                # FIX: Removed await from update_state
                                app.update_state(config, {"verification_status": "approved"})
                                async for e in app.astream(None, config=config): 
                                    if 'final_summary' in e:
                                        print(f"\n{e['final_summary']['messages'][-1].content}\n")
                            else:
                                reason = input("Razón del rechazo: ")
                                AuditLogger.log("VERIFICATION", f"User REJECTED changes. Reason: {reason}")
                                # FIX: Removed await from update_state
                                app.update_state(config, {"verification_status": "rejected", "user_feedback": reason})
                                print("🔄 Iniciando restauración y re-planificación...")
                                async for e in app.astream(None, config=config): pass
                
                except Exception as e:
                    print(f"\n❌ Error Crítico en Main Loop: {e}")
                    traceback.print_exc()

if __name__ == "__main__": asyncio.run(run_client())