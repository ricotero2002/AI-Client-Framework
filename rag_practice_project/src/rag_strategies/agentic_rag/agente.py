import os
import sys
from pathlib import Path
import json
import uuid
from typing import TypedDict, Annotated, List, Dict, Any, Optional

# Add project root to sys.path
root_path = str(Path(__file__).parent.parent.parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# Local imports
from tools import optimize_query, retrieve_documents, rerank_documents
from prompt import Prompt
from client_factory import ClientFactory

# --- Configuration ---
PROVIDER = 'gemini' 
MODEL = 'gemini-2.5-flash'
client = ClientFactory.create_client(PROVIDER, langsmith=True)
client.select_model(MODEL)

TOOL_MAP = {
    "optimize_query": optimize_query,
    "retrieve_documents": retrieve_documents,
    "rerank_documents": rerank_documents
}

SYSTEM_INSTRUCTIONS = """
You are an expert vegetarian recipe assistant using an Agentic RAG pipeline.

### YOUR GOAL
Find the best recipes for the user by executing this pipeline:
1. **Optimize**: Understand the user's intent and ingredients.
2. **Retrieve**: Search the database.
3. **Analyze & Loop**: If results are poor (0 docs), RELAX the query and try again.
4. **Rerank**: Select the best matches.
5. **Answer**: Explain the recipe to the user.

### CRITICAL RULES
1. **Tool Usage**:
   - Call tools by name. Output JSON: {"tool": "name", "arguments": {...}}
   - **Data Flow**: You do NOT need to copy-paste large data. The system automatically injects the output of the previous tool into the next one.
   - For `retrieve_documents`, just pass empty args: {} (System uses optimization data).
   - For `rerank_documents`, just pass empty args: {} (System uses retrieval data).

2. **The "Zero Results" Loop - RELAXATION STRATEGIES**:
   - If `retrieve_documents` returns 0 documents:
     - DO NOT call `rerank_documents`.
     - **MUST** call `optimize_query` again with ONE of these relaxation strategies:
       
       **Strategy A - Relax Ingredient Logic (RECOMMENDED FIRST)**:
       - If previous query used ingredient_filter_operator="$and" (requires ALL ingredients)
       - Change to ingredient_filter_operator="$or" (requires AT LEAST ONE ingredient)
       - Keep the same ingredient list
       - Example: "chickpeas AND eggplant" → "chickpeas OR eggplant"
       
       **Strategy B - Remove Nutritional Filters**:
       - If query had nutritional constraints (calories, protein, etc.)
       - Remove those filters and search only by ingredients
       
       **Strategy C - Reduce Ingredients**:
       - If Strategy A failed, try with just the most important ingredient
       - Remove secondary ingredients
   
   - Only give up after 2 failed attempts with different strategies.
   - After an optimization always try to retrieve documents.
   - ALWAYS include the `"query"` argument in `optimize_query`, even if just changing filters.

3. **Final Answer**:
   - Once `rerank_documents` is done, use the provided text to answer the user.
   - Do NOT invent recipes. Use the context.
   - If you found multiple recipes in previous steps, mention them.
"""

class AgenticRAGState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# --- HELPER: Find VALID data in history ---
def get_last_valid_tool_output(messages: List[BaseMessage], tool_name: str) -> Optional[Dict]:
    """Scans history backwards to find the last SUCCESSFUL output of a specific tool."""
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == tool_name:
            try:
                data = json.loads(msg.content)
                # Ensure it's not an error message wrapped in JSON or a raw string
                if isinstance(data, dict) and "error" not in data and "raw_content" not in data:
                    return data
            except:
                continue
    return None

def convert_messages_to_conversation_history(messages: List[BaseMessage]) -> List[Dict[str, str]]:
    history = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            history.append({"role": "user", "content": str(msg.content)})
        elif isinstance(msg, AIMessage) and msg.content:
            history.append({"role": "assistant", "content": str(msg.content)})
        elif isinstance(msg, ToolMessage):
            # We summarize tool outputs to save context window, unless it's the very last one
            content = str(msg.content)
            if len(content) > 500 and msg != messages[-1]:
                content = content[:500] + "... (truncated)"
            history.append({"role": "user", "content": f"[System/Tool {msg.name} Output]: {content}"})
    return history

def parse_tool_call(response_text: str) -> Optional[Dict[str, Any]]:
    try:
        clean_text = response_text.strip()
        if clean_text.startswith("```json"): clean_text = clean_text[7:]
        if clean_text.startswith("```"): clean_text = clean_text[3:]
        if clean_text.endswith("```"): clean_text = clean_text[:-3]
        data = json.loads(clean_text.strip())
        if isinstance(data, dict) and "tool" in data:
            return data
    except:
        pass
    return None

# --- CORE NODE LOGIC ---
def agent_node(state: AgenticRAGState):
    messages = state["messages"]
    prompt = Prompt(use_delimiters=False)
    prompt.set_system(SYSTEM_INSTRUCTIONS)
    prompt.set_conversation_context(convert_messages_to_conversation_history(messages))
    
    # Context Injection & Steering
    last_msg = messages[-1]
    user_input = last_msg.content if messages else ""
    
    # 1. ANALYZE PREVIOUS STEP TO GUIDE AGENT
    if isinstance(last_msg, ToolMessage):
        if last_msg.name == "optimize_query":
            # Check if optimization failed
            if "error" in str(last_msg.content).lower():
                prompt.set_user_input(f"{user_input}\n\n[SYSTEM]: ⚠️ Optimization failed. Try calling 'optimize_query' again with simpler keywords.")
            else:
                prompt.set_user_input(f"{user_input}\n\n[SYSTEM]: Optimization success. Now call 'retrieve_documents'.")
            
        elif last_msg.name == "retrieve_documents":
            try:
                data = json.loads(last_msg.content)
                count = len(data.get("documents", []))
            except: 
                count = 0
            
            if count == 0:
                # CRITICAL: Tell agent exactly what query text to use
                # Get the previous optimization to see what was attempted
                prev_opt = get_last_valid_tool_output(messages, "optimize_query")
                
                if prev_opt:
                    ingredients = prev_opt.get("ingredient_filters", [])
                    prev_operator = prev_opt.get("ingredient_filter_operator", "$and")
                    
                    if ingredients and len(ingredients) > 1 and prev_operator == "$and":
                        # Strategy: Switch to OR
                        ingredients_str = " OR ".join(ingredients)
                        prompt.set_user_input(
                            f"{user_input}\n\n[SYSTEM]: ⚠️ Found 0 documents with ALL ingredients required. "
                            f"RELAXATION STRATEGY: Call optimize_query with this NEW query text:\n"
                            f"'recipes with {ingredients_str}' (this means ANY of these ingredients, not all)\n"
                            f"This will find recipes that have AT LEAST ONE of the ingredients."
                        )
                    elif ingredients and len(ingredients) > 1 and prev_operator == "$or":
                        # Strategy: Try with just first ingredient
                        main_ingredient = ingredients[0]
                        prompt.set_user_input(
                            f"{user_input}\n\n[SYSTEM]: ⚠️ Still 0 documents even with OR. "
                            f"RELAXATION STRATEGY: Call optimize_query with just the main ingredient:\n"
                            f"'recipes with {main_ingredient}'"
                        )
                    else:
                        # Generic fallback
                        prompt.set_user_input(
                            f"{user_input}\n\n[SYSTEM]: ⚠️ Found 0 documents. "
                            "Try optimize_query with a simpler, broader search term."
                        )
                else:
                    prompt.set_user_input(
                        f"{user_input}\n\n[SYSTEM]: ⚠️ Found 0 documents. DO NOT give up. "
                        "Call 'optimize_query' again with a simpler query."
                    )
            else:
                prompt.set_user_input(f"{user_input}\n\n[SYSTEM]: Found {count} documents. Now call 'rerank_documents'.")
                
        elif last_msg.name == "rerank_documents":
            prompt.set_user_input(f"{user_input}\n\n[SYSTEM]: Reranking done. Analyze the documents above and answer the user's question.")
    else:
        prompt.set_user_input(user_input)

    # 2. GENERATE RESPONSE
    response_text, _ = client.get_response(prompt)
    tool_data = parse_tool_call(response_text)
    
    if tool_data:
        tool_name = tool_data.get("tool")
        tool_args = tool_data.get("arguments", {})
        print(f"--- 🤖 Agent calling: {tool_name} ---")

        # 3. AUTO-FETCH / DATA FLOW LOGIC
        if tool_name == "retrieve_documents":
            print("   ↳ 🔄 Auto-fetching optimization data...")
            # Search for LAST VALID optimization
            opt_data = get_last_valid_tool_output(messages, "optimize_query")
            
            if not opt_data:
                return {"messages": [AIMessage(content="SYSTEM ERROR: No valid 'optimize_query' output found in history. Please call optimize_query first.")]}
            
            tool_args = opt_data # Inject
            
        elif tool_name == "rerank_documents":
            print("   ↳ 🔄 Auto-fetching retrieval data...")
            # Need Query (from Optimize) and Docs (from Retrieve)
            opt_data = get_last_valid_tool_output(messages, "optimize_query")
            ret_data = get_last_valid_tool_output(messages, "retrieve_documents")
            
            if not opt_data or not ret_data:
                return {"messages": [AIMessage(content="SYSTEM ERROR: Missing optimization or retrieval data. Cannot rerank.")]}
                
            tool_args = {
                "query": opt_data.get("query"),
                "retrieval_results_json": json.dumps(ret_data) # Reranker expects stringified JSON
            }

        # 4. EXECUTE TOOL CALL
        return {
            "messages": [
                AIMessage(
                    content="",
                    additional_kwargs={
                        "tool_calls": [{
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "function": {"name": tool_name, "arguments": json.dumps(tool_args)},
                            "type": "function"
                        }]
                    }
                )
            ]
        }
    
    # Plain text response
    return {"messages": [AIMessage(content=response_text)]}

# Graph Setup
tools_node = ToolNode(list(TOOL_MAP.values()))

def should_continue(state: AgenticRAGState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "additional_kwargs") and last_message.additional_kwargs.get("tool_calls"):
        return "tools"
    return END

workflow = StateGraph(AgenticRAGState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

checkpointer = SqliteSaver(sqlite3.connect("agentic_rag_memory.sqlite", check_same_thread=False))
app = workflow.compile(checkpointer=checkpointer)