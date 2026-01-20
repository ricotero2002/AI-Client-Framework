# AI Client Framework

Un framework completo y extensible para orquestar múltiples LLMs (OpenAI, Gemini, Anthropic) con soporte nativo para **Prompt Engineering Estructurado**, **Chat con Persistencia**, **Sistema de Evaluación de Prompts**, **Tracing Avanzado** y **Workflows Agenciales**.

---

## 🎯 Core Features

### 1. **Multi-Provider Unified API**
Interfaz polimórfica para OpenAI (Responses API), Google Gemini (SDK 2.0) y Anthropic Claude.

### 2. **Structured Prompt Engine**
Clase `Prompt` robusta con:
- System instructions
- Few-shot examples
- Templates con `[[variables]]`
- Esquemas de salida estructurados (Pydantic)
- Tracking de uso y costos
- Versionado y mejora automática

### 3. **Chat System con Persistencia**
Sistema completo de chat con:
- Persistencia en SQLite
- Compresión automática de contexto
- Tracking de modelo y prompt por mensaje
- Historial completo de conversaciones

### 4. **Prompt Evaluation System (Evals)**
Sistema de evaluación de prompts con:
- Golden examples (test cases)
- Evaluación automática con LLM
- Feedback humano
- Mejora automática de prompts
- Versionado de prompts

### 5. **Observability (LangSmith)**
Integración nativa con LangSmith para tracing detallado de tokens, modelos y proveedores.

### 6. **Advanced Pricing & Counting**
Gestión centralizada de más de 60 modelos con pricing detallado (input, output, cached).

---

## 📁 Estructura del Proyecto

```
IA/
├── base_client.py              # Abstract Base Class para clientes
├── client_factory.py           # Factory para instanciación dinámica
├── openai_client.py            # Cliente OpenAI (Responses API)
├── gemini_client.py            # Cliente Google Gemini (SDK 2.0)
├── anthropic_client.py         # Cliente Anthropic Claude
├── openai_client_smith.py      # OpenAI con LangSmith tracing
├── gemini_client_smith.py      # Gemini con LangSmith tracing
├── prompt.py                   # Motor de prompts estructurados
├── chat.py                     # Sistema de chat con persistencia
├── database.py                 # ORM y gestión de base de datos
├── eval_database.py            # Extensiones para sistema de evaluación
├── prompt_evaluator.py         # Motor de evaluación de prompts
├── config.py                   # Configuración de modelos y pricing
├── compare_prompts.py          # Herramienta de comparación de prompts
├── interactive_chat_test.py    # Chat interactivo para testing
├── examples/
│   ├── chat_example.py         # Ejemplo de chat básico
│   ├── prompt_tracking_example.py  # Ejemplo de tracking de uso
│   ├── comedian_eval_example.py    # Ejemplo completo de evaluación
│   └── test_improvement.py     # Mejora de prompts con feedback
└── data/                       # Base de datos SQLite (auto-generada)
```

---

## 🚀 Quick Start

### 1. Instalación

```bash
pip install -r requirements.txt
```

### 2. Configuración (.env)

```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...

# Opcional para Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT="my-project"
```

### 3. Uso Básico

```python
from client_factory import create_client
from prompt import Prompt

# Crear cliente
client = create_client('gemini')
client.select_model('gemini-2.0-flash-exp')

# Crear prompt
prompt = Prompt()
prompt.set_system("Eres un asistente útil.")
prompt.set_user_input("¿Qué es Python?")

# Obtener respuesta
response, usage = client.get_response(prompt)
print(response)
```

---

## 📚 Guías de Uso Detalladas

### 🔹 Structured Outputs con Pydantic

Valida automáticamente respuestas JSON usando modelos Pydantic:

```python
from pydantic import BaseModel, Field

class BookInfo(BaseModel):
    title: str
    author: str
    summary: str = Field(description="Resumen breve del libro")

prompt = (
    Prompt()
    .set_system("Eres un experto bibliotecario.")
    .set_user_input("Dame información sobre 'Rayuela'")
    .set_output_schema(BookInfo)
)

response_json, usage = client.get_response(prompt)
book = BookInfo.model_validate_json(response_json)
print(book.title, book.author)
```

**Ejemplo completo:** `examples/prompt_tracking_example.py`

---

### 🔹 Chat con Persistencia

Sistema completo de chat con historial persistente y compresión automática:

```python
from chat import ChatSession
from client_factory import create_client
from prompt import Prompt

# Crear nueva conversación
chat = ChatSession(title="Mi Chat", max_messages=10)

# Configurar prompt
prompt = Prompt()
prompt.set_system("Eres un asistente experto en Python.")
prompt.save()

# Crear cliente
client = create_client('gemini')

# Conversación
chat.add_message('user', '¿Qué es una lista?')
response = chat.get_response(client, prompt)
print(response)

# Cargar conversación existente
chat2 = ChatSession.load(chat.conversation_id)
```

**Características:**
- ✅ Persistencia automática en SQLite
- ✅ Compresión de contexto cuando excede `max_messages`
- ✅ Tracking de modelo y prompt por mensaje
- ✅ Estadísticas de uso y costos

**Ejemplo completo:** `examples/chat_example.py`

**Herramienta interactiva:** `interactive_chat_test.py`

---

### 🔹 Prompt Tracking y Estadísticas

Trackea el uso de tus prompts y analiza costos:

```python
from prompt import Prompt

# Crear y guardar prompt
prompt = Prompt()
prompt.set_system("Eres un revisor de código.")
prompt.save()

# Usar el prompt
response, usage = client.get_response(prompt)

# Guardar estadísticas de uso
cost = client.estimate_cost(usage.prompt_tokens, usage.completion_tokens)
prompt.save_usage(
    model=client.current_model,
    input_tokens=usage.prompt_tokens,
    output_tokens=usage.completion_tokens,
    response=response,
    cost=cost.total_cost
)

# Ver estadísticas
stats = prompt.get_usage_stats()
print(f"Total llamadas: {stats['total_calls']}")
print(f"Costo total: ${stats['total_cost']:.6f}")
print(f"Promedio por llamada: ${stats['total_cost']/stats['total_calls']:.6f}")

# Estadísticas por modelo
model_stats = prompt.get_usage_by_model()
for model, data in model_stats.items():
    print(f"{model}: {data['calls']} llamadas, ${data['avg_cost']:.6f} promedio")
```

**Herramienta de comparación:** `compare_prompts.py`

```bash
python compare_prompts.py
```

Opciones:
1. Comparar todos los prompts
2. Ver estadísticas detalladas de un prompt
3. Comparar prompts por modelo específico

**Ejemplo completo:** `examples/prompt_tracking_example.py`

---

### 🔹 Sistema de Evaluación de Prompts (Evals)

Evalúa y mejora tus prompts automáticamente usando golden examples:

#### 1. Crear Prompt y Golden Examples

```python
from prompt import Prompt
from eval_database import get_eval_db

# Crear prompt
comedian = Prompt()
comedian.set_system(
    "Sos un comediante argentino. Generás chistes inteligentes "
    "con humor observacional sobre la vida cotidiana."
)
comedian.save()

# Agregar golden examples (test cases)
db = get_eval_db()
db.add_test_case(
    prompt_id=comedian.get_id(),
    input="Hacé un chiste sobre el subte",
    expected_output="El subte es el único lugar donde 'no hay lugar' "
                   "significa que hay 47 personas en un vagón para 20...",
    category="transporte",
    notes="Humor observacional sobre transporte público"
)
```

#### 2. Ejecutar Evaluación

```python
from prompt_evaluator import PromptEvaluator

# Crear evaluador
eval_client = create_client('gemini')
evaluator = PromptEvaluator(eval_client, evaluator_model='gemini-2.0-flash-exp')

# Obtener test cases
test_cases = db.get_test_cases(comedian.get_id())
test_cases_dict = [tc.to_dict() for tc in test_cases]

# Evaluar
test_client = create_client('gemini')
results = evaluator.batch_evaluate(
    comedian,
    test_cases_dict,
    test_client
)

# Ver reporte
report = evaluator.generate_report(results)
print(f"Score promedio: {report['avg_score']:.2f}")
print(f"Aprobados: {report['passed']}/{report['total']}")
```

#### 3. Agregar Feedback Humano

```python
# Actualizar con feedback humano
db.update_evaluation_human_feedback(
    eval_id=1,
    human_score=0.8,
    human_feedback="Buen chiste pero le falta más acidez"
)
```

#### 4. Mejorar Prompt Automáticamente

```python
from prompt_evaluator import PromptImprover

# Crear improver
improve_client = create_client('gemini')
improver = PromptImprover(improve_client, improver_model='gemini-2.0-flash-exp')

# Analizar fallas
failures = improver.analyze_failures(results, threshold=0.7)

# Generar mejoras
improvements = improver.generate_improvements(comedian, failures)

# Crear nueva versión
improved = improver.create_improved_version(comedian, improvements, version=2)
improved.save()

# Guardar versión
db.save_prompt_version(
    parent_prompt_id=comedian.get_id(),
    version=2,
    system_message=improvements['system_message'],
    few_shot_examples=[...],
    improvement_reason=improvements['explanation']
)
```

**Características del Sistema de Evaluación:**
- ✅ Golden examples como test cases
- ✅ Evaluación automática con LLM (structured output)
- ✅ Feedback humano opcional
- ✅ Mejora automática basada en fallas
- ✅ Versionado de prompts
- ✅ Tracking de evolución del prompt

**Ejemplo completo:** `examples/comedian_eval_example.py`

**Mejora con feedback:** `examples/test_improvement.py`

---

### 🔹 Few-Shot Learning

Enseña comportamientos específicos con ejemplos:

```python
prompt = Prompt()
prompt.set_system("Eres un traductor de jerga argentina.")

# Agregar ejemplos
prompt.add_few_shot_example(
    "Traducí: 'Che, vamos a morfar unas empanadas'",
    "Hey, let's go eat some empanadas"
)
prompt.add_few_shot_example(
    "Traducí: 'Estoy re cansado, boludo'",
    "I'm really tired, dude"
)

prompt.set_user_input("Traducí: 'Qué copado este lugar'")
response, _ = client.get_response(prompt)
```

---

### 🔹 Templates con Variables

Crea prompts reutilizables con variables:

```python
prompt = Prompt()
prompt.set_system("Eres un generador de emails profesionales.")
prompt.set_user_input(
    "Escribe un email para [[recipient]] sobre [[topic]]. "
    "El tono debe ser [[tone]]."
)

# Usar con diferentes valores
prompt.set_variables({
    'recipient': 'el equipo de ventas',
    'topic': 'los resultados del Q4',
    'tone': 'formal y motivador'
})

response, _ = client.get_response(prompt)
```

---

### 🔹 LangSmith Tracing

Activa tracing detallado para debugging:

```python
# Crear cliente con tracing
client = create_client('gemini', langsmith=True)

# Todas las llamadas se tracean automáticamente
response, usage = client.get_response(prompt)

# Ver en LangSmith dashboard:
# - Tokens usados
# - Costo
# - Latencia
# - Prompts completos
# - Respuestas
```

---

## 📊 Modelos Soportados

### OpenAI
- `gpt-5-nano`, `gpt-5-mini`, `gpt-4.5-preview`
- `o1`, `o1-mini`, `o3-mini`
- `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`

### Google Gemini
- `gemini-2.0-flash-exp`, `gemini-2.0-flash-lite`
- `gemini-2.5-flash`, `gemini-2.5-pro`
- `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-1.5-flash-8b`

### Anthropic Claude
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`
- `claude-3-opus-20240229`

**Pricing completo en:** `config.py`

---

## 🛠️ Herramientas Incluidas

### `compare_prompts.py`
Compara estadísticas de uso entre todos tus prompts:
- Costos totales y promedios
- Tokens por llamada
- Comparación por modelo
- Estadísticas detalladas

### `interactive_chat_test.py`
Chat interactivo para testing:
- Crear o cargar conversaciones
- Configurar prompts
- Comandos: `stats`, `history`, `clear`, `exit`

---

## 🧠 Workflows Agenciales (LangGraph)

El framework está optimizado para grafos de estado complejos. Ver `langgraph_prueba_2.py` para un ejemplo completo de workflow de escritura:

1. **Ideation**: Genera ángulos para un tema
2. **Outline**: Estructura con secciones
3. **Writing**: Genera contenido en paralelo
4. **Assembler**: Une las piezas
5. **Editor**: Refina tono y estilo

---

## 📖 Ejemplos de Uso

| Ejemplo | Descripción | Archivo |
|---------|-------------|---------|
| Chat básico | Sistema de chat con persistencia | `examples/chat_example.py` |
| Prompt tracking | Tracking de uso y costos | `examples/prompt_tracking_example.py` |
| Evaluación completa | Sistema de evals con golden examples | `examples/comedian_eval_example.py` |
| Mejora de prompts | Mejora automática con feedback | `examples/test_improvement.py` |
| Chat interactivo | Herramienta de testing | `interactive_chat_test.py` |
| Comparación | Comparar prompts y costos | `compare_prompts.py` |

---

## 🔧 Arquitectura

### Patrón de Herencia para Tracing
- **Clientes base** (`OpenAIClient`, `GeminiClient`): Livianos, sin decoradores
- **Clientes Smith** (`OpenAIClientSmith`, `GeminiClientSmith`): Con decoradores `@traceable` y metadatos

### Base de Datos
- **SQLite** para persistencia
- **SQLAlchemy ORM** para modelos
- **Tablas**: `conversations`, `messages`, `prompts`, `prompt_usage`, `test_cases`, `evaluations`, `prompt_versions`

### Evaluación de Prompts
- **Structured Output** con Pydantic para scoring confiable
- **Feedback humano** opcional para mejorar precisión
- **Mejora automática** usando LLM para analizar fallas

---

## 📝 Licencia

MIT License

---

## 🚀 Roadmap


---

*Desarrollado para el futuro de la IA Agencial*
