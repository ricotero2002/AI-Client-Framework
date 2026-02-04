# AI Client Framework & Agentic Systems

**Framework completo y extensible para orquestar LLMs, construir agentes autónomos, y desarrollar sistemas de IA de producción**

Un ecosistema integrado que incluye: wrapper unificado multi-provider, sistema de prompts estructurados, agentes con supervisión humana, pipelines de generación de contenido, servidores MCP, sistemas RAG avanzados, y herramientas de evaluación.

---

## 🎯 Proyectos Principales

### 1. **🤖 Human-in-the-Loop IDL Agent** ⭐⭐⭐
**Agente Autónomo con Supervisión Humana y Sistema de Rollback**

Agente inteligente basado en LangGraph y MCP que ejecuta comandos de terminal de forma autónoma, con aprobación humana para operaciones peligrosas, sistema de backup/restore automático, y capacidad de aprendizaje de errores pasados.

**Características:**
- ✅ Arquitectura de doble agente (Planner + Executor)
- ✅ Supervisión humana selectiva (solo para operaciones unsafe)
- ✅ Backup automático antes de cambios destructivos
- ✅ Rollback inteligente si el usuario rechaza cambios
- ✅ Aprendizaje de errores (Golden Dataset)
- ✅ Protección contra alucinaciones de paths
- ✅ Auditoría completa en `execution_audit.log`

**Tecnologías:** LangGraph, MCP, Gemini 2.5, Pydantic

📂 **Directorio:** `Human_IDL/`  
📖 **README:** [Human_IDL/README.md](Human_IDL/README.md)

**Ejemplo de Uso:**
```bash
python client.py server_terminal.py
```

---

### 2. **🔧 AI Client Framework (Core)** ⭐⭐⭐
**Wrapper Unificado Multi-Provider con Prompt Engineering Avanzado**

Framework robusto para orquestar múltiples LLMs (OpenAI, Gemini, Anthropic) con soporte nativo para prompts estructurados, chat persistente, evaluación de prompts, y tracing avanzado.

#### **Nuevas Funcionalidades del Wrapper**

##### **Prompt Class - Soporte para Chats**
```python
from prompt import Prompt

# Crear prompt con historial de conversación
prompt = Prompt()
prompt.set_system("Eres un asistente experto en Python")

# Agregar mensajes al historial
prompt.add_user_message("¿Qué es una lista?")
prompt.add_assistant_message("Una lista es una estructura de datos...")
prompt.add_user_message("Dame un ejemplo")

# Obtener respuesta (mantiene contexto)
response, _ = client.get_response(prompt)
```

**Características del Chat:**
- ✅ Historial de conversación completo
- ✅ Soporte para mensajes de herramientas (tool messages)
- ✅ Límite configurable de mensajes en contexto
- ✅ Compatible con todos los providers

##### **Gemini Client - Cambio Automático de Modelo**
```python
from gemini_client import GeminiClient

client = GeminiClient()
client.select_model('gemini-2.5-flash')

# Si el modelo alcanza rate limit o está sobrecargado,
# automáticamente cambia a un modelo alternativo similar
response, _ = client.get_response(prompt)
# ⚠️  Rate limit hit for gemini-2.5-flash. Trying fallback models...
# 🔄 Attempting with gemini-2.0-flash-exp...
# ✅ Success with gemini-2.0-flash-exp!
```

**Sistema de Fallbacks:**
- 🔄 Fallbacks inteligentes basados en pricing similar
- 🔄 Detección automática de rate limits (429) y sobrecarga (503)
- 🔄 Cambio permanente al modelo alternativo si funciona
- 🔄 Top 5 alternativas ordenadas por cercanía de precio

##### **Otras Mejoras del Wrapper**

**Structured Output con Pydantic:**
```python
from pydantic import BaseModel

class BookInfo(BaseModel):
    title: str
    author: str
    summary: str

prompt = Prompt()
prompt.set_output_schema(BookInfo)
response, _ = client.get_response(prompt)

# Validación automática
is_valid, data, error = prompt.validate_response(response)
```

**Tool Support:**
```python
# Agregar herramientas al prompt
prompt.set_tools(gemini_tools)

# Convertir herramientas LangChain a formato Gemini
from prompt import convert_langchain_tool_to_gemini
gemini_tools = [convert_langchain_tool_to_gemini(t) for t in lc_tools]
```

**Template Variables:**
```python
prompt.set_user_input("Analiza este texto: [[text]]")
prompt.set_variable("text", "Hello world")
```

**File Attachments:**
```python
prompt.attach_image("screenshot.png", description="Error screenshot")
prompt.attach_pdf("document.pdf")
```

#### **Core Features**

1. **Multi-Provider Unified API**
   - OpenAI (Responses API)
   - Google Gemini (SDK 2.0)
   - Anthropic Claude

2. **Structured Prompt Engine**
   - System instructions
   - Few-shot examples
   - Templates con `[[variables]]`
   - Esquemas de salida estructurados (Pydantic)
   - Tracking de uso y costos
   - Versionado y mejora automática

3. **Chat System con Persistencia**
   - Persistencia en SQLite
   - Compresión automática de contexto
   - Tracking de modelo y prompt por mensaje
   - Historial completo de conversaciones

4. **Prompt Evaluation System (Evals)**
   - Golden examples (test cases)
   - Evaluación automática con LLM
   - Feedback humano
   - Mejora automática de prompts
   - Versionado de prompts

5. **Observability (LangSmith)**
   - Integración nativa con LangSmith
   - Tracing detallado de tokens, modelos y proveedores

6. **Advanced Pricing & Counting**
   - Gestión centralizada de más de 60 modelos
   - Pricing detallado (input, output, cached)

**Archivos Core:**
- `base_client.py` - Abstract Base Class
- `client_factory.py` - Factory para instanciación dinámica
- `openai_client.py` - Cliente OpenAI
- `gemini_client.py` - Cliente Gemini con fallbacks
- `prompt.py` - Motor de prompts estructurados (47KB, 1331 líneas)
- `chat.py` - Sistema de chat con persistencia
- `database.py` - ORM y gestión de base de datos
- `prompt_evaluator.py` - Motor de evaluación
- `config.py` - Configuración de modelos y pricing

**Ejemplos:**
- `examples/chat_example.py` - Chat básico
- `examples/prompt_tracking_example.py` - Tracking de uso
- `examples/comedian_eval_example.py` - Evaluación completa
- `interactive_chat_test.py` - Chat interactivo

---

### 3. **📊 LangGraph Content Generation Pipeline** ⭐⭐
**Sistema de Generación de Contenido con Paralelización y Feedback Loops**

Workflow avanzado de generación de contenido que demuestra patrones de orquestación complejos: Map-Reduce, Conditional Routing, Feedback Loops y Structured Output.

**Características:**
- ✅ **Map-Reduce Pattern**: Genera múltiples secciones en paralelo (~60% más rápido)
- ✅ **Feedback Loop**: Editor revisa y reescribe automáticamente
- ✅ **Structured Output**: Validación con Pydantic
- ✅ **LangSmith Tracing**: Observabilidad completa

**Pipeline:**
1. **Ideation**: Genera ángulo único para el tema
2. **Outline**: Estructura con 3-5 secciones (structured output)
3. **Writing**: Genera secciones en paralelo (Map)
4. **Assembler**: Une las piezas (Reduce)
5. **Editor**: Revisa y mejora (Feedback Loop)

📂 **Directorio:** `langGraph/`  
📖 **README:** [langGraph/README.md](langGraph/README.md)

**Ejemplo de Uso:**
```bash
python langgraph_chaining.py
```

---

### 4. **🔐 NeMo Defense Bot** ⭐⭐
**Sistema de Defensa para LLMs con Guardrails Multicapa**

Sistema de guardrails implementado con NVIDIA NeMo Guardrails para proteger modelos de lenguaje contra ataques adversariales, jailbreaks, inyecciones y exposición de PII.

**Características:**
- ✅ **Detección de Jailbreaks**: NVIDIA NeMo Guard API
- ✅ **Moderación de Contenido**: Nemotron Safety Guard 8B
- ✅ **Control de Tópicos**: Restricción de dominios
- ✅ **Protección de PII**: GLiNER para enmascaramiento automático
- ✅ **Detección de Inyecciones**: SQL, XSS, Template, Code
- ✅ **Guardrails Personalizados**: Regex patterns, topic blockers

**Resultados de Evaluación:**
- **Garak (PromptInject)**: 100% de bloqueo (DEFCON 5)
- **Moderation Eval**: 6/6 casos bloqueados correctamente

📂 **Directorio:** `nemo_defense_bot/`  
📖 **README:** [nemo_defense_bot/README.md](nemo_defense_bot/README.md)

**Ejemplo de Uso:**
```bash
.\start_nemo_server.ps1
```

---

### 5. **🌐 MCP Servers Suite** ⭐⭐

#### **5.1 GitHub PR Review + Notion**
Servidor MCP para análisis automático de Pull Requests con integración a Notion.

**Características:**
- ✅ Fetch automático de PRs de GitHub
- ✅ Análisis de diffs línea por línea
- ✅ Creación de documentación en Notion
- ✅ Compatible con Claude Desktop

📂 **Directorio:** `MCP/PR_Review/`  
📖 **README:** [MCP/PR_Review/README.md](MCP/PR_Review/README.md)

**Herramientas MCP:**
- `fetch_pr(repo_owner, repo_name, pr_number)`: Obtiene cambios del PR
- `create_notion_page(title, content)`: Crea página en Notion

#### **5.2 Multi-MCP Server con FastAPI**
Servidor FastAPI que expone múltiples servidores MCP vía HTTP.

**Características:**
- ✅ Múltiples servidores MCP en una app
- ✅ Endpoints HTTP independientes
- ✅ Gestión unificada de lifecycle
- ✅ Fácil extensión con nuevos servidores

📂 **Directorio:** `MCP/Multi_mcp/`  
📖 **README:** [MCP/Multi_mcp/README.md](MCP/Multi_mcp/README.md)

**Servidores Incluidos:**
- `/echo/mcp`: Herramientas de ejemplo (echo, reverse)
- `/math/mcp`: Operaciones matemáticas (add, multiply)

**Ejemplo de Uso:**
```bash
python main.py
curl -X POST http://localhost:8000/math/mcp/call \
  -d '{"tool": "add_tool", "arguments": {"a": 10, "b": 32}}'
```

---

### 6. **📚 RAG Practice Project** ⭐⭐
**Sistema RAG Multi-Estrategia con Evaluación Comparativa**

Implementación completa de múltiples estrategias RAG (Naive, Advanced, Agentic, Graph) con sistema de evaluación y comparación de performance.

**Estrategias Implementadas:**
- **Naive RAG**: Retrieval básico + generación
- **Advanced RAG**: Query expansion + re-ranking + prompt engineering
- **Agentic RAG**: Agente con herramientas (retrieve, search, calculate)
- **Graph RAG**: Knowledge Graph con Neo4j

**Características:**
- ✅ Evaluación automática con métricas (Faithfulness, Relevancy, etc.)
- ✅ Comparación de estrategias
- ✅ Análisis de trade-offs (calidad vs velocidad)
- ✅ Visualización de resultados

📂 **Directorio:** `rag_practice_project/`  
📖 **README:** [rag_practice_project/README.md](rag_practice_project/README.md)

**Ejemplo de Uso:**
```bash
python run_all_experiments.py
python compare_systems.py
```

---

### 7. **🎯 Gbeder System** ⭐
**Sistema de Benchmarking de Agentes con MCP**

Sistema completo para evaluar agentes de IA usando el benchmark GAIA, con integración de herramientas MCP (Tavily search, calculadora, etc.).

**Características:**
- ✅ Benchmark GAIA (General AI Assistants)
- ✅ Integración con Tavily para búsqueda web
- ✅ Herramientas MCP personalizadas
- ✅ Análisis de resultados y métricas

📂 **Directorio:** `gbeder_system/`  
📖 **README:** [gbeder_system/README.md](gbeder_system/README.md)

---

## 📁 Estructura del Repositorio

```
IA/
├── 🤖 Human_IDL/                    # Agente autónomo con supervisión humana
│   ├── client.py                    # Agente principal (LangGraph)
│   ├── server_terminal.py           # Servidor MCP
│   └── README.md
│
├── 📊 langGraph/                    # Pipelines de generación de contenido
│   ├── langgraph_chaining.py        # Pipeline con Map-Reduce
│   └── README.md
│
├── 🔐 nemo_defense_bot/             # Sistema de guardrails para LLMs
│   ├── config/                      # Configuración de guardrails
│   ├── eval_outputs/                # Resultados de evaluaciones
│   └── README.md
│
├── 🌐 MCP/                          # Servidores MCP
│   ├── PR_Review/                   # GitHub PR + Notion
│   ├── Multi_mcp/                   # Multi-server FastAPI
│   └── Custom_Client/               # Cliente MCP personalizado
│
├── 📚 rag_practice_project/         # Sistema RAG multi-estrategia
│   ├── src/rag_strategies/          # Implementaciones de RAG
│   ├── results/                     # Resultados de experimentos
│   └── README.md
│
├── 🎯 gbeder_system/                # Benchmarking de agentes
│   ├── agents.py                    # Agentes con MCP
│   ├── eval.py                      # Sistema de evaluación
│   └── README.md
│
├── 🔧 Core Framework/               # Wrapper de LLMs
│   ├── base_client.py               # Abstract base class
│   ├── client_factory.py            # Factory pattern
│   ├── openai_client.py             # Cliente OpenAI
│   ├── gemini_client.py             # Cliente Gemini (con fallbacks)
│   ├── prompt.py                    # Motor de prompts (47KB)
│   ├── chat.py                      # Sistema de chat
│   ├── database.py                  # Persistencia SQLite
│   ├── prompt_evaluator.py          # Evaluación de prompts
│   └── config.py                    # Configuración y pricing
│
├── 📝 examples/                     # Ejemplos de uso
│   ├── chat_example.py
│   ├── prompt_tracking_example.py
│   ├── comedian_eval_example.py
│   └── test_improvement.py
│
├── 🛠️ Herramientas/
│   ├── compare_prompts.py           # Comparación de prompts
│   ├── interactive_chat_test.py     # Chat interactivo
│   └── prueba_modelos.py            # Testing de modelos
│
├── .env                             # Variables de entorno
├── requirements.txt                 # Dependencias
└── README.md                        # Este archivo
```

---

## 🚀 Quick Start

### 1. Instalación

```bash
# Clonar repositorio
git clone <repository-url>
cd IA

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración

Crear archivo `.env` en la raíz:
```env
# LLM APIs
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...

# Opcional: LangSmith Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=my-project

# Opcional: MCP Servers
GITHUB_TOKEN=ghp_...
NOTION_API_KEY=secret_...
NOTION_PAGE_ID=...

# Opcional: NeMo Guardrails
NVIDIA_API_KEY=nvapi-...
```

### 3. Uso Básico del Framework

```python
from client_factory import create_client
from prompt import Prompt

# Crear cliente
client = create_client('gemini')
client.select_model('gemini-2.5-flash')

# Crear prompt
prompt = Prompt()
prompt.set_system("Eres un asistente útil.")
prompt.set_user_input("¿Qué es Python?")

# Obtener respuesta
response, usage = client.get_response(prompt)
print(response)

# Ver costos
cost = client.estimate_cost(usage.prompt_tokens, usage.completion_tokens)
print(f"Costo: ${cost.total_cost:.6f}")
```

---

## 📚 Guías de Uso Detalladas

### 🔹 Structured Outputs con Pydantic

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

### 🔹 Chat con Persistencia

```python
from chat import ChatSession

# Crear nueva conversación
chat = ChatSession(title="Mi Chat", max_messages=10)

# Configurar prompt
prompt = Prompt()
prompt.set_system("Eres un asistente experto en Python.")
prompt.save()

# Conversación
chat.add_message('user', '¿Qué es una lista?')
response = chat.get_response(client, prompt)
print(response)

# Cargar conversación existente
chat2 = ChatSession.load(chat.conversation_id)
```

### 🔹 Prompt Tracking y Estadísticas

```python
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
```

### 🔹 Sistema de Evaluación de Prompts

```python
from prompt import Prompt
from eval_database import get_eval_db
from prompt_evaluator import PromptEvaluator

# 1. Crear prompt
comedian = Prompt()
comedian.set_system("Sos un comediante argentino...")
comedian.save()

# 2. Agregar golden examples
db = get_eval_db()
db.add_test_case(
    prompt_id=comedian.get_id(),
    input="Hacé un chiste sobre el subte",
    expected_output="El subte es el único lugar...",
    category="transporte"
)

# 3. Ejecutar evaluación
evaluator = PromptEvaluator(eval_client)
test_cases = db.get_test_cases(comedian.get_id())
results = evaluator.batch_evaluate(comedian, test_cases, test_client)

# 4. Ver reporte
report = evaluator.generate_report(results)
print(f"Score promedio: {report['avg_score']:.2f}")
```

### 🔹 LangSmith Tracing

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

## 🚀 Roadmap

### Framework Core
- [ ] Soporte para más providers (Cohere, AI21, etc.)
- [ ] Streaming de respuestas
- [ ] Batch processing optimizado
- [ ] Cache distribuido con Redis

### Agentes
- [ ] Multi-agent orchestration
- [ ] Herramientas de búsqueda web integradas
- [ ] Soporte para código ejecutable
- [ ] Integración con bases de datos

### RAG
- [ ] Hybrid search (keyword + semantic)
- [ ] Multi-modal RAG (imágenes, videos)
- [ ] Adaptive retrieval strategies
- [ ] Query routing automático

### MCP
- [ ] Más servidores MCP (Jira, Linear, Slack, etc.)
- [ ] Auto-discovery de servidores
- [ ] Dashboard de monitoreo
- [ ] Versioning de herramientas

### Evaluación
- [ ] Más métricas de evaluación
- [ ] A/B testing de prompts
- [ ] Regression testing automático
- [ ] Benchmark suite completo

---