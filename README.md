# AI Client Framework

Un framework agnóstico y extensible para orquestar múltiples LLMs (OpenAI, Gemini, etc.) con soporte nativo para **Prompt Engineering Estructurado**, **Tracing Avanzado** y **Workflows Agenciales Complejos**.

## 🎯 Core Features

- **Multi-Provider Unified API**: Interfaz polimórfica perfeccionada para OpenAI (vía Responses API) y Google Gemini (vía `google-genai` SDK).
- **Structured Prompt Engine**: Clase `Prompt` robusta con soporte para `system_instruction`, `few-shot examples`, templates con `[[variables]]` y esquemas de salida.
- **Observability (LangSmith)**: Integración nativa con LangSmith para tracing detallado, metadatos de tokens, modelos y proveedores.
- **Agentic Orchestration (LangGraph)**: Diseño optimizado para grafos de estado complejos con nodos especializados y operaciones de mapeo.
- **Advanced Pricing & Counting Engine**: Gestión centralizada de más de 60 modelos con pricing detallado (input, output, cached) en `config.py`.
- **Structured Outputs (Pydantic)**: Validación estricta y automática de respuestas JSON usando modelos Pydantic directamente en el motor de prompts.

## 📁 Tech Stack & Structure

```
IA/
├── base_client.py           # Abstract Base Class para estandarización de contratos
├── client_factory.py        # Factory para instanciación dinámica y selección de modo (Smith/Regular)
├── openai_client.py         # Cliente especializado para OpenAI (Responses API)
├── gemini_client.py         # Cliente especializado para Google Gemini (SDK 2.0)
├── openai_client_smith.py   # Variante con Tracing para OpenAI
├── gemini_client_smith.py   # Variante con Tracing para Gemini
├── prompt.py                # Motor de prompts estructurados y validación
├── config.py                # Base de datos de modelos (GPT-5, O-Series, Gemini 2.0) y pricing
└── langgraph_prueba_2.py    # Workflow agencial completo (Ideación -> Outline -> Writing -> Edit)
```

## 🚀 Quick Start

### 1. Configuración (.env)
```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
# Opcional para Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT="my-project"
```

### 2. Usage: Structured Output & LangSmith
```python
from client_factory import create_client
from prompt import Prompt
from pydantic import BaseModel, Field

class BookInfo(BaseModel):
    title: str
    author: str
    summary: str = Field(description="Un resumen breve del libro")

# langsmith=True activa automáticamente la variante Smith del cliente
client = create_client('gemini', langsmith=True)
client.select_model('gemini-2.0-flash-lite')

prompt = (
    Prompt()
    .set_system("Eres un experto bibliotecario.")
    .set_user_input("Dame información sobre el libro 'Rayuela'")
    .set_output_schema(BookInfo)
)

response_json, usage = client.get_response(prompt)
print(response_json) # JSON parseado automáticamente
```

## 🧠 Workflows Agenciales (LangGraph)

El framework brilla en implementaciones de grafos. El archivo `langgraph_prueba_2.py` implementa un flujo de escritura profesional:

1.  **Ideation**: Genera y selecciona el mejor ángulo para un tema.
2.  **Outline**: Crea una estructura de 3 a 5 secciones usando **Structured Output**.
3.  **Writing**: Genera contenido detallado para cada sección en paralelo.
4.  **Assembler**: Une las piezas manteniendo la coherencia.
5.  **Editor**: Refina el tono y estilo (con lógica de retroalimentación).

## 📊 Modelos Soportados

Soporte integrado para más de 60 modelos, incluyendo:
- **OpenAI**: `gpt-5-nano`, `gpt-5-mini`, `gpt-4.5-preview`, `o1`, `o3-mini`, `gpt-4o`.
- **Gemini**: `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-pro`, `gemini-1.5-flash-8b`.

## 🛠️ Tracing & Debugging

El framework utiliza un patrón de **Herencia Especializada** para el tracing:
- Los clientes base (`OpenAIClient`, `GeminiClient`) son livianos y sin decoradores.
- Los clientes Smith (`OpenAIClientSmith`, `GeminiClientSmith`) inyectan decoradores `@traceable` y metadatos detallados de tokens/costo a LangSmith sin ensuciar la lógica base del usuario.

---
*License: MIT | Desarrollado para el futuro de la IA Agencial.*
