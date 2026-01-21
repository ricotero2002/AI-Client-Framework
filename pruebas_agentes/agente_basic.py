import os
import random
import re
from typing import Optional, Type, TypedDict, Literal
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Importaciones de LangChain y Pydantic
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.utilities import OpenWeatherMapAPIWrapper  
from langgraph.graph import StateGraph, END

from langsmith import traceable

from transformers import pipeline
# Get an [API key](https://home.openweathermap.org/api_keys) first.
# Set API key either by passing it in to constructor directly
# or by setting the environment variable "OPENWEATHERMAP_API_KEY".

# --- Configuration ---
# You can change this to 'gemini' if you have a Gemini key
PROVIDER = 'gemini' 
#MODEL = 'gemini-2.5-flash-lite' # or 'gpt-4o', 'gemini-1.5-flash'
MODEL = 'gemini-2.0-flash-exp'
#client = ClientFactory.create_client(PROVIDER, langsmith=True)

# Configuración opcional para Wikipedia (para que no traiga documentos enormes)
os.environ["WIKIPEDIA_TOP_K_RESULTS"] = "1"
os.environ["WIKIPEDIA_MAX_DOC_CONTENT_LENGTH"] = "2000"
os.environ["WIKIPEDIA_LANG"] = "es"  # Configurar Wikipedia en español

class WeatherInput(BaseModel):
    """Esquema de entrada para consultar el clima."""
    location: str = Field(
       ..., 
        description="El nombre de la ciudad o región, ej: 'Buenos Aires', 'Madrid'."
    )
    country_code: Optional[str] = Field(
        None, 
        description="El código de país ISO 3166-1 alpha-2 opcional, ej: 'AR', 'ES'."
    )

class MathInput(BaseModel):
    """Esquema de entrada para operaciones matemáticas."""
    a: int = Field(..., description="El primer número entero.")
    b: int = Field(..., description="El segundo número entero.")

class WikiInput(BaseModel):
    """Esquema de entrada para búsquedas en Wikipedia."""
    query: str = Field(
       ..., 
        description="El término o concepto a buscar en Wikipedia."
    )

@tool("get_weather", args_schema=WeatherInput)
@traceable(name="tool_weather") # Trazabilidad en LangSmith
def get_weather(location: str, country_code: Optional[str] = None) -> str:
    """
    Obtiene el estado actual del clima para una ubicación específica.
    Usa esta herramienta cuando el usuario pregunte por el tiempo, temperatura o clima.
    """
    # Simulación de respuesta de API para la prueba
    # En producción, aquí iría una llamada a OpenWeatherMap o similar.
    print(f"DEBUG: Consultando clima para {location}")
    
    weather = OpenWeatherMapAPIWrapper()
    weather_data = weather.run(location) 
    
    return weather_data

@tool("add_integers", args_schema=MathInput)
@traceable(name="tool_calculator")
def add_integers(a: int, b: int) -> int:
    """
    Calcula la suma de dos números enteros.
    Usa esta herramienta SOLAMENTE para sumar enteros. No sirve para otras operaciones.
    """
    return a + b


@tool("search_wikipedia", args_schema=WikiInput)
@traceable(name="tool_wikipedia")
def search_wikipedia(query: str) -> str:
    """
    Busca información general, histórica o factual en Wikipedia.
    Usa esta herramienta cuando necesites contexto sobre qué es algo, quién es alguien o datos históricos.
    """
    try:
        wiki = WikipediaAPIWrapper()
        # Ejecutamos la búsqueda
        result = wiki.run(query)
        if not result:
            return "No se encontró información relevante en Wikipedia."
        return result
    except Exception as e:
        return f"Error al conectar con Wikipedia: {str(e)}"

# Lista de herramientas listas para inyectar en el agente
tools_list = [get_weather, add_integers, search_wikipedia]



# Definimos el estado del grafo
class AgentState(TypedDict):
    user_input: str      # La pregunta del usuario
    intent: str          # La intención detectada (weather, math, wiki, other)
    output: str          # La respuesta final

# ------------------------------------------------------------------
# Configuración del Modelo de Hugging Face (Zero-Shot Classification)
# ------------------------------------------------------------------
# Cargamos el pipeline una sola vez fuera de la función para eficiencia.
# NOTA: La primera vez descargará el modelo (~1.6GB).
classifier = pipeline(
    "zero-shot-classification", 
    model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", 
    device=-1
)

ner = pipeline(
    task="token-classification",
    model="tanaos/tanaos-NER-v1",
    aggregation_strategy="first"
)

# Definición de entidades nombradas que queremos extraer
NAMED_ENTITIES = {
    "PERSON": "Individual people, fictional characters",
    "ORG": "Companies, institutions, agencies",
    "LOCATION": "Geographical areas",
    "DATE": "Absolute or relative dates, including years, months and/or days",
    "TIME": "Specific time of the day",
    "PERCENT": "Percentage expressions",
    "NUMBER": "Numeric measurements or expressions",
    "FACILITY": "Buildings, airports, highways, etc.",
    "PRODUCT": "Objects, vehicles, food, etc. bearing a specific name",
    "WORK_OF_ART": "Titles of creative works",
    "LANGUAGE": "Natural or programming languages",
    "NORP": "National, religious or political groups",
    "ADDRESS": "full addresses",
    "PHONE_NUMBER": "telephone numbers",
}

def extract_named_entities(text: str) -> dict:
    """
    Extrae entidades nombradas del texto usando el pipeline NER.
    
    Args:
        text: El texto del cual extraer entidades
        
    Returns:
        Un diccionario con las entidades agrupadas por tipo
        Ejemplo: {'PERSON': ['John'], 'LOCATION': ['Barcelona'], 'TIME': ['15:45']}
    """
    # Ejecutar NER
    ner_results = ner(text)
    
    # Agrupar entidades por tipo
    entities_by_type = {}
    
    for entity in ner_results:
        entity_type = entity['entity_group']
        # Limpiar la palabra: eliminar espacios y puntuación al final
        entity_word = entity['word'].strip()
        # Remover puntuación común al final (?, !, ., ,)
        entity_word = re.sub(r'[?!.,;:]$', '', entity_word)
        entity_score = entity['score']
        
        # Solo incluir entidades con confianza razonable (> 0.5)
        if entity_score > 0.5:
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append({
                'word': entity_word,
                'score': entity_score,
                'start': entity['start'],
                'end': entity['end']
            })
    
    print(f"\n--- Entidades extraídas: {entities_by_type} ---")
    return entities_by_type


# Simplificamos un poco las etiquetas para que sean semánticamente más distintas
# Mantenemos las 'keys' igual para tu lógica interna, cambiamos los 'values' a inglés.
CANDIDATE_LABELS = {
    "weather": "get current weather or temperature",
    "math": "calculate a math sum or add numbers",
    "wiki": "search for factual information, history, or people", # 'people' ayuda mucho con 'Einstein'
    "other": "general conversation or greeting"
}
#classifier = pipeline("zero-shot-classification", model="Recognai/zeroshot_selectra_medium")

# Definimos las etiquetas candidatas que el modelo usará para comparar.
# Las claves son las etiquetas legibles para nosotros, los valores son descripciones semánticas para el modelo.
# Solo pasamos la lista de descripciones al modelo
labels_list = list(CANDIDATE_LABELS.values())

@traceable(name="node_classifier")
def classify_input_node(state: AgentState) -> AgentState:
    """
    Nodo de LangGraph que utiliza BART-Large-MNLI para clasificar la intención.
    """
    user_text = state["user_input"]
    
    print(f"--- Clasificando intención para: '{user_text}' ---")

    # Ejecutamos la clasificación zero-shot
    result = classifier(user_text, labels_list, multi_label=False)
    
    # El modelo devuelve las etiquetas y los scores ordenados de mayor a menor confianza
    top_label_desc = result["labels"][0]
    score = result["scores"][0]
    
    # Mapeamos la descripción ganadora de vuelta a nuestra clave interna (weather, math, etc.)
    # Buscamos qué clave (key) corresponde al valor (value) que ganó
    detected_intent = next(k for k, v in CANDIDATE_LABELS.items() if v == top_label_desc)

    print(f"--- Intención detectada: {detected_intent} (Confianza: {score:.4f}) ---")
    
    # Actualizamos el estado con la intención detectada
    return {"intent": detected_intent}


# 1. Definimos los nodos ejecutores (Wrappers para que encajen en el grafo)
# Cada nodo recibe el estado, ejecuta la tool y actualiza el 'output'
@traceable(name="node_weather")
def weather_node(state: AgentState):
    """
    Nodo que maneja consultas de clima.
    Extrae la ubicación del input del usuario usando NER.
    """
    # Extraer entidades del input del usuario
    entities = extract_named_entities(state["user_input"])
    
    # Buscar LOCATION en las entidades extraídas
    location = None
    country_code = None
    
    if "LOCATION" in entities and len(entities["LOCATION"]) > 0:
        # Tomar la primera ubicación encontrada
        location = entities["LOCATION"][0]["word"]
        print(f"--- Ubicación detectada: {location} ---")
    
    # Si no se encontró ubicación, usar un valor por defecto o error
    if not location:
        return {"output": "No pude detectar una ubicación en tu consulta. Por favor, especifica una ciudad."}
    
    # Invocar la herramienta de clima
    try:
        res = get_weather.invoke({"location": location}) 
        return {"output": res}
    except Exception as e:
        return {"output": f"Error al consultar el clima: {str(e)}"}

@traceable(name="node_math")
def math_node(state: AgentState):
    """
    Nodo que maneja operaciones matemáticas.
    Extrae números del input del usuario usando NER.
    """
    # Extraer entidades del input del usuario
    entities = extract_named_entities(state["user_input"])
    
    # Buscar números en las entidades extraídas
    numbers = []
    
    if "NUMBER" in entities:
        for num_entity in entities["NUMBER"]:
            try:
                # Extraer solo dígitos del texto
                digits_only = re.sub(r'\D', '', num_entity["word"])
                if digits_only:
                    num = int(digits_only)
                    numbers.append(num)
                    print(f"Número extraído: {num} de '{num_entity['word']}'")
            except ValueError:
                print(f"No se pudo convertir '{num_entity['word']}' a número")
    
    # Si no encontramos exactamente 2 números, usar valores por defecto o error
    if len(numbers) < 2:
        return {"output": "No pude detectar dos números en tu consulta. Por favor, especifica dos números para sumar."}
    
    # Tomar los primeros dos números
    a, b = numbers[0], numbers[1]
    print(f"--- Números detectados: {a} y {b} ---")
    
    res = add_integers.invoke({"a": a, "b": b})
    return {"output": f"La suma de {a} + {b} = {res}"}

@traceable(name="node_wikipedia")
def wiki_node(state: AgentState):
    """
    Busca en Wikipedia, pero intenta extraer la entidad principal primero
    para que la búsqueda sea efectiva.
    """
    original_query = state["user_input"]
    search_term = original_query # Por defecto, buscamos todo

    # 1. Intentamos extraer entidades clave para buscar solo eso
    entities = extract_named_entities(original_query)
    
    # Priorizamos Personas, Organizaciones, Lugares o Productos
    relevant_entities = []
    for tag in ["PERSON", "ORG", "LOCATION", "PRODUCT", "WORK_OF_ART", "MISC"]:
        if tag in entities:
            relevant_entities.extend(entities[tag])
    
    # Si encontramos entidades, usamos la que tenga mayor score
    if relevant_entities:
        # Ordenamos por score descendente y tomamos la palabra de la mejor
        best_entity = sorted(relevant_entities, key=lambda x: x['score'], reverse=True)[0]
        search_term = best_entity['word']
        print(f"--- Wikipedia: Buscando '{search_term}' en lugar de la frase completa ---")
    
    # 2. Invocamos la herramienta con el término limpio
    res = search_wikipedia.invoke({"query": search_term})
    
    return {"output": res}

@traceable(name="node_other")
def other_node(state: AgentState):
    return {"output": "Lo siento, solo puedo ayudar con clima, matemáticas o wikipedia."}

# 2. Definimos la función de Router (Decide a dónde ir después de clasificar)
def router(state: AgentState):
    intent = state["intent"]
    # Retorna el nombre del siguiente nodo basado en el intent
    if intent == "weather":
        return "node_weather"
    elif intent == "math":
        return "node_math"
    elif intent == "wiki":
        return "node_wikipedia"
    else:
        return "node_other"

# 3. Armamos el Grafo
workflow = StateGraph(AgentState)

# Agregamos los nodos
workflow.add_node("node_classifier", classify_input_node)
workflow.add_node("node_weather", weather_node)
workflow.add_node("node_math", math_node)
workflow.add_node("node_wikipedia", wiki_node)
workflow.add_node("node_other", other_node)

# Definimos el punto de entrada
workflow.set_entry_point("node_classifier")

# Agregamos las aristas condicionales
workflow.add_conditional_edges(
    "node_classifier",
    router,
    {
        "node_weather": "node_weather",
        "node_math": "node_math",
        "node_wikipedia": "node_wikipedia",
        "node_other": "node_other"
    }
)

# Todas las ramas terminan en END
workflow.add_edge("node_weather", END)
workflow.add_edge("node_math", END)
workflow.add_edge("node_wikipedia", END)
workflow.add_edge("node_other", END)

# Compilamos la aplicación
app = workflow.compile()

# ---------------------------------------------------------
# PRUEBA FINAL DEL AGENTE
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n--- INICIANDO AGENTE ---\n")
    
    # Probamos con Wikipedia
    test_inputs = [
        "¿Cuál es el clima en Bogotá?",
        "Cuanto es 20 mas 50?",
        "Quien fue Albert Einstein?", # Ahora debería ser 'wiki'
        "Hola, como estás?",
        "Explícame la teoría de la relatividad" # Debería ser 'wiki'
    ]
    
    
    # Ejecutamos el grafo
    for text in test_inputs:
        inputs = {"user_input": text, "intent": "", "output": ""}
        for output in app.stream(inputs):
            for key, value in output.items():
                print(f"Nodo '{key}': {value}")

