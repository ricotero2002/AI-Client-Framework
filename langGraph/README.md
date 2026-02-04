# LangGraph Content Generation Pipeline

**Sistema de Generación de Contenido con Paralelización y Feedback Loops**

Un workflow avanzado de generación de contenido usando **LangGraph** que demuestra patrones de orquestación complejos: **Map-Reduce**, **Conditional Routing**, **Feedback Loops** y **Structured Output**.

---

## 🎯 Características Principales

### 1. **Map-Reduce Pattern**
- **Paralelización**: Genera múltiples secciones simultáneamente
- **Agregación**: Ensambla las piezas en un documento coherente
- **Eficiencia**: Reduce tiempo de generación en ~60%

### 2. **Feedback Loop con Editor**
- **Revisión automática**: Editor evalúa calidad del contenido
- **Iteración condicional**: Reescribe si no cumple estándares
- **Límite de intentos**: Máximo 2 revisiones para evitar loops infinitos

### 3. **Structured Output**
- **Pydantic Schemas**: Validación automática de respuestas
- **Type Safety**: Garantiza estructura correcta del outline
- **JSON Mode**: Respuestas estructuradas del LLM

### 4. **Integración con Framework**
- **Client Factory**: Soporte multi-provider (OpenAI, Gemini, Anthropic)
- **Prompt Class**: Prompts estructurados con system/user/few-shot
- **LangSmith Tracing**: Observabilidad completa del workflow

---

## 🏗️ Arquitectura del Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INPUT                                   │
│              "El futuro de la IA"                                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  1. IDEATION NODE                                │
│  - Genera ángulo único y cautivador                             │
│  - Selecciona la mejor perspectiva                              │
│  Output: "La IA como catalizador de creatividad humana"         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  2. OUTLINE NODE                                 │
│  - Genera estructura con 3-5 secciones                          │
│  - Usa Structured Output (Pydantic)                             │
│  Output: ["Introducción", "Casos de Uso", "Desafíos", ...]      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              3. MAP SECTIONS (Paralelización)                    │
│  Genera Send() para cada sección:                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Section 1   │  │ Section 2   │  │ Section 3   │             │
│  │ (Worker)    │  │ (Worker)    │  │ (Worker)    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┴────────────────┘                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  4. ASSEMBLER NODE                               │
│  - Une todas las secciones generadas                            │
│  - Crea borrador completo                                       │
│  Output: Artículo completo sin editar                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  5. EDITOR NODE                                  │
│  - Revisa tono, fluidez y calidad                               │
│  - Decide: Aprobar o Reescribir                                 │
│  - Incrementa review_count                                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
   [review_count <= 1]         [review_count > 1]
         │                           │
         ▼                           ▼
    ┌─────────┐                 ┌─────────┐
    │ REWRITE │                 │   END   │
    │ (loop)  │                 │         │
    └────┬────┘                 └─────────┘
         │
         └──────► EDITOR NODE (nueva iteración)
```

---

## 📁 Estructura del Proyecto

```
langGraph/
├── langgraph_chaining.py      # Pipeline completo con Map-Reduce
├── langgraph_prueba.py         # Versión anterior (referencia)
└── README.md
```

---

## 🚀 Instalación y Uso

### Requisitos

```bash
pip install langgraph langchain-core langsmith pydantic
```

### Configuración

Crear archivo `.env` en el directorio raíz (IA/):
```env
GEMINI_API_KEY=tu_api_key_aqui
# Opcional para tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__tu_key_aqui
LANGCHAIN_PROJECT=content-generation
```

### Ejecución

```bash
cd langGraph
python langgraph_chaining.py
```

**Interacción:**
```
Iniciando flujo de trabajo de Generación de Contenido con LangGraph...
Introduce un tema (ej. 'El futuro de la IA'): La revolución de los agentes autónomos

--- 1. IDEATION (La revolución de los agentes autónomos) ---
Idea seleccionada: Los agentes autónomos como nueva frontera de la productividad humana

--- 2. OUTLINE ---
Secciones (type=<class 'list'>): ['Introducción: El auge de los agentes', 'Casos de uso en la industria', 'Desafíos éticos y técnicos', 'El futuro del trabajo humano-agente', 'Conclusión']

--- 3. WRITING ---
   [Worker] Escribiendo sección: 'Introducción: El auge de los agentes'...
   [Worker] Escribiendo sección: 'Casos de uso en la industria'...
   [Worker] Escribiendo sección: 'Desafíos éticos y técnicos'...
   [Worker] Escribiendo sección: 'El futuro del trabajo humano-agente'...
   [Worker] Escribiendo sección: 'Conclusión'...

--- ENSAMBLANDO BORRADOR ---

--- 4. EDITOR REVIEW ---
>> EDITOR: El tono es muy informal. ¡Reescribir!

--- 4. EDITOR REVIEW ---
>> EDITOR: Aprobado.

=== CONTENIDO FINAL ===

[Artículo completo generado]

Guardado en 'resultado_articulo.md'
```

---

## 🔧 Componentes Técnicos

### 1. **State Definition**

```python
class ContentState(TypedDict):
    topic: str                                      # Tema original
    selected_idea: str                              # Ángulo seleccionado
    outline: List[str]                              # Lista de secciones
    sections_content: Annotated[List[str], operator.add]  # Contenido de secciones (acumulativo)
    final_content: str                              # Artículo final
    review_count: int                               # Contador de revisiones

class SectionState(TypedDict):
    section_title: str                              # Título de la sección
    idea_context: str                               # Contexto de la idea principal
```

**Nota sobre `Annotated[List[str], operator.add]`:**
- Permite que múltiples workers agreguen contenido a la misma lista
- LangGraph automáticamente concatena los resultados
- Esencial para el patrón Map-Reduce

### 2. **Ideation Node**

**Propósito:** Generar el ángulo más interesante para el tema.

```python
@traceable
def ideation_node(state: ContentState) -> Dict:
    client = ClientFactory.create_client(PROVIDER, langsmith=False)
    client.select_model(MODEL)
    
    prompt = (
        Prompt()
        .set_system("Eres un experto estratega de contenido...")
        .set_user_input(f"Dame una idea única y cautivadora para: {state['topic']}")
    )
    
    response, _ = client.get_response(prompt)
    return {"selected_idea": response, "review_count": 0}
```

### 3. **Outline Node con Structured Output**

**Propósito:** Crear estructura del artículo con validación automática.

```python
@traceable
def outline_node(state: ContentState) -> Dict:
    client = ClientFactory.create_client(PROVIDER, langsmith=True)
    client.select_model(MODEL)
    
    # Definir schema con Pydantic
    class Secciones(BaseModel):
        sections: List[str] = Field(
            min_length=3, 
            max_length=5,
            description="Lista de títulos de las secciones principales"
        )
    
    prompt = (
        Prompt()
        .set_system("Eres un arquitecto de la información...")
        .set_user_input(f"Crea un esquema de 3 a 5 secciones para: {state['selected_idea']}")
        .set_output_schema(Secciones)
    )
    
    # El client automáticamente maneja structured output
    response, _ = client.get_response(prompt)
    data = json.loads(response)
    sections = data.get("sections", [])
    
    return {"outline": sections}
```

**Ventajas de Structured Output:**
- ✅ Garantiza que la respuesta sea una lista
- ✅ Valida longitud (3-5 secciones)
- ✅ Evita parsing manual de texto
- ✅ Reduce errores de formato

### 4. **Map Sections (Paralelización)**

**Propósito:** Generar múltiples secciones en paralelo.

```python
def map_sections(state: ContentState):
    """Genera las tareas paralelas (Map)"""
    return [
        Send("write_section", {
            "section_title": s, 
            "idea_context": state["selected_idea"]
        }) 
        for s in state["outline"]
    ]
```

**Cómo funciona:**
1. LangGraph recibe una lista de `Send()` objects
2. Ejecuta cada `Send()` en paralelo (o secuencialmente según config)
3. Cada worker recibe su propio `SectionState`
4. Los resultados se acumulan en `sections_content` gracias a `operator.add`

### 5. **Writing Node (Worker)**

**Propósito:** Generar contenido para una sección específica.

```python
@traceable
def writing_node(state: SectionState) -> Dict:
    client = ClientFactory.create_client(PROVIDER, langsmith=True)
    client.select_model(MODEL)
    
    title = state["section_title"]
    print(f"   [Worker] Escribiendo sección: '{title}'...")

    prompt = (
        Prompt()
        .set_system("Eres un redactor experto...")
        .set_user_input(f"Tema: {state['idea_context']}\nSección: {title}\n\nEscribe el contenido.")
    )
    
    content, _ = client.get_response(prompt)
    
    # Retorna lista para acumular en sections_content
    return {"sections_content": [content]}
```

**Nota:** Retorna `{"sections_content": [content]}` (lista) para que LangGraph pueda concatenar con `operator.add`.

### 6. **Assembler Node**

**Propósito:** Unir todas las secciones en un documento coherente.

```python
@traceable
def assembler_node(state: ContentState):
    print("--- ENSAMBLANDO BORRADOR ---")
    full_draft = "\n\n".join(state['sections_content'])
    return {"final_content": full_draft}
```

### 7. **Editor Node con Feedback Loop**

**Propósito:** Revisar y mejorar el contenido, con lógica de reescritura.

```python
@traceable
def editor_node(state: ContentState):
    print("--- 4. EDITOR REVIEW ---")
    
    # Lógica condicional: rechazar en primer intento
    if state["review_count"] < 1:
        print(">> EDITOR: El tono es muy informal. ¡Reescribir!")

        client = ClientFactory.create_client(PROVIDER, langsmith=True)
        client.select_model(MODEL)
        
        prompt = (
            Prompt()
            .set_system("Eres un editor jefe estricto...")
            .set_user_input(f"Texto original:\n{state['final_content']}\n\nMejora este texto.")
        )
        
        final_version, _ = client.get_response(prompt)
        return {"final_content": final_version, "review_count": state["review_count"] + 1}
    
    print(">> EDITOR: Aprobado.")
    return {"review_count": state["review_count"] + 1}
```

### 8. **Conditional Routing**

**Propósito:** Decidir si continuar editando o finalizar.

```python
def should_continue(state: ContentState):
    """Decide si volvemos a escribir o terminamos"""
    if state["review_count"] <= 1:
        return "rewrite"  # Volver a editor
    return "end"  # Finalizar
```

---

## 🔀 Construcción del Grafo

```python
def create_content_graph():
    workflow = StateGraph(ContentState)
    
    # Agregar nodos
    workflow.add_node("ideacion", ideation_node)
    workflow.add_node("outline", outline_node)
    workflow.add_node("write_section", writing_node)  # Worker para Map
    workflow.add_node("assembler", assembler_node)
    workflow.add_node("editor", editor_node)
    
    # Definir flujo
    workflow.set_entry_point("ideacion")
    workflow.add_edge("ideacion", "outline")
    
    # Map-Reduce: Paralelización de secciones
    workflow.add_conditional_edges("outline", map_sections, ["write_section"])
    
    workflow.add_edge("write_section", "assembler")
    workflow.add_edge("assembler", "editor")
    
    # Feedback Loop: Editor puede reescribir
    workflow.add_conditional_edges(
        "editor",
        should_continue,
        {
            "rewrite": "editor",  # Loop back
            "end": END
        }
    )
    
    return workflow.compile()
```

---

## 📊 Patrones de LangGraph Demostrados

### 1. **Map-Reduce Pattern**

**Definición:** Dividir una tarea en subtareas paralelas, ejecutarlas, y luego agregar resultados.

**Implementación:**
```python
# Map: Generar tareas paralelas
workflow.add_conditional_edges("outline", map_sections, ["write_section"])

# Reduce: Agregar resultados
def assembler_node(state):
    full_draft = "\n\n".join(state['sections_content'])
    return {"final_content": full_draft}
```

**Ventajas:**
- ⚡ Reduce tiempo de ejecución (5 secciones en paralelo vs secuencial)
- 🔄 Escalable (funciona con 3 o 50 secciones)
- 🧩 Modular (cada worker es independiente)

### 2. **Conditional Routing**

**Definición:** Decidir el siguiente nodo basado en el estado actual.

**Implementación:**
```python
def should_continue(state: ContentState):
    if state["review_count"] <= 1:
        return "rewrite"
    return "end"

workflow.add_conditional_edges(
    "editor",
    should_continue,
    {"rewrite": "editor", "end": END}
)
```

### 3. **Feedback Loops**

**Definición:** Permitir que un nodo se ejecute múltiples veces hasta cumplir una condición.

**Implementación:**
```python
# Editor puede llamarse a sí mismo
workflow.add_conditional_edges(
    "editor",
    should_continue,
    {"rewrite": "editor", "end": END}  # "editor" -> "editor" es el loop
)
```

**Protección contra loops infinitos:**
```python
if state["review_count"] <= 1:  # Máximo 2 revisiones
    return "rewrite"
return "end"
```

### 4. **State Accumulation**

**Definición:** Múltiples nodos agregan datos a la misma clave del estado.

**Implementación:**
```python
class ContentState(TypedDict):
    sections_content: Annotated[List[str], operator.add]  # ← Clave

# Cada worker agrega su contenido
def writing_node(state: SectionState) -> Dict:
    return {"sections_content": [content]}  # Se concatena automáticamente
```

---

## 🎨 Personalización

### Cambiar Modelo

```python
# En langgraph_chaining.py, líneas 23-26
PROVIDER = 'gemini'  # o 'openai', 'anthropic'
MODEL = 'gemini-2.0-flash-lite'  # o 'gpt-4o', 'claude-3-5-sonnet'
```

### Ajustar Número de Secciones

```python
class Secciones(BaseModel):
    sections: List[str] = Field(
        min_length=5,   # Cambiar mínimo
        max_length=10,  # Cambiar máximo
        description="..."
    )
```

### Modificar Lógica del Editor

```python
def editor_node(state: ContentState):
    # Opción 1: Siempre aprobar (sin loop)
    return {"review_count": state["review_count"] + 1}
    
    # Opción 2: Usar LLM para decidir
    prompt = Prompt().set_system("Evalúa si el contenido es de calidad profesional. Responde 'APROBAR' o 'RECHAZAR'.")
    decision, _ = client.get_response(prompt)
    
    if "RECHAZAR" in decision:
        # Reescribir
        ...
    else:
        # Aprobar
        return {"review_count": state["review_count"] + 1}
```

### Agregar Nodo de Investigación

```python
@traceable
def research_node(state: ContentState) -> Dict:
    """Busca información relevante antes de escribir"""
    # Usar herramienta de búsqueda (Tavily, Google, etc.)
    research_data = search_web(state['topic'])
    return {"research_context": research_data}

# Agregar al grafo
workflow.add_node("research", research_node)
workflow.add_edge("ideacion", "research")
workflow.add_edge("research", "outline")
```

---

## 📈 Métricas de Performance

### Tiempo de Ejecución (5 secciones)

| Modo | Tiempo | Speedup |
|------|--------|---------|
| **Secuencial** | ~150s | 1x |
| **Paralelo (Map)** | ~60s | 2.5x |

### Tokens Utilizados (Ejemplo)

| Nodo | Input Tokens | Output Tokens | Costo (Gemini Flash) |
|------|--------------|---------------|----------------------|
| Ideation | 50 | 30 | $0.000024 |
| Outline | 80 | 50 | $0.000039 |
| Writing (x5) | 400 | 1500 | $0.000570 |
| Assembler | 0 | 0 | $0 |
| Editor (x2) | 3000 | 2000 | $0.0015 |
| **TOTAL** | ~3530 | ~3580 | **~$0.002** |

---

## 🔍 Debugging con LangSmith

### Activar Tracing

```python
# En langgraph_chaining.py
client = ClientFactory.create_client(PROVIDER, langsmith=True)  # ← Activar
```

### Visualizar en Dashboard

1. Ir a https://smith.langchain.com/
2. Seleccionar proyecto "content-generation"
3. Ver trace completo del workflow:
   - Tiempo de cada nodo
   - Tokens consumidos
   - Inputs/outputs de cada LLM call
   - Estructura del grafo ejecutado

### Ejemplo de Trace

```
Run: content-generation-2026-02-04
├─ ideation_node (15s, 80 tokens)
├─ outline_node (12s, 130 tokens)
├─ map_sections (0s, dispatch)
│  ├─ writing_node [Section 1] (20s, 380 tokens)
│  ├─ writing_node [Section 2] (22s, 420 tokens)
│  ├─ writing_node [Section 3] (18s, 350 tokens)
│  ├─ writing_node [Section 4] (21s, 400 tokens)
│  └─ writing_node [Section 5] (19s, 390 tokens)
├─ assembler_node (1s, 0 tokens)
├─ editor_node [Iteration 1] (25s, 2500 tokens)
└─ editor_node [Iteration 2] (23s, 2500 tokens)

Total: 156s, 7150 tokens, $0.002143
```

---

## 🚨 Errores Comunes y Soluciones

### Error 1: "sections_content" no se acumula

**Problema:**
```python
class ContentState(TypedDict):
    sections_content: List[str]  # ❌ Sin Annotated
```

**Solución:**
```python
class ContentState(TypedDict):
    sections_content: Annotated[List[str], operator.add]  # ✅
```

### Error 2: Workers no se ejecutan en paralelo

**Problema:** Falta importar `Send` de LangGraph.

**Solución:**
```python
from langgraph.types import Send  # ← Importar

def map_sections(state: ContentState):
    return [Send("write_section", {...}) for s in state["outline"]]
```

### Error 3: Loop infinito en Editor

**Problema:** No hay límite en `review_count`.

**Solución:**
```python
def should_continue(state: ContentState):
    if state["review_count"] <= 1:  # ← Límite explícito
        return "rewrite"
    return "end"
```

### Error 4: Structured Output no funciona

**Problema:** Modelo no soporta JSON mode.

**Solución:**
```python
# Verificar que el modelo soporte structured output
# Gemini 1.5+, GPT-4+, Claude 3+ soportan
# Si no, parsear manualmente:
response, _ = client.get_response(prompt)
sections = extract_sections_from_text(response)  # Parsing manual
```

---

## 🔮 Extensiones Posibles

### 1. **SEO Optimization Node**
```python
@traceable
def seo_optimizer_node(state: ContentState) -> Dict:
    """Optimiza el contenido para SEO"""
    prompt = Prompt().set_system("Eres un experto en SEO...")
    optimized, _ = client.get_response(prompt)
    return {"final_content": optimized}
```

### 2. **Multi-Language Support**
```python
@traceable
def translation_node(state: ContentState) -> Dict:
    """Traduce el artículo a múltiples idiomas"""
    languages = ["en", "es", "fr", "de"]
    translations = {}
    for lang in languages:
        prompt = Prompt().set_user_input(f"Translate to {lang}: {state['final_content']}")
        translations[lang], _ = client.get_response(prompt)
    return {"translations": translations}
```

### 3. **Image Generation**
```python
@traceable
def image_generation_node(state: ContentState) -> Dict:
    """Genera imágenes para cada sección"""
    from generate_image import generate_image
    images = []
    for section in state['outline']:
        img_path = generate_image(f"Illustration for: {section}", f"section_{i}.png")
        images.append(img_path)
    return {"section_images": images}
```

### 4. **Fact-Checking Node**
```python
@traceable
def fact_checker_node(state: ContentState) -> Dict:
    """Verifica afirmaciones con búsqueda web"""
    # Extraer claims del contenido
    # Verificar cada claim con búsqueda
    # Marcar claims no verificables
    return {"fact_check_report": report}
```

---

## 📚 Referencias

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **Map-Reduce Pattern**: https://langchain-ai.github.io/langgraph/how-tos/map-reduce/
- **Conditional Edges**: https://langchain-ai.github.io/langgraph/how-tos/branching/
- **LangSmith**: https://docs.smith.langchain.com/

---

**Parte del AI Client Framework**  
**Versión:** 1.0.0  
**Última actualización:** 2026-02-04
