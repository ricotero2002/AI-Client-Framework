# Migración de Ollama a GPT-4o en Graph RAG

## 🎯 Resumen

Se migró el sistema de Graph RAG de usar **Ollama (llama2)** a **GPT-4o via client_factory** para la extracción de entidades y expansión de sinónimos.

## ✅ Cambios Realizados

### 1. Nuevo Wrapper LLM para LlamaIndex

**Archivo:** [`src/graph_db/llamaindex_llm_wrapper.py`](file:///c:/Users/Agustin/Desktop/Agustin/IA/rag_practice_project/src/graph_db/llamaindex_llm_wrapper.py)

- Implementa `CustomLLM` de LlamaIndex
- Integra `client_factory` (OpenAI/Gemini clients)
- Soporta LangSmith tracing
- Compatible con PropertyGraphIndex

**Uso:**
```python
from src.graph_db.llamaindex_llm_wrapper import create_llm_for_llamaindex

llm = create_llm_for_llamaindex(
    provider="openai",
    model="gpt-4o",
    temperature=0.0,
    langsmith=True  # Habilita tracing
)
```

### 2. Actualización de GraphBuilder

**Archivo:** [`src/graph_db/graph_builder.py`](file:///c:/Users/Agustin/Desktop/Agustin/IA/rag_practice_project/src/graph_db/graph_builder.py)

**Cambios:**
- ❌ Removido: `from llama_index.llms.ollama import Ollama`
- ✅ Agregado: `from src.graph_db.llamaindex_llm_wrapper import create_llm_for_llamaindex`
- ❌ Removido parámetro: `ollama_model`
- ✅ Agregados parámetros: `llm_provider`, `llm_model`, `langsmith`

**Antes:**
```python
builder = GraphBuilder(
    ollama_model="llama2"
)
```

**Ahora:**
```python
builder = GraphBuilder(
    llm_provider="openai",
    llm_model="gpt-4o",
    langsmith=False  # o True para tracing
)
```

### 3. Actualización de setup_graph.py

**Archivo:** [`setup_graph.py`](file:///c:/Users/Agustin/Desktop/Agustin/IA/rag_practice_project/setup_graph.py)

**Cambios:**
```python
# Antes
builder = GraphBuilder(
    neo4j_manager=neo4j_manager,
    show_progress=True
)

# Ahora
builder = GraphBuilder(
    neo4j_manager=neo4j_manager,
    llm_provider="openai",
    llm_model="gpt-4o",
    langsmith=False,  # Cambiar a True para LangSmith
    show_progress=True
)
```

### 4. Actualización de Configuración

**Archivo:** [`config/config.py`](file:///c:/Users/Agustin/Desktop/Agustin/IA/rag_practice_project/config/config.py#L66-L93)

**Nuevas variables:**
```python
# Provider y modelo para Graph RAG
GRAPH_EXTRACTION_LLM_PROVIDER = os.getenv("GRAPH_EXTRACTION_LLM_PROVIDER", "openai")
GRAPH_EXTRACTION_MODEL = os.getenv("GRAPH_EXTRACTION_MODEL", "gpt-4o")
```

**Nota:** Ollama config se marca como OBSOLETO pero se mantiene por compatibilidad.

### 5. GraphRetriever (Sin Cambios)

**Archivo:** [`src/graph_db/graph_retriever.py`](file:///c:/Users/Agustin/Desktop/Agustin/IA/rag_practice_project/src/graph_db/graph_retriever.py)

No requiere cambios - usa automáticamente el LLM configurado en el `PropertyGraphIndex`.

---

## 🔧 Configuración Necesaria

### Variables de Entorno (.env)

```bash
# OpenAI API Key (necesario para GPT-4o)
OPENAI_API_KEY=tu_openai_api_key_aqui

# Neo4j Aura
NEO4J_URI=neo4j+s://tu-instancia.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=tu_password
NEO4J_DATABASE=neo4j

# Graph RAG Configuration
GRAPH_EXTRACTION_LLM_PROVIDER=openai
GRAPH_EXTRACTION_MODEL=gpt-4o

# LangSmith (opcional, para tracing)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=tu_langsmith_key
```

---

## 🚀 Uso Actualizado

### Construcción del Grafo

```bash
# Con GPT-4o (default ahora)
python setup_graph.py --sample 20

# Con muestra más grande
python setup_graph.py --sample 100
```

### Programático

```python
from src.graph_db.graph_builder import GraphBuilder
from src.graph_db.neo4j_manager import Neo4jManager

# Crear builder con GPT-4o
builder = GraphBuilder(
    llm_provider="openai",
    llm_model="gpt-4o",
    langsmith=True,  # Habilitar tracing
    show_progress=True
)

# Preparar y construir
documents = builder.prepare_documents(df)
index = builder.build_graph(documents, reset=True)
```

### Con Otros Modelos

```python
# Usar GPT-4o-mini (más rápido, más barato)
builder = GraphBuilder(
    llm_provider="openai",
    llm_model="gpt-4o-mini",
    langsmith=False
)

# Usar Gemini
builder = GraphBuilder(
    llm_provider="gemini",
    llm_model="gemini-2.0-flash",
    langsmith=False
)
```

---

## 💰 Comparación de Costos

### Ollama (Antes)
- **Costo monetario:** $0 (modelo local)
- **Costo computacional:** Alto uso de CPU/RAM
- **Velocidad:** Depende del hardware local
- **Calidad:** Variable según modelo

### GPT-4o (Ahora)
- **Costo monetario:** ~$2.50 / 1M input tokens, ~$10 / 1M output tokens
- **Costo computacional:** Ninguno (API)
- **Velocidad:** Rápida y consistente
- **Calidad:** Excelente para extracción de entidades

### Ejemplo de Costo Real

Para **100 recetas**:
- Tokens estimados: ~50,000 (input) + ~20,000 (output)
- Costo aproximado: **$0.33**

Para **1,000 recetas**:
- Costo aproximado: **$3.30**

---

## ⚙️ Ventajas de la Migración

### 1. **Calidad Superior**
- GPT-4o es mucho mejor para extracción de entidades
- Identifica relaciones más complejas
- Menos errores en parsing

### 2. **Velocidad Consistente**
- No depende del hardware local
- Procesamiento paralelo en la nube
- Sin variabilidad por carga del sistema

### 3. **LangSmith Integration**
- Tracing completo de extracciones
- Debug de queries complejas
- Análisis de costos precisos

### 4. **Flexibilidad**
- Fácil cambiar a GPT-4o-mini (más barato)
- Fácil cambiar a Gemini
- Mismo código para todos

### 5. **Sin Dependencias Locales**
- No necesitas Ollama instalado
- No necesitas descargar modelos grandes
- Funciona en cualquier máquina

---

## 🧪 Testing

### Test del Wrapper

```bash
# Test básico del wrapper
python src/graph_db/llamaindex_llm_wrapper.py
```

### Test de Construcción

```bash
# Test con muestra muy pequeña
python setup_graph.py --sample 5
```

Esto debería:
1. ✅ Conectar a Neo4j Aura
2. ✅ Inicializar GPT-4o via client_factory
3. ✅ Extraer entidades de 5 recetas
4. ✅ Crear nodos y relaciones en Neo4j
5. ✅ Guardar embeddings en ChromaDB

---

## 📊 Verificación

### 1. Verificar Wrapper Funciona

```python
from src.graph_db.llamaindex_llm_wrapper import create_llm_for_llamaindex

llm = create_llm_for_llamaindex("openai", "gpt-4o")
response = llm.complete("Extract entities: quinoa salad recipe")
print(response.text)
```

### 2. Verificar Neo4j

```cypher
// En Neo4j Browser
MATCH (n) RETURN n LIMIT 25
MATCH ()-[r]->() RETURN type(r), count(*) as count
```

### 3. Verificar LangSmith (si está habilitado)

- Ir a https://smith.langchain.com
- Ver traces de extracciones
- Analizar costos y latencias

---

## 🐛 Troubleshooting

### Error: "OpenAI API Key not configured"

```bash
# Verifica que .env tenga:
OPENAI_API_KEY=sk-...
```

### Error: "ClientFactory not found"

Asegúrate que `client_factory.py` esté en el directorio correcto:
```
c:\Users\Agustin\Desktop\Agustin\IA\client_factory.py
```

### Error: "Import Error on llamaindex_llm_wrapper"

Verifica que el path esté correcto:
```python
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
```

---

## 📝 Próximos Pasos

1. ✅ Test con muestra pequeña (`--sample 10`)
2. ✅ Verificar calidad de entidades extraídas en Neo4j
3. ✅ Comparar costos reales vs estimados
4. ✅ Decidir si usar GPT-4o-mini para producción (más barato)
5. ✅ Habilitar LangSmith si se necesita debugging

---

## 🔄 Rollback (Si es necesario)

Si necesitas volver a Ollama:

1. Revierte cambios en `graph_builder.py`:
```python
from llama_index.llms.ollama import Ollama

builder = GraphBuilder(
    ollama_model="llama2"
)
```

2. Asegúrate que Ollama esté corriendo:
```bash
ollama list
```

---

**Migración completada el:** 2026-01-29  
**Versión:** Graph RAG v2.0 con GPT-4o
