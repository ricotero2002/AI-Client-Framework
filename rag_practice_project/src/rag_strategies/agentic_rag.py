"""
Agentic RAG - Wrapper for LangGraph Agent in Experiments
"""
from typing import Dict, Any, List, Set
from pathlib import Path
import sys
import time
import uuid
import json
import importlib.util

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.rag_strategies.base_strategy import BaseRAGStrategy
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Load Agent Module dynamically
agentic_rag_dir = Path(__file__).parent / "agentic_rag"
if str(agentic_rag_dir) not in sys.path:
    sys.path.insert(0, str(agentic_rag_dir))

agentic_rag_path = agentic_rag_dir / "agente.py"
spec = importlib.util.spec_from_file_location("agentic_rag.agente", agentic_rag_path)
agente_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agente_module)


class AgenticRAGStrategy(BaseRAGStrategy):
    """
    Agentic RAG wrapper that collects full execution traces and accumulates context.
    """
    
    def __init__(self, max_iterations: int = 15):
        super().__init__("Agentic RAG")
        self.max_iterations = max_iterations
        self.app = agente_module.app
        
    def generate_response(self, query: str, **kwargs) -> Dict[str, Any]:
        start_time = time.time()
        thread_id = f"experiment_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id}}
        
        inputs = {"messages": [HumanMessage(content=query)]}
        
        # --- DATA COLLECTION CONTAINERS ---
        execution_trace = []
        all_retrieved_documents = [] 
        seen_doc_ids = set() # To avoid duplicates in the context list
        
        iteration = 0
        try:
            # 1. Run the Graph
            for event in self.app.stream(inputs, config=config):
                iteration += 1
                if iteration >= self.max_iterations:
                    break
            
            # 2. Extract Final State
            snapshot = self.app.get_state(config)
            messages = snapshot.values.get("messages", [])
            final_response = ""

            # 3. Process History to build Trace & Context
            for i, msg in enumerate(messages):
                step_data = {
                    "step": i, 
                    "role": "unknown", 
                    "content": str(msg.content)[:1000] # Truncate long content for trace
                }

                if isinstance(msg, HumanMessage):
                    step_data["role"] = "user"

                elif isinstance(msg, AIMessage):
                    step_data["role"] = "agent"
                    # Check for tool calls
                    if msg.additional_kwargs.get("tool_calls"):
                        step_data["tool_calls"] = []
                        for tc in msg.additional_kwargs["tool_calls"]:
                            step_data["tool_calls"].append({
                                "name": tc["function"]["name"],
                                "args": tc["function"]["arguments"]
                            })
                    else:
                        # If AI message has no tool calls, it's likely the answer
                        if msg.content.strip():
                            final_response = msg.content

                elif isinstance(msg, ToolMessage):
                    step_data["role"] = "tool"
                    step_data["tool_name"] = msg.name
                    
                    # Try to parse tool output to get documents
                    try:
                        output_json = json.loads(msg.content)
                        step_data["output_json"] = output_json # Save full output in trace if needed
                        
                        # -- CAPTURE DOCUMENTS --
                        # Works for both 'retrieve_documents' and 'rerank_documents' 
                        # as long as they return a "documents" list
                        if "documents" in output_json and isinstance(output_json["documents"], list):
                            docs = output_json["documents"]
                            # Also try to get metadata if available
                            metas = output_json.get("metadatas", [{} for _ in docs])
                            
                            for doc_text, doc_meta in zip(docs, metas):
                                # Create a unique ID for the doc to prevent duplicates
                                # Use ID if available, else hash the text
                                doc_id = doc_meta.get("id", hash(doc_text))
                                
                                if doc_id not in seen_doc_ids:
                                    all_retrieved_documents.append(doc_text)
                                    seen_doc_ids.add(doc_id)
                                    
                    except:
                        pass

                execution_trace.append(step_data)

            # 4. Metrics & Return
            total_latency = (time.time() - start_time) * 1000
            input_tokens = len(query) // 4
            output_tokens = len(final_response) // 4
            
            # Fallback if empty response
            if not final_response:
                final_response = "Error: Agent did not produce a final text response."

            return {
                "strategy": self.name,
                "query": query,
                "response": final_response,
                "context": all_retrieved_documents, # Contains ALL docs from ALL steps
                "latency_ms": total_latency,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "model": agente_module.MODEL,
                "extra_info": {
                    "thread_id": thread_id,
                    "iterations": iteration,
                    "doc_count": len(all_retrieved_documents),
                    "execution_trace": execution_trace
                }
            }

        except Exception as e:
            return {
                "strategy": self.name,
                "query": query,
                "response": f"Critical Error in Agent: {str(e)}",
                "error": str(e),
                "context": [],
                "latency_ms": (time.time() - start_time) * 1000
            }