import os
import operator
import time
from typing import TypedDict, List, Dict, Annotated
from dotenv import load_dotenv

# Import framework classes
from client_factory import ClientFactory
from prompt import Prompt
from langgraph.types import Send  # <--- CRÍTICO PARA MAP OPERATIONS
from langgraph.graph import StateGraph, END
from langsmith import traceable
from pydantic import BaseModel, Field
import json


# Load environment variables
load_dotenv()

# --- Configuration ---
# You can change this to 'gemini' if you have a Gemini key
#PROVIDER = 'openAI' 
PROVIDER = 'gemini'
#MODEL = 'gpt-5-nano' # or 'gpt-4o', 'gemini-1.5-flash'
#MODEL = 'gemini-2.0-flash-exp'
MODEL = 'gemini-2.0-flash-lite'

# --- State Definition ---
class ContentState(TypedDict):
    topic: str
    selected_idea: str
    outline: List[str]
    sections_content: Annotated[List[str], operator.add] 
    final_content: str
    review_count: int # Para evitar loops infinitos

class SectionState(TypedDict):
    section_title: str
    idea_context: str
# --- Nodes ---

@traceable
def ideation_node(state: ContentState) -> Dict:
    """Generates ideas and selects the best angle."""
    print(f"\n--- 1. IDEATION ({state['topic']}) ---")
    
    client = ClientFactory.create_client(PROVIDER, langsmith=False)
    client.select_model(MODEL)
    
    prompt = (
        Prompt()
        .set_system("Eres un experto estratega de contenido. Tu objetivo es encontrar el ángulo más interesante para un tema.")
        .set_user_input(f"Dame una idea única y cautivadora para un artículo sobre: {state['topic']}. Responde SOLO con la idea central en una frase.")
    )
    
    response, _ = client.get_response(prompt)
    print(f"Idea seleccionada: {response}")
    return {"selected_idea": response, "review_count": 0}

@traceable
def outline_node(state: ContentState) -> Dict:
    """Generates a structured outline based on the idea."""
    print(f"\n--- 2. OUTLINE ---")
    
    client = ClientFactory.create_client(PROVIDER, langsmith=True)
    client.select_model(MODEL)
    
    # Use Structured Output feature of our framework
    class Secciones(BaseModel):
        sections: List[str] = Field(min_length=3, max_length=5,description="Lista de títulos de las secciones principales")
    

    prompt = (
        Prompt()
        .set_system("Eres un arquitecto de la información. Crea un esquema detallado.")
        .set_user_input(f"Crea un esquema de 3 a 5 secciones para un artículo basado en esta idea: {state['selected_idea']}")
        .set_output_schema(Secciones)
    )
    
    # The client automatically detects structured output and handles it
    response, _ = client.get_response(prompt)
    
    data = json.loads(response)
    sections = data.get("sections", [])
    
    print(f"Secciones (type={type(sections)}): {sections}")
    return {"outline": sections}

@traceable
def writing_node(state: SectionState) -> Dict:
    """Writes the full content based on sections."""
    print(f"\n--- 3. WRITING ---")
    
    client = ClientFactory.create_client(PROVIDER, langsmith=True)
    client.select_model(MODEL)
    
    title = state["section_title"]
    print(f"   [Worker] Escribiendo sección: '{title}'...")

    prompt = (
            Prompt()
            .set_system("Eres un redactor experto. Escribe una sección concisa pero profunda.")
            .set_user_input(f"Tema: {state['idea_context']}\nSección actual: {title}\n\nEscribe el contenido para esta sección.")
        )
    content, _ = client.get_response(prompt)
    
    return {"sections_content": [content]} 


# --- NUEVO: Nodo Agregador (Junta todo) ---
@traceable
def assembler_node(state: ContentState):
    print("--- ENSAMBLANDO BORRADOR ---")
    # Une todas las piezas generadas en paralelo
    full_draft = "\n".join(state['sections_content'])
    return {"final_content": full_draft}

@traceable
def editor_node(state: ContentState):
    print("--- 4. EDITOR REVIEW ---")
    # Lógica condicional simulada
    # Si es el primer intento, rechazamos para mostrar el loop.
    if state["review_count"] < 1:
        print(">> EDITOR: El tono es muy informal. ¡Reescribir!")

        client = ClientFactory.create_client(PROVIDER, langsmith=True)
        client.select_model(MODEL)
        prompt = (
        Prompt()
        .set_system("Eres un editor jefe estricto. Revisa el texto, mejora la fluidez y el tono.")
        .set_user_input(f"Texto original:\n{state['final_content']}\n\nMejora este texto. Mantén la estructura pero eleva la calidad.")
    )
        final_version, _ = client.get_response(prompt)

        return {"final_content": final_version, "review_count": state["review_count"] + 1}

    
    
    
    print(">> EDITOR: Aprobado.")
    return {"review_count": state["review_count"] + 1}

def map_sections(state: ContentState):
    """Genera las tareas paralelas (Map)"""
    return [
        Send("write_section", {
            "section_title": s, 
            "idea_context": state["selected_idea"]
        }) 
        for s in state["outline"]
    ]

def should_continue(state: ContentState):
    """Decide si volvemos a escribir o terminamos"""
    if state["review_count"] <= 1:
        return "rewrite" # Nombre del edge condicional
    return "end"


def create_content_graph():
    workflow = StateGraph(ContentState)
    
    # Add nodes
    workflow.add_node("ideacion", ideation_node)
    workflow.add_node("outline", outline_node)
    workflow.add_node("write_section", writing_node) # Nodo Worker
    workflow.add_node("assembler", assembler_node)
    workflow.add_node("editor", editor_node)
    
    # Add edges
    workflow.set_entry_point("ideacion")
    workflow.add_edge("ideacion", "outline")
    workflow.add_conditional_edges("outline", map_sections, ["write_section"])
    workflow.add_edge("write_section", "assembler")
    workflow.add_edge("assembler", "editor")
    workflow.add_conditional_edges(
        "editor",
        should_continue,
        {
            "rewrite": "editor", # Si rechaza, volvemos al principio (o a redacción)
            "end": END
        }
    )
    
    return workflow.compile()

# --- Main Execution ---

if __name__ == "__main__":
    app_graph = create_content_graph()
    
    print("Iniciando flujo de trabajo de Generación de Contenido con LangGraph...")
    topic_input = input("Introduce un tema (ej. 'El futuro de la IA'): ") or "El futuro de la IA"
    
    initial_state = {"topic": topic_input}
    
    result = app_graph.invoke(initial_state)
    
    print("\n\n=== CONTENIDO FINAL ===\n")
    print(result["final_content"])
    
    # Save to file
    with open("resultado_articulo.md", "w", encoding="utf-8") as f:
        f.write(result["final_content"])
    print(f"\nGuardado en 'resultado_articulo.md'")
