# RAG Practice Project - Sistema Multi-Estrategia con Dataset de Recetas Veganas

## 📋 Resumen Ejecutivo

Proyecto de investigación que implementa y compara **6 estrategias diferentes de RAG** (Retrieval-Augmented Generation) utilizando un dataset de recetas vegetarianas. El objetivo principal es analizar el trade-off entre **calidad de respuesta**, **latencia** y **costo** en diferentes arquitecturas RAG.

**Resultado Principal**: Graph RAG obtuvo la mejor calidad (0.654) pero con 13× más latencia que Naive RAG, revelando que el cuello de botella está en el **retrieval**, no en la generación.

---

## 🎯 Objetivos del Proyecto

1. **Implementar 6 estrategias RAG** con complejidad creciente
2. **Evaluar objetivamente** usando DeepEval (LLM-as-a-Judge)
3. **Analizar métricas** de calidad, latencia y costo
4. **Identificar bottlenecks** en el pipeline RAG
5. **Generar recomendaciones** para optimización

---

## 📊 Dataset Utilizado

### Fuente de Datos
- **Nombre**: Vegan Recipes Dataset
- **Formato Original**: CSV
- **Procesamiento**: Convertido a Parquet para eficiencia
- **Ubicación**: `data/processed/vegan_recipes_processed.parquet`

### Estructura del Dataset
```python
Columnas principales:
- title: Nombre de la receta
- ingredients: Lista de ingredientes
- instructions: Pasos de preparación
- nutrition: Información nutricional (calorías, proteínas, etc.)
- tags: Categorías (sopa, ensalada, curry, etc.)
```

### Estadísticas
- **Total de recetas**: ~50 recetas veganas
- **Campos indexados**: title, ingredients, instructions, nutrition
- **Embeddings**: Generados con modelo de OpenAI `text-embedding-3-small`

### Casos de Prueba
Se crearon **6 consultas de prueba** con ground truth para evaluación:

```python
TEST_QUERIES = [
    {
        "query": "Menciona exactamente 3 recetas que contengan garbanzos.",
        "expected_output": "1) Chickpea & Potato Curry, 2) Roasted Curried Chickpeas..."
    },
    {
        "query": "Dame solo una receta de sopa que tenga menos de 200 calorías.",
        "expected_output": "Creamy Cauliflower Pakora Soup (135 calorías)"
    },
    # ... 4 consultas más
]
```

---

## 🛠️ Estrategias RAG Implementadas

### 1. **No RAG (Baseline)**
**Archivo**: `src/rag_strategies/no_rag.py`

**Descripción**: El modelo responde únicamente con su conocimiento pre-entrenado, sin acceso al dataset.

**Implementación**:
```python
class NoRAGStrategy(BaseRAGStrategy):
    def generate_response(self, query: str) -> Dict[str, Any]:
        prompt = Prompt()
        prompt.set_system("Eres un asistente de cocina vegana.")
        prompt.set_user_input(query)
        
        response, usage = self.client.get_response(prompt)
        return {"response": response, "context": []}
```

**Propósito**: Establecer baseline para medir el valor agregado del RAG.

---

### 2. **Naive RAG**
**Archivo**: `src/rag_strategies/naive_rag.py`

**Descripción**: Implementación más simple de RAG: búsqueda vectorial + generación directa.

**Pipeline**:
1. **Retrieval**: Búsqueda de similitud coseno en ChromaDB
2. **Generation**: Prompt con contexto recuperado

**Implementación**:
```python
class NaiveRAGStrategy(BaseRAGStrategy):
    def __init__(self, top_k=3):
        self.vector_db = ChromaManager()
        self.top_k = top_k
    
    def generate_response(self, query: str):
        # Paso 1: Recuperar documentos
        results = self.vector_db.query(query, n_results=self.top_k)
        
        # Paso 2: Construir prompt
        context = "\n\n".join([doc["content"] for doc in results])
        prompt = Prompt()
        prompt.set_system("Responde usando SOLO el contexto proporcionado.")
        prompt.set_user_input(f"Contexto:\n{context}\n\nPregunta: {query}")
        
        # Paso 3: Generar respuesta
        response, usage = self.client.get_response(prompt)
        return {"response": response, "context": results}
```

**Resultados**:
- ⚡ **Latencia**: 1.4s (el más rápido)
- 💰 **Costo**: Muy bajo
- 📊 **Calidad**: 0.421 (inaceptable)
- ❌ **Recall**: 0.08 (pierde 92% de información relevante)

**Diagnóstico**: Excelente para prototipos, pero calidad insuficiente para producción.

---

### 3. **Advanced RAG**
**Archivo**: `src/rag_strategies/advanced_rag.py`

**Descripción**: Implementa técnicas avanzadas de retrieval: query expansion, re-ranking y prompt engineering mejorado.

**Pipeline**:
1. **Query Expansion**: LLM genera múltiples variaciones de la consulta
2. **Multi-Query Retrieval**: Búsqueda con cada variación
3. **Re-Ranking**: Cross-encoder reordena por relevancia
4. **Generation**: Prompt estructurado con few-shot examples

**Implementación Detallada**:

```python
class AdvancedRAGStrategy(BaseRAGStrategy):
    def __init__(self, top_k=20):
        self.vector_db = ChromaManager()
        self.expansion_client = create_client("gemini")
        self.expansion_client.select_model("gemini-2.5-flash")
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        self.top_k = top_k
    
    def _expand_query(self, query: str) -> List[str]:
        """Genera 3 variaciones de la consulta"""
        prompt = Prompt()
        prompt.set_system("""Genera 3 variaciones de la consulta para mejorar retrieval.
        Considera: sinónimos, reformulaciones, descomposición en sub-preguntas.""")
        prompt.set_user_input(query)
        
        response, _ = self.expansion_client.get_response(prompt)
        # Parsear las 3 queries expandidas
        return [query] + parse_expanded_queries(response)
    
    def _rerank_documents(self, query: str, docs: List[Dict]) -> List[Dict]:
        """Re-rankea usando cross-encoder"""
        pairs = [[query, doc["content"]] for doc in docs]
        scores = self.reranker.predict(pairs)
        
        # Ordenar por score descendente
        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, score in ranked]
    
    def generate_response(self, query: str):
        # Paso 1: Query Expansion
        expanded_queries = self._expand_query(query)
        
        # Paso 2: Multi-Query Retrieval
        all_docs = []
        for exp_query in expanded_queries:
            results = self.vector_db.query(exp_query, n_results=self.top_k)
            all_docs.extend(results)
        
        # Deduplicar
        unique_docs = deduplicate_by_content(all_docs)
        
        # Paso 3: Re-Ranking
        reranked_docs = self._rerank_documents(query, unique_docs)[:10]
        
        # Paso 4: Generation con Few-Shot
        context = format_context(reranked_docs)
        prompt = Prompt()
        prompt.set_system(ADVANCED_SYSTEM_PROMPT)
        prompt.add_few_shot_example(
            user="Dame recetas con tofu",
            assistant="Aquí tienes 2 recetas con tofu: 1) Tofu Scramble..."
        )
        prompt.set_user_input(f"Contexto:\n{context}\n\nPregunta: {query}")
        
        response, usage = self.client.get_response(prompt)
        
        return {
            "response": response,
            "context": reranked_docs,
            "extra_info": {
                "expanded_queries": expanded_queries,
                "reranking_scores": [doc["rerank_score"] for doc in reranked_docs]
            }
        }
```

**Resultados**:
- 📊 **Calidad**: 0.5 (decepcionante dado el costo)
- 💰 **Costo**: $0.017 (el más caro)
- ⚠️ **Precision**: 0.333 (bajo ROI)
- 🔍 **Recall**: 0.25 (mejor que Naive, pero insuficiente)

**Diagnóstico**: El re-ranker no está optimizado. Necesita fine-tuning para dominio culinario.

---

### 4. **Agentic RAG**
**Archivo**: `src/rag_strategies/agentic_rag.py`

**Descripción**: Agente autónomo con LangGraph que decide dinámicamente qué herramientas usar.

**Arquitectura**:
```
┌─────────────┐
│   Planner   │ ──> Analiza query y decide estrategia
└──────┬──────┘
       │
       ├──> Tool 1: vector_search(query, top_k)
       ├──> Tool 2: filter_by_nutrition(calories, protein)
       ├──> Tool 3: get_recipe_by_name(name)
       └──> Tool 4: list_recipes_by_tag(tag)
```

**Implementación con LangGraph**:

```python
from langgraph.graph import StateGraph, END

class AgenticRAGStrategy(BaseRAGStrategy):
    def __init__(self, max_iterations=15):
        self.vector_db = ChromaManager()
        self.max_iterations = max_iterations
        self.graph = self._build_graph()
    
    def _build_graph(self):
        # Definir herramientas
        tools = [
            Tool(
                name="vector_search",
                func=self.vector_db.query,
                description="Busca recetas por similitud semántica"
            ),
            Tool(
                name="filter_nutrition",
                func=self._filter_by_nutrition,
                description="Filtra por calorías, proteínas, etc."
            )
        ]
        
        # Crear agente ReAct
        workflow = StateGraph(AgentState)
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("executor", self._executor_node)
        workflow.add_node("synthesizer", self._synthesizer_node)
        
        workflow.add_edge("planner", "executor")
        workflow.add_conditional_edges(
            "executor",
            self._should_continue,
            {"continue": "planner", "finish": "synthesizer"}
        )
        workflow.add_edge("synthesizer", END)
        
        return workflow.compile()
    
    def _planner_node(self, state: AgentState):
        """Decide qué herramienta usar"""
        prompt = Prompt()
        prompt.set_system(AGENTIC_PLANNER_PROMPT)
        prompt.set_tools(self.tools)
        prompt.set_user_input(state["query"])
        
        response, _ = self.client.get_response(prompt)
        tool_call = parse_tool_call(response)
        
        return {"tool_call": tool_call, "iteration": state["iteration"] + 1}
    
    def _executor_node(self, state: AgentState):
        """Ejecuta la herramienta seleccionada"""
        tool_name = state["tool_call"]["name"]
        tool_args = state["tool_call"]["args"]
        
        result = self.tools[tool_name](**tool_args)
        
        return {"observations": state["observations"] + [result]}
    
    def generate_response(self, query: str):
        initial_state = {
            "query": query,
            "observations": [],
            "iteration": 0
        }
        
        final_state = self.graph.invoke(initial_state)
        return {
            "response": final_state["final_answer"],
            "context": final_state["observations"]
        }
```

**Resultados**:
- ✅ **Fidelidad**: 1.0 (no alucina)
- ❌ **Relevancia Contextual**: 0.190 (trae mucho "ruido")
- 📊 **Calidad General**: 0.6
- 🔄 **Iteraciones Promedio**: 3-5

**Diagnóstico**: Excelente para tareas multi-paso, pero necesita mejor filtrado de contexto.

---

### 5. **Graph RAG**
**Archivo**: `src/rag_strategies/graph_rag.py`

**Descripción**: Utiliza un Knowledge Graph (Neo4j) para entender relaciones entre entidades (recetas, ingredientes, nutrición).

**Arquitectura del Grafo**:
```
(Recipe) -[:CONTAINS]-> (Ingredient)
(Recipe) -[:HAS_NUTRITION]-> (Nutrition)
(Recipe) -[:TAGGED_AS]-> (Tag)
(Ingredient) -[:PAIRS_WITH]-> (Ingredient)
```

**Pipeline**:
1. **Graph Construction**: LLM extrae entidades y relaciones
2. **Hybrid Retrieval**: Combina búsqueda vectorial + Cypher queries
3. **Path Finding**: Encuentra conexiones entre conceptos
4. **Generation**: Contexto enriquecido con relaciones

**Implementación**:

```python
from neo4j import GraphDatabase
from llama_index.core import KnowledgeGraphIndex

class GraphRAGStrategy(BaseRAGStrategy):
    def __init__(self, graph_index, graph_retriever, top_k=10):
        self.graph_index = graph_index
        self.graph_retriever = graph_retriever
        self.top_k = top_k
    
    def generate_response(self, query: str):
        # Paso 1: Determinar tipo de consulta
        query_type = self._classify_query(query)
        
        if query_type == "relationship":
            # Usar Cypher query para relaciones
            results = self.graph_retriever.query(query)
        else:
            # Usar retrieval híbrido
            results = self.graph_retriever.retrieve(query, top_k=self.top_k)
        
        # Paso 2: Enriquecer con contexto de grafo
        enriched_context = self._enrich_with_graph(results)
        
        # Paso 3: Generar respuesta
        prompt = Prompt()
        prompt.set_system(GRAPH_RAG_SYSTEM_PROMPT)
        prompt.set_user_input(f"Contexto:\n{enriched_context}\n\nPregunta: {query}")
        
        response, usage = self.client.get_response(prompt)
        
        return {"response": response, "context": results}
    
    def _enrich_with_graph(self, results):
        """Agrega relaciones del grafo al contexto"""
        enriched = []
        for result in results:
            # Obtener nodos relacionados
            related = self.graph_index.get_related_nodes(result["node_id"])
            enriched.append({
                "content": result["content"],
                "relationships": related
            })
        return enriched
```

**Construcción del Grafo**:

```python
# setup_graph.py
from src.graph_db.graph_builder import GraphBuilder

builder = GraphBuilder(neo4j_manager, llm_model="gemini-2.5-pro")

# Extraer entidades y relaciones con LLM
for recipe in recipes_df.iterrows():
    entities = builder.extract_entities(recipe)
    relationships = builder.extract_relationships(recipe, entities)
    
    # Insertar en Neo4j
    builder.add_to_graph(entities, relationships)
```

**Resultados**:
- 🏆 **Calidad**: 0.654 (la mejor)
- ✅ **Fidelidad**: 0.958 (casi perfecta)
- ⚠️ **Latencia**: 18.6s ± 12s (13× más lento que Naive)
- 💰 **Costo**: Alto (múltiples llamadas LLM)

**Diagnóstico**: Ideal para investigación offline y reportes complejos. Necesita optimización de latencia.

---

## 📈 Evaluación con DeepEval

### Framework de Evaluación
**Herramienta**: DeepEval (LLM-as-a-Judge)  
**Archivo**: `src/evaluation/evaluator.py`

### Métricas Implementadas

#### 1. **Contextual Precision**
```python
ContextualPrecisionMetric(threshold=0.5, model=eval_llm)
```
**Definición**: ¿Los documentos recuperados son relevantes para la query?  
**Fórmula**: `relevant_docs / total_retrieved_docs`

#### 2. **Contextual Recall**
```python
ContextualRecallMetric(threshold=0.5, model=eval_llm)
```
**Definición**: ¿Se recuperó toda la información necesaria del ground truth?  
**Fórmula**: `info_in_context / info_in_ground_truth`

#### 3. **Contextual Relevancy**
```python
ContextualRelevancyMetric(threshold=0.5, model=eval_llm)
```
**Definición**: ¿El contexto recuperado es relevante (sin ruido)?  
**Fórmula**: `relevant_sentences / total_sentences_in_context`

#### 4. **Faithfulness**
```python
FaithfulnessMetric(threshold=0.5, model=eval_llm)
```
**Definición**: ¿La respuesta está respaldada por el contexto (no alucina)?  
**Fórmula**: `claims_supported / total_claims`

#### 5. **Answer Relevancy**
```python
AnswerRelevancyMetric(threshold=0.5, model=eval_llm)
```
**Definición**: ¿La respuesta es relevante a la pregunta original?  
**Fórmula**: Similitud semántica entre query y respuesta

### Implementación del Evaluador

```python
class RAGEvaluator:
    def __init__(self):
        self.eval_llm = DeepEvalCustomLLM(
            provider="openai",
            model_name="gpt-4o-mini"
        )
        
        self.metrics = {
            "contextual_precision": ContextualPrecisionMetric(...),
            "contextual_recall": ContextualRecallMetric(...),
            "contextual_relevancy": ContextualRelevancyMetric(...),
            "faithfulness": FaithfulnessMetric(...),
            "answer_relevancy": AnswerRelevancyMetric(...)
        }
    
    def evaluate_response(self, query, response, context, expected_output):
        test_case = LLMTestCase(
            input=query,
            actual_output=response,
            retrieval_context=context,
            expected_output=expected_output
        )
        
        results = {}
        for name, metric in self.metrics.items():
            metric.measure(test_case)
            results[name] = {
                "score": metric.score,
                "reason": metric.reason
            }
        
        results["overall_score"] = mean([m.score for m in self.metrics.values()])
        return results
```

### Ejecución de Experimentos

```python
# run_all_experiments.py
runner = ExperimentRunner(strategies, TEST_QUERIES)
results = runner.run_experiments()

# Resultados guardados en JSON
{
    "timestamp": "2026-01-30T15:30:00",
    "strategy": "graph_rag",
    "query": "Menciona 3 recetas con garbanzos",
    "response": "1) Chickpea & Potato Curry...",
    "quality_metrics": {
        "contextual_precision": {"score": 0.8, "reason": "..."},
        "contextual_recall": {"score": 0.33, "reason": "..."},
        "faithfulness": {"score": 0.95, "reason": "..."},
        "overall_score": 0.654
    },
    "latency_ms": 18600,
    "cost_usd": 0.015
}
```

---

## 📊 Resultados Comparativos

### Tabla de Resultados

| Estrategia | Calidad | Latencia | Costo | Recall | Fidelidad | Uso Ideal |
|-----------|---------|----------|-------|--------|-----------|-----------|
| **Graph RAG** | 0.654 🏆 | 18.6s ⚠️ | Alto | 0.33 | 0.958 ✅ | Investigación offline |
| **Agentic RAG** | 0.600 | 8.5s | Medio | 0.25 | 1.0 ✅ | Tareas multi-paso |
| **Advanced RAG** | 0.500 | 5.2s | $0.017 💰 | 0.25 | 1.0 ✅ | Necesita optimización |
| **Naive RAG** | 0.421 ❌ | 1.4s ⚡ | Bajo | 0.08 ❌ | 0.85 | Prototipos |
| **No RAG** | 0.300 | 0.8s | Muy bajo | 0.0 | 0.5 | Baseline |

### Análisis de Bottlenecks

#### 🔴 **Problema Principal: RETRIEVAL**
Todas las estrategias sufren de **bajo Contextual Recall** (0.08 - 0.33):
- **Significado**: El sistema pierde 67-92% de información relevante
- **Causa Raíz**: 
  - Dataset pequeño (~50 recetas)
  - Embeddings genéricos (no fine-tuned para dominio culinario)
  - Consultas complejas que requieren razonamiento multi-hop

#### 🟢 **Fortaleza: GENERATION**
Los LLMs están funcionando perfectamente:
- **Agentic & Advanced**: Fidelidad 1.0 (no alucinan)
- **Conclusión**: El cuello de botella NO es la generación

---

## 💰 Análisis de Costos

### Desglose por Estrategia

```python
# Costos estimados por 1000 queries
{
    "naive_rag": "$2.50",
    "advanced_rag": "$17.00",  # ⚠️ Más caro
    "agentic_rag": "$8.50",
    "graph_rag": "$12.00"  # Estimado (usa herramientas externas)
}
```

### Optimizaciones de Costo Implementadas

1. **Modelo de Expansión**: `gemini-2.5-flash` (barato) para query expansion
2. **Modelo de Generación**: `DEFAULT_MODEL` configurable
3. **Caching**: Embeddings cacheados en ChromaDB
4. **Batch Processing**: Múltiples queries en paralelo

---

## 🔮 Mejoras Futuras

### 🚑 Prioridad 1: Arreglar Retrieval (URGENTE)

#### Opción A: Cambiar Modelo de Embeddings
```python
# Actual
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Propuesto
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
# O fine-tuning específico para recetas
```

#### Opción B: Aumentar Dataset
- Agregar 500+ recetas veganas
- Incluir más variaciones de ingredientes
- Enriquecer metadatos nutricionales

#### Opción C: Hybrid Search
```python
# Combinar búsqueda vectorial + keyword search
results_vector = chroma.query(query, n_results=20)
results_bm25 = bm25_index.search(query, k=20)
results_final = reciprocal_rank_fusion([results_vector, results_bm25])
```

### 🧹 Prioridad 2: Limpieza de Contexto

#### Mejorar Re-Ranker
```python
# Actual: Cross-encoder genérico
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# Propuesto: Fine-tuned para recetas
reranker = CrossEncoder('custom-recipe-reranker')
# Entrenar con pares (query, receta_relevante)
```

#### Filtrado de Ruido en Agentic RAG
```python
def _filter_observations(self, observations):
    """Elimina observaciones redundantes o irrelevantes"""
    unique = deduplicate_by_semantic_similarity(observations)
    relevant = [obs for obs in unique if relevance_score(obs) > 0.7]
    return relevant[:5]  # Top 5
```

### ⚡ Prioridad 3: Optimización de Graph RAG

#### Pre-Cálculo de Grafos
```python
# Cachear subgrafos frecuentes
frequent_patterns = [
    "recetas_con_ingrediente",
    "recetas_bajo_calorias",
    "recetas_alto_proteina"
]

for pattern in frequent_patterns:
    subgraph = extract_subgraph(pattern)
    cache.set(pattern, subgraph)
```

#### Paralelización de Queries
```python
import asyncio

async def parallel_graph_retrieval(queries):
    tasks = [graph_retriever.query_async(q) for q in queries]
    results = await asyncio.gather(*tasks)
    return merge_results(results)
```

---

## 🛠️ Tecnologías Utilizadas

### Core Framework
- **Python**: 3.10+
- **LangChain**: Abstracciones RAG
- **LangGraph**: Orquestación de agentes

### Vector Database
- **ChromaDB**: Almacenamiento de embeddings
- **Persistencia**: Local en `data/chroma_db/`

### Graph Database
- **Neo4j**: Knowledge Graph
- **LlamaIndex**: Integración con Neo4j

### LLMs
- **OpenAI**: GPT-4o-mini (evaluación)
- **Google Gemini**: gemini-2.5-flash (query expansion), gemini-2.5-pro (graph construction)

### Evaluación
- **DeepEval**: Framework LLM-as-a-Judge
- **Métricas**: Precision, Recall, Relevancy, Faithfulness

### Utilities
- **Pandas**: Procesamiento de datos
- **Pydantic**: Validación de schemas
- **python-dotenv**: Gestión de variables de entorno

---

## 📁 Estructura del Proyecto

```
rag_practice_project/
├── data/
│   ├── raw/
│   │   └── vegan_recipes.csv
│   ├── processed/
│   │   └── vegan_recipes_processed.parquet
│   └── chroma_db/                    # Vector DB persistente
├── src/
│   ├── data/
│   │   └── load_dataset.py           # Carga y preprocesamiento
│   ├── vector_db/
│   │   ├── chroma_manager.py         # Wrapper ChromaDB
│   │   └── setup_chroma.py           # Inicialización
│   ├── graph_db/
│   │   ├── neo4j_manager.py          # Conexión Neo4j
│   │   ├── graph_builder.py          # Construcción del grafo
│   │   └── graph_retriever.py        # Queries Cypher
│   ├── rag_strategies/
│   │   ├── base_strategy.py          # Clase abstracta
│   │   ├── no_rag.py
│   │   ├── naive_rag.py
│   │   ├── advanced_rag.py
│   │   ├── agentic_rag.py
│   │   └── graph_rag.py
│   ├── evaluation/
│   │   ├── evaluator.py              # DeepEval integration
│   │   └── analyzer.py               # Análisis de resultados
│   └── utils/
│       └── config_loader.py
├── config/
│   └── config.py                     # Configuración global
├── results/                          # Resultados de experimentos
│   └── experiment_results_*.json
├── run_all_experiments.py            # Script principal
├── setup_graph.py                    # Construcción del grafo
├── requirements.txt
└── README.md
```

---

## 🚀 Instalación y Uso

### 1. Instalación

```bash
# Clonar repositorio
cd rag_practice_project

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cat > .env << EOF
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
EOF
```

### 2. Preparar Datos

```bash
# Cargar dataset
python src/data/load_dataset.py

# Crear vector database
python src/vector_db/setup_chroma.py

# Construir knowledge graph (opcional, solo para Graph RAG)
python setup_graph.py
```

### 3. Ejecutar Experimentos

```bash
# Correr todas las estrategias
python run_all_experiments.py

# Resultados en: results/experiment_results_YYYYMMDD_HHMMSS.json
```

### 4. Analizar Resultados

```bash
# Generar visualizaciones y resumen
python src/evaluation/analyzer.py
```

---

## 📝 Conclusiones

### Hallazgos Clave

1. **Graph RAG es el ganador en calidad** (0.654) pero requiere optimización de latencia
2. **El bottleneck está en el retrieval**, no en la generación
3. **Advanced RAG tiene bajo ROI** - necesita mejor re-ranker
4. **Agentic RAG tiene fidelidad perfecta** pero trae ruido contextual

### Recomendaciones

- **Para producción**: Usar Naive RAG optimizado (mejor latencia/costo)
- **Para investigación**: Graph RAG con pre-cálculo de subgrafos
- **Para tareas complejas**: Agentic RAG con filtrado mejorado

### Lecciones Aprendidas

1. **Dataset pequeño limita todas las estrategias** - invertir en datos de calidad
2. **Embeddings genéricos no capturan semántica de dominio** - considerar fine-tuning
3. **LLM-as-a-Judge (DeepEval) es confiable** para evaluación objetiva
4. **Trade-off calidad/latencia es inevitable** - elegir según caso de uso

---

**Proyecto realizado como práctica de arquitecturas RAG avanzadas.**  
**Fecha**: Enero 2026  
**Duración**: 3 meses
