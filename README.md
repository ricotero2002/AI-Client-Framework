# AI Client Framework

Un framework agnóstico y extensible para orquestar múltiples LLMs (OpenAI, Gemini, etc.) con soporte nativo para **Prompt Engineering Estructurado**, **Caching Optimization** y **Workflows Agenciales**.

## 🎯 Core Features

- **Multi-Provider Unified API**: Interfaz polimórfica para OpenAI y Gemini.
- **Structured Prompt Engine**: Clase `Prompt` robusta con separación lógica de contexto (System, Few-Shot, User).
- **Advanced Caching Strategy**: Análisis de tokens estáticos/dinámicos para maximizar el Cache Hit Ratio (Context Caching).
- **Structured Outputs (JSON/Pydantic)**: Validación de esquemas de salida y parsing automático integrado.
- **Template System**: Interpolación de variables `[[variable]]` y validación de integridad.
- **LangGraph Ready**: Integración directa para construir grafos de estado y agentes complejos.

## 📁 Tech Stack & Structure

```
IA/
├── client_factory.py       # Factory Pattern para instanciación dinámica de proveedores
├── prompt.py               # Motor de prompts estructurados, validación y templates
├── base_client.py          # Abstract Base Class (ABC) para estandarización de contratos
├── prompt_optimizer.py     # Análisis de tokens y heurísticas de caching
├── langgraph_prueba.py     # Implementación de referencia para flujos agenciales
└── config.py               # Gestión centralizada de modelos y pricing
```

## 🚀 Quick Start

### 1. Instalación
```bash
pip install -r requirements.txt
```

### 2. Configuración (.env)
```env
OPENAI_API_KEY=-...
GEMINI_API_KEY=...
```

### 3. Usage: Structured Prompting & Pydantic
Generación de contenido con validación de esquema estricta.

```python
from client_factory import create_client
from prompt import Prompt
from pydantic import BaseModel

# Definir esquema de salida esperado
class AnalysisResult(BaseModel):
    sentiment: str
    key_points: list[str]
    confidence_score: float

client = create_client('gemini') # o 'openai'
client.select_model('gemini-1.5-pro')

# Construcción del Prompt Estructurado
prompt = (
    Prompt()
    .set_system("Eres un analista de datos senior.")
    .add_few_shot_example(
        user="Analiza: 'El producto es lento pero funcional'", 
        assistant='{"sentiment": "neutral", "confidence_score": 0.8}'
    )
    .set_user_input("Analiza este feedback: [[feedback]]")
    .set_variable("feedback", "La nueva UI es increíble y muy rápida.")
    .set_output_schema(AnalysisResult) # Pydantic binding
)

# Ejecución
response, metadata = client.get_response(
    prompt, 
    response_schema=prompt.get_output_schema()
)

print(response) # Instancia validada de AnalysisResult o dict
```

### 4. Usage: Agentic Workflow (LangGraph)
Ejemplo de integración en grafos de estado (`langgraph_prueba.py`).

```python
def ideation_node(state: AgentState):
    client = ClientFactory.create_client('openai')
    prompt = Prompt().set_system("Generate innovative ideas...").set_user_input(state['topic'])
    response, _ = client.get_response(prompt)
    return {"idea": response}

workflow = StateGraph(AgentState)
workflow.add_node("ideation", ideation_node)
# ... compilar y ejecutar
```

## � Performance & Optimization

- **Token Counting**: Integración con `tiktoken` (OpenAI) y APIs nativas.
- **Cost Estimation**: Estimación en tiempo real basada en pricing configurable (`config.py`).
- **Cache Analytics**: `client.optimize_prompt_for_caching(messages)` analiza el payload para recomendar estrategias de `TTL` y orden de mensajes.

## 🤝 Extensibility

Para agregar un nuevo proveedor (ej. Claude), implementar `BaseAIClient` y registrar en `ClientFactory`. El `Prompt` class es agnóstico al modelo.

---
*License: MIT | Contribuciones bienvenidas mediante PRs.*
