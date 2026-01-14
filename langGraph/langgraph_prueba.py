import os
import operator
import time
from typing import TypedDict, List, Dict, Annotated
from dotenv import load_dotenv

# Import framework classes
from client_factory import ClientFactory
from prompt import Prompt

# Import LangGraph
try:
    from langgraph.graph import StateGraph, END
except ImportError:
    print("Error: LangGraph not installed. Please install with: pip install -r requirements_langgraph.txt")
    exit(1)

# Load environment variables
load_dotenv()

# --- Configuration ---
# You can change this to 'gemini' if you have a Gemini key
PROVIDER = 'gemini' 
#MODEL = 'gemini-2.5-flash-lite' # or 'gpt-4o', 'gemini-1.5-flash'
MODEL = 'gemini-2.0-flash-exp'

# --- State Definition ---
class ContentState(TypedDict):
    topic: str
    selected_idea: str
    outline: List[str]
    draft: str
    critique: str
    final_content: str

# --- Nodes ---

def ideation_node(state: ContentState) -> Dict:
    """Generates ideas and selects the best angle."""
    print(f"\n--- 1. IDEATION ({state['topic']}) ---")
    
    client = ClientFactory.create_client(PROVIDER)
    client.select_model(MODEL)
    
    prompt = (
        Prompt()
        .set_system("Eres un experto estratega de contenido. Tu objetivo es encontrar el ángulo más interesante para un tema.")
        .set_user_input(f"Dame una idea única y cautivadora para un artículo sobre: {state['topic']}. Responde SOLO con la idea central en una frase.")
    )
    
    response, _ = client.get_response(prompt)
    print(f"Idea seleccionada: {response}")
    return {"selected_idea": response}

def outline_node(state: ContentState) -> Dict:
    """Generates a structured outline based on the idea."""
    print(f"\n--- 2. OUTLINE ---")
    
    client = ClientFactory.create_client(PROVIDER)
    client.select_model(MODEL)
    
    # Use Structured Output feature of our framework
    prompt = (
        Prompt()
        .set_system("Eres un arquitecto de la información. Crea un esquema detallado.")
        .set_user_input(f"Crea un esquema de 3 a 5 secciones para un artículo basado en esta idea: {state['selected_idea']}")
        .add_output_field("sections", list[str], "Lista de títulos de las secciones principales")
    )
    
    # The framework handles the json parsing automatically via structured output if we configure the client correctly.
    # We need to pass the schema to OpenAI's response_format parameter.
    schema = prompt.get_output_schema()
    
    response, _ = client.get_response(
            prompt,
            response_mime_type="application/json",
            response_schema=schema
        )
    # Parse the JSON response
    import json
    try:
        # If response is already a dict (some client implementations might do this)
        if isinstance(response, dict):
            data = response
        else:
            data = json.loads(response)
            
        sections = data.get("sections", [])
        
        # DEBUG: Verify type
        print(f"DEBUG: Type of sections: {type(sections)}")
        if isinstance(sections, str):
            print("DEBUG: sections is a string, attempting to parse...")
            try:
                sections = json.loads(sections)
            except:
                pass
                
    except json.JSONDecodeError:
        print(f"Error parsing JSON: {response}")
        # Fallback
        sections = [line.strip("- ") for line in response.split("\n") if line.strip()]

    print(f"Secciones: {sections}")
    return {"outline": sections}

def writing_node(state: ContentState) -> Dict:
    """Writes the full content based on sections."""
    print(f"\n--- 3. WRITING ---")
    
    client = ClientFactory.create_client(PROVIDER)
    client.select_model(MODEL)
    
    full_draft = ""
    
    # We simulate "writing by sections" by iterating here.
    # In a more advanced graph, this could be a 'map' operation.
    for section in state['outline']:
        print(f"Escribiendo sección: {section}...")
        prompt = (
            Prompt()
            .set_system("Eres un redactor experto. Escribe una sección concisa pero profunda.")
            .set_user_input(f"Tema: {state['selected_idea']}\nSección actual: {section}\n\nEscribe el contenido para esta sección.")
        )
        content, _ = client.get_response(prompt)
        full_draft += f"## {section}\n\n{content}\n\n"
        
        # Add sleep to respect Gemini rate limits (10 RPM for some models)
        print("Esperando 10 segundos para respetar el límite de tasa de la API...")
        time.sleep(10)
        
    return {"draft": full_draft}

def review_node(state: ContentState) -> Dict:
    """Reviews and polishes the draft."""
    print(f"\n--- 4. REVIEW ---")
    
    client = ClientFactory.create_client(PROVIDER)
    client.select_model(MODEL)
    
    prompt = (
        Prompt()
        .set_system("Eres un editor jefe estricto. Revisa el texto, mejora la fluidez y el tono.")
        .set_user_input(f"Texto original:\n{state['draft']}\n\nMejora este texto. Mantén la estructura pero eleva la calidad.")
    )
    
    final_version, _ = client.get_response(prompt)
    return {"final_content": final_version}

# --- Graph Construction ---

def create_content_graph():
    workflow = StateGraph(ContentState)
    
    # Add nodes
    workflow.add_node("ideacion", ideation_node)
    workflow.add_node("outline", outline_node)
    workflow.add_node("redaccion", writing_node)
    workflow.add_node("revision", review_node)
    
    # Add edges
    workflow.set_entry_point("ideacion")
    workflow.add_edge("ideacion", "outline")
    workflow.add_edge("outline", "redaccion")
    workflow.add_edge("redaccion", "revision")
    workflow.add_edge("revision", END)
    
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

## ver lo de operaciones de mapa y falta tener vertices condicionales