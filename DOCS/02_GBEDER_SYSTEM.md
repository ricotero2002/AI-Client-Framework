# GBeder Multi-Agent Research System

## 📋 Resumen Ejecutivo

Sistema multi-agente autónomo construido con **LangGraph** que transforma consultas de investigación en reportes completos y verificados. Implementa **3 patrones de orquestación** diferentes (Supervisor, Sequential, Reflexion) con integración **MCP nativa** para búsqueda web vía Tavily.

**Resultado Principal**: El patrón **Reflexion** domina en todas las métricas - 3.9× más rápido y 3.9× más barato que Supervisor, con la mejor calidad (0.820).

---

## 🎯 Objetivos del Proyecto

1. **Implementar 3 patrones de orquestación** multi-agente
2. **Integración MCP** para desacoplar APIs de lógica de agentes
3. **Evaluación con DeepEval** (LLM-as-a-Judge)
4. **Tracking completo** de costos, tokens y uso de Tavily
5. **Benchmarking automatizado** con análisis agregado

---

## 🏗️ Arquitectura del Sistema

### Pipeline Cognitivo (4 Agentes)

```
┌─────────────────────────────────────────────────────────────┐
│                      USER QUERY                             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │    Orchestration Pattern        │
        │  (Supervisor/Sequential/        │
        │   Reflexion)                    │
        └────────────────┬────────────────┘
                         │
      ┌──────────────────┼──────────────────┐
      │                  │                  │
      ▼                  ▼                  ▼
┌──────────┐      ┌──────────┐      ┌──────────┐
│Researcher│      │ Analyst  │      │Synthesizer│
│(Hunter)  │─────▶│ (Filter) │─────▶│(Architect)│
└──────────┘      └──────────┘      └──────────┘
      │                                    │
      │ Tavily MCP                         │
      │ tavily_search                      │
      │ tavily_extract                     │
      │                                    ▼
      │                             ┌──────────┐
      │                             │ Reviewer │
      │                             │ (Critic) │
      │                             └──────────┘
      │                                    │
      └────────────────────────────────────┘
                         │
                         ▼
                  FINAL REPORT
        (with DeepEval quality scores)
```

### Agentes Especializados

| Agente | Modelo | Rol | Herramientas |
|--------|--------|-----|--------------|
| **Researcher** | gemini-2.5-flash | Búsqueda de información web | Tavily MCP (search, extract) |
| **Analyst** | gemini-2.0-flash | Procesamiento y análisis de datos | Python REPL |
| **Synthesizer** | gemini-2.5-flash-lite | Redacción de reportes | Ninguna (context-only) |
| **Reviewer** | gemini-2.0-flash-lite | Control de calidad | DeepEval metrics |

**Principio de Diseño**: Ningún modelo se repite en una ejecución para optimizar costo/calidad.

---

## 🔍 Integración MCP (Model Context Protocol)

### ¿Por Qué MCP?

MCP desacopla las APIs externas de la lógica de agentes:

- **Portabilidad**: Cambiar Tavily por Google Search sin tocar código de agentes
- **Seguridad**: API keys centralizadas en el servidor MCP
- **Observabilidad**: Todas las llamadas trazadas en LangSmith
- **Versionado**: Actualizar API sin romper agentes

### Servidor MCP Tavily

**Archivo**: `gbeder_system/tavily_mcp_server.py`

```python
from fastmcp import FastMCP
from tavily import TavilyClient
import os

mcp = FastMCP("Tavily Research Server")
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@mcp.tool()
def tavily_search(
    query: str,
    search_depth: str = "advanced",
    max_results: int = 5,
    include_answer: bool = True,
    include_images: bool = False
) -> dict:
    """
    Busca información en la web usando Tavily.
    
    Args:
        query: Consulta de búsqueda
        search_depth: basic/advanced/fast
        max_results: Número de resultados (1-10)
        include_answer: Incluir respuesta directa
        include_images: Incluir imágenes
    
    Returns:
        {
            "results": [{"url": str, "title": str, "content": str, "score": float}],
            "answer": str (si include_answer=True)
        }
    """
    response = tavily.search(
        query=query,
        search_depth=search_depth,
        max_results=max_results,
        include_answer=include_answer,
        include_images=include_images
    )
    return response

@mcp.tool()
def tavily_extract(
    urls: list[str],
    extract_depth: str = "full",
    format: str = "markdown"
) -> dict:
    """
    Extrae contenido completo de URLs.
    
    Args:
        urls: Lista de URLs a extraer
        extract_depth: basic/full
        format: markdown/text
    
    Returns:
        {"extractions": [{"url": str, "content": str}]}
    """
    response = tavily.extract(urls=urls)
    return response

if __name__ == "__main__":
    mcp.run()
```

### Cliente MCP

**Archivo**: `gbeder_system/mcp_client.py`

```python
import asyncio
import subprocess
import json
from typing import Dict, Any

class MCPClient:
    def __init__(self, server_script_path: str):
        self.server_script = server_script_path
        self.process = None
        self.reader = None
        self.writer = None
    
    async def connect(self):
        """Inicia el servidor MCP como subproceso"""
        self.process = await asyncio.create_subprocess_exec(
            "python", self.server_script,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.reader = self.process.stdout
        self.writer = self.process.stdin
        
        # Handshake inicial
        await self._send_message({"jsonrpc": "2.0", "method": "initialize"})
        response = await self._receive_message()
        print(f"MCP Server initialized: {response}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Llama a una herramienta del servidor MCP"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 1
        }
        
        await self._send_message(request)
        response = await self._receive_message()
        
        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")
        
        return response.get("result", {})
    
    async def disconnect(self):
        """Cierra la conexión MCP"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        if self.process:
            self.process.terminate()
            await self.process.wait()
    
    async def _send_message(self, message: Dict):
        """Envía mensaje JSON-RPC al servidor"""
        data = json.dumps(message).encode() + b"\n"
        self.writer.write(data)
        await self.writer.drain()
    
    async def _receive_message(self) -> Dict:
        """Recibe mensaje JSON-RPC del servidor"""
        line = await self.reader.readline()
        return json.loads(line.decode())
```

### Uso en Agentes

```python
# En ResearcherAgent
class ResearcherAgent:
    def __init__(self, mcp_client: MCPClient):
        self.mcp = mcp_client
    
    async def execute(self, state: GBederState):
        # Refinar query con LLM
        refined_queries = self._refine_search_query(state["query"])
        
        # Buscar con Tavily vía MCP
        all_sources = []
        for query in refined_queries:
            result = await self.mcp.call_tool("tavily_search", {
                "query": query,
                "search_depth": "advanced",
                "max_results": 5
            })
            all_sources.extend(result["results"])
        
        # Actualizar estado
        state["retrieved_context"] = all_sources
        state["tavily_api_calls"] += len(refined_queries)
        return state
```

---

## 🧠 Patrones de Orquestación

### Patrón A: Sequential con Feedback

**Archivo**: `gbeder_system/graphs/sequential_pattern.py`

**Topología**:
```
Researcher → Analyst → Synthesizer → Reviewer
                ▲                        │
                │                        │
                └────── (if needed) ─────┘
```

**Implementación LangGraph**:

```python
from langgraph.graph import StateGraph, END

def create_sequential_graph(mcp_client):
    workflow = StateGraph(GBederState)
    
    # Crear agentes
    researcher = ResearcherAgent(mcp_client)
    analyst = AnalystAgent()
    synthesizer = SynthesizerAgent()
    reviewer = ReviewerAgent()
    
    # Definir nodos
    workflow.add_node("researcher", researcher.execute)
    workflow.add_node("analyst", analyst.execute)
    workflow.add_node("synthesizer", synthesizer.execute)
    workflow.add_node("reviewer", reviewer.execute)
    
    # Definir flujo
    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "analyst")
    workflow.add_edge("analyst", "synthesizer")
    workflow.add_edge("synthesizer", "reviewer")
    
    # Lógica de feedback
    def should_continue(state):
        if state["is_complete"]:
            return END
        elif state["needs_more_data"]:
            return "researcher"  # Volver a buscar
        elif state["iteration_count"] < 5:
            return "synthesizer"  # Re-escribir
        else:
            return END  # Max iterations
    
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            END: END,
            "researcher": "researcher",
            "synthesizer": "synthesizer"
        }
    )
    
    return workflow.compile()
```

**Características**:
- ✅ Determinista y fácil de debuggear
- ✅ Costo predecible
- ⚠️ "Telephone effect" - degradación de contexto
- ⚠️ Sin comunicación cross-agent

**Resultados** (promedio 6 runs):
- Latencia: 44.76s
- Costo: $0.0026
- Calidad: 0.804
- Tavily Searches: 2.0

---

### Patrón B: Supervisor (Hierarchical)

**Archivo**: `gbeder_system/graphs/supervisor_pattern.py`

**Topología**:
```
       ┌──────────────┐
       │  Supervisor  │ ──> Toma decisiones de routing
       └──────┬───────┘
              │
    ┌─────────┼──────────┬──────────┐
    ▼         ▼          ▼          ▼
Researcher  Analyst  Synthesizer  Reviewer
    │         │          │          │
    └─────────┴──────────┴──────────┘
              │
              ▼
           [END]
```

**Implementación**:

```python
from pydantic import BaseModel

class SupervisorDecision(BaseModel):
    next_agent: str  # "researcher" | "analyst" | "synthesizer" | "reviewer" | "FINISH"
    reasoning: str
    progress_assessment: float  # 0.0-1.0

def create_supervisor_graph(mcp_client):
    workflow = StateGraph(GBederState)
    
    # Agentes workers
    agents = {
        "researcher": ResearcherAgent(mcp_client),
        "analyst": AnalystAgent(),
        "synthesizer": SynthesizerAgent(),
        "reviewer": ReviewerAgent()
    }
    
    # Nodo Supervisor
    def supervisor_node(state: GBederState):
        """Supervisor decide qué agente ejecutar siguiente"""
        prompt = Prompt()
        prompt.set_system("""Eres un supervisor de investigación.
        Analiza el estado actual y decide qué agente debe actuar siguiente.
        
        Agentes disponibles:
        - researcher: Busca información en la web
        - analyst: Analiza y procesa datos
        - synthesizer: Redacta el reporte
        - reviewer: Evalúa calidad
        - FINISH: Terminar si el trabajo está completo
        
        Considera:
        - Progreso actual (0.0-1.0)
        - Gaps de información
        - Calidad del draft
        """)
        
        prompt.set_user_input(f"""
        Query: {state['query']}
        Contexto recuperado: {len(state.get('retrieved_context', []))} fuentes
        Análisis: {'Sí' if state.get('analysis') else 'No'}
        Draft: {'Sí' if state.get('draft') else 'No'}
        Scores: {state.get('scores', {})}
        Iteración: {state.get('iteration_count', 0)}/10
        """)
        
        prompt.set_output_schema(SupervisorDecision)
        
        response, _ = supervisor_client.get_response(prompt)
        decision = parse_json(response)
        
        print(f"📋 SUPERVISOR: {decision.next_agent} (Progress: {decision.progress_assessment:.1%})")
        print(f"   Reasoning: {decision.reasoning}")
        
        state["current_agent"] = decision.next_agent
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        return state
    
    # Agregar nodos
    workflow.add_node("supervisor", supervisor_node)
    for name, agent in agents.items():
        workflow.add_node(name, agent.execute)
    
    # Routing dinámico
    def route_to_agent(state):
        next_agent = state["current_agent"]
        if next_agent == "FINISH" or state["iteration_count"] >= 10:
            return END
        return next_agent
    
    workflow.set_entry_point("supervisor")
    
    # Cada agente vuelve al supervisor
    for agent_name in agents.keys():
        workflow.add_edge(agent_name, "supervisor")
    
    # Supervisor decide siguiente paso
    workflow.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {**{name: name for name in agents.keys()}, END: END}
    )
    
    return workflow.compile()
```

**Características**:
- ✅ Adaptativo - workflows no lineales
- ✅ Flexible para queries complejas
- ⚠️ Supervisor es bottleneck (cada decisión = LLM call)
- ❌ Alto costo - 6× más tokens que Reflexion

**Resultados**:
- Latencia: 153.28s (⚠️ 3.9× más lento)
- Costo: $0.0098 (⚠️ 3.9× más caro)
- Calidad: 0.818
- Iteraciones: 12.0 (siempre llega al máximo)

**⚠️ Issue Conocido**: Supervisor consistentemente llega a max iterations, sugiriendo ineficiencia en lógica de routing.

---

### Patrón C: Reflexion (Critic-Reviewer Loop)

**Archivo**: `gbeder_system/graphs/reflexion_pattern.py`

**Topología**:
```
Researcher → Analyst → ┌──────────────┐
                       │              ▼
                       │    Synthesizer ↔ Critic
                       │              │
                       └──────────────┘
                                      │
                                      ▼
                                   [END]
```

**Implementación**:

```python
def create_reflexion_graph(mcp_client):
    workflow = StateGraph(GBederState)
    
    researcher = ResearcherAgent(mcp_client)
    analyst = AnalystAgent()
    synthesizer = SynthesizerAgent()
    reviewer = ReviewerAgent()
    
    # Fase 1: Research (una sola vez)
    workflow.add_node("researcher", researcher.execute)
    
    # Fase 2: Analysis (una sola vez)
    workflow.add_node("analyst", analyst.execute)
    
    # Fase 3: Refinement Loop
    workflow.add_node("synthesizer", synthesizer.execute)
    workflow.add_node("critic", reviewer.execute)
    
    # Flujo
    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "analyst")
    workflow.add_edge("analyst", "synthesizer")
    workflow.add_edge("synthesizer", "critic")
    
    # Loop de refinamiento
    def should_refine(state):
        """Decide si refinar o terminar"""
        if state.get("is_complete", False):
            return END
        elif state.get("iteration_count", 0) >= 5:
            return END  # Max refinement cycles
        else:
            return "synthesizer"  # Refinar draft
    
    workflow.add_conditional_edges(
        "critic",
        should_refine,
        {
            END: END,
            "synthesizer": "synthesizer"
        }
    )
    
    return workflow.compile()
```

**Características**:
- ✅ Máxima calidad (0.820)
- ✅ Más rápido (39.34s)
- ✅ Más barato ($0.0025)
- ✅ Consistente (baja varianza)
- ⚠️ No puede pedir más datos mid-loop

**Resultados**:
- **⚡ Fastest**: 39.34s
- **💰 Cheapest**: $0.0025
- **⭐ Highest Quality**: 0.820
- **🔋 Most Token-Efficient**: 12,609 tokens
- Tavily Searches: 2.0
- Iterations: 1.0

**🏆 Ganador**: Reflexion domina en TODAS las dimensiones medidas.

---

## 📊 Benchmarking y Análisis

### Sistema de Benchmarking

**Archivo**: `gbeder_system/results/run_comparison.py`

```python
import asyncio
from datetime import datetime
from gbeder_system.graphs import (
    create_supervisor_graph,
    create_sequential_graph,
    create_reflexion_graph
)
from gbeder_system.mcp_client import MCPClient

async def run_benchmark(query: str):
    """Ejecuta los 3 patrones y compara resultados"""
    
    patterns = [
        ("supervisor", create_supervisor_graph),
        ("sequential", create_sequential_graph),
        ("reflexion", create_reflexion_graph)
    ]
    
    results = {}
    
    for pattern_name, graph_factory in patterns:
        print(f"\n{'='*60}")
        print(f"Running: {pattern_name.upper()}")
        print(f"{'='*60}")
        
        # Conectar MCP
        mcp_client = MCPClient("gbeder_system/tavily_mcp_server.py")
        await mcp_client.connect()
        
        # Crear grafo
        graph = graph_factory(mcp_client)
        
        # Estado inicial
        initial_state = {
            "query": query,
            "messages": [],
            "retrieved_context": [],
            "analysis": "",
            "draft": "",
            "feedback": "",
            "scores": {},
            "iteration_count": 0,
            "pattern_name": pattern_name,
            "current_agent": "",
            "total_tokens": {},
            "input_tokens": {},
            "output_tokens": {},
            "total_cost": 0.0,
            "is_complete": False,
            "needs_more_data": False,
            "tavily_api_calls": 0,
            "tavily_total_searches": 0
        }
        
        # Ejecutar
        start_time = datetime.now()
        final_state = await graph.ainvoke(
            initial_state,
            {"configurable": {"thread_id": f"{pattern_name}_{datetime.now().timestamp()}"}}
        )
        end_time = datetime.now()
        
        # Calcular métricas
        latency = (end_time - start_time).total_seconds()
        
        results[pattern_name] = {
            "latency_seconds": latency,
            "total_cost": final_state["total_cost"],
            "total_tokens": sum(final_state["total_tokens"].values()),
            "tavily_searches": final_state["tavily_total_searches"],
            "quality_score": final_state.get("scores", {}).get("overall", 0.0),
            "iterations": final_state["iteration_count"],
            "draft": final_state["draft"]
        }
        
        await mcp_client.disconnect()
    
    # Guardar resultados
    save_benchmark_results(query, results)
    
    return results

# Ejecutar
if __name__ == "__main__":
    query = "Explain the latest developments in sustainable energy technology"
    asyncio.run(run_benchmark(query))
```

### Análisis Agregado

**Archivo**: `gbeder_system/analyze_benchmarks.py`

```python
import json
from pathlib import Path
from collections import defaultdict
import statistics

def analyze_benchmarks(results_dir: Path):
    """Analiza múltiples runs de benchmarks"""
    
    # Cargar todos los JSONs
    all_results = []
    for file in results_dir.glob("benchmark_*.json"):
        with open(file) as f:
            all_results.append(json.load(f))
    
    # Agregar por patrón
    pattern_metrics = defaultdict(lambda: defaultdict(list))
    
    for result in all_results:
        for pattern_name, metrics in result["results"].items():
            for metric_name, value in metrics.items():
                if isinstance(value, (int, float)):
                    pattern_metrics[pattern_name][metric_name].append(value)
    
    # Calcular estadísticas
    print("="*80)
    print("BENCHMARK AGGREGATE ANALYSIS")
    print("="*80)
    print(f"\nAnalyzed: {len(all_results)} complete benchmark runs")
    
    for pattern_name in ["reflexion", "sequential", "supervisor"]:
        metrics = pattern_metrics[pattern_name]
        
        print(f"\n{pattern_name.upper()}")
        print("-"*40)
        
        for metric_name, values in metrics.items():
            avg = statistics.mean(values)
            median = statistics.median(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0
            
            print(f"  {metric_name}:")
            print(f"    Avg: {avg:.4f}")
            print(f"    Median: {median:.4f}")
            print(f"    StdDev: {stdev:.4f}")
    
    # Best performers
    print("\n" + "="*80)
    print("BEST PERFORMERS")
    print("="*80)
    
    best_latency = min(pattern_metrics.items(), 
                       key=lambda x: statistics.mean(x[1]["latency_seconds"]))
    print(f"⚡ Fastest: {best_latency[0]} ({statistics.mean(best_latency[1]['latency_seconds']):.2f}s)")
    
    best_cost = min(pattern_metrics.items(),
                    key=lambda x: statistics.mean(x[1]["total_cost"]))
    print(f"💰 Cheapest: {best_cost[0]} (${statistics.mean(best_cost[1]['total_cost']):.4f})")
    
    best_quality = max(pattern_metrics.items(),
                       key=lambda x: statistics.mean(x[1]["quality_score"]))
    print(f"⭐ Highest Quality: {best_quality[0]} ({statistics.mean(best_quality[1]['quality_score']):.3f})")

if __name__ == "__main__":
    analyze_benchmarks(Path("gbeder_system/results/output"))
```

### Resultados Agregados (6 Runs)

| Métrica | Reflexion | Sequential | Supervisor |
|---------|-----------|------------|------------|
| **Avg Latency** | **39.34s** ⚡ | 44.76s | 153.28s |
| **Avg Cost** | **$0.0025** 💰 | $0.0026 | $0.0098 |
| **Avg Tokens** | **12,609** 🔋 | 13,673 | 76,123 |
| **Avg Tavily** | **2.0** 🔍 | 2.0 | 3.0 |
| **Avg Quality** | **0.820** ⭐ | 0.804 | 0.818 |
| **Avg Iterations** | 1.0 | 0.0 | 12.0 |

### Proyección de Costos (1000 Queries)

| Pattern | Cost/Query | Cost/1000 | vs Reflexion |
|---------|------------|-----------|--------------|
| Reflexion | $0.0025 | $2.50 | 1.00× |
| Sequential | $0.0026 | $2.60 | 1.04× |
| Supervisor | $0.0098 | $9.80 | 3.92× ⚠️ |

---

## 💰 Sistema de Tracking de Costos

### Tracking a Nivel de Agente

```python
# En cada agente
class ResearcherAgent:
    def execute(self, state):
        # ... lógica del agente ...
        
        # Track tokens
        state["input_tokens"][self.model_name] = \
            state.get("input_tokens", {}).get(self.model_name, 0) + usage.prompt_tokens
        
        state["output_tokens"][self.model_name] = \
            state.get("output_tokens", {}).get(self.model_name, 0) + usage.completion_tokens
        
        state["total_tokens"][self.model_name] = \
            state.get("total_tokens", {}).get(self.model_name, 0) + usage.total_tokens
        
        return state
```

### Cálculo de Costos

```python
# config.py
GEMINI_PRICING = {
    "gemini-2.5-flash": {
        "input": 0.30,   # per 1M tokens
        "output": 2.50,
        "cached": 0.075
    },
    "gemini-2.5-flash-lite": {
        "input": 0.10,
        "output": 0.40,
        "cached": 0.025
    },
    "gemini-2.0-flash": {
        "input": 0.10,
        "output": 0.40,
        "cached": 0.025
    },
    "gemini-2.0-flash-lite": {
        "input": 0.075,
        "output": 0.30,
        "cached": 0.01875
    }
}

def calculate_total_cost(state):
    """Calcula costo total basado en tokens usados"""
    total_cost = 0.0
    
    for model, tokens in state["input_tokens"].items():
        pricing = GEMINI_PRICING[model]
        total_cost += (tokens / 1_000_000) * pricing["input"]
    
    for model, tokens in state["output_tokens"].items():
        pricing = GEMINI_PRICING[model]
        total_cost += (tokens / 1_000_000) * pricing["output"]
    
    return total_cost
```

### Tracking de Tavily

```python
# En ResearcherAgent
state["tavily_api_calls"] = state.get("tavily_api_calls", 0) + num_queries
state["tavily_total_searches"] = state.get("tavily_total_searches", 0) + num_queries
```

---

## 🛠️ Tecnologías Utilizadas

### Core Framework
- **LangGraph**: Orquestación multi-agente con state management
- **LangSmith**: Tracing y observabilidad
- **Pydantic**: Schemas estructurados para outputs

### LLMs
- **Google Gemini 2.x**: 4 modelos diferentes según complejidad
- **OpenAI GPT-4o-mini**: Evaluación con DeepEval (opcional)

### MCP Integration
- **FastMCP**: Framework para crear servidores MCP
- **Tavily API**: Búsqueda web y extracción de contenido

### Evaluación
- **DeepEval**: LLM-as-a-Judge metrics
- **Métricas**: Faithfulness, Answer Relevancy, Contextual Recall

### Utilities
- **asyncio**: Operaciones asíncronas
- **python-dotenv**: Variables de entorno

---

## 📁 Estructura del Proyecto

```
gbeder_system/
├── config.py                  # Modelos, prompts, thresholds
├── state.py                   # TypedDict schemas
├── agents.py                  # 4 agentes especializados
├── mcp_client.py              # Cliente MCP
├── tavily_mcp_server.py       # Servidor MCP Tavily
├── direct_tavily_client.py    # Cliente directo (fallback)
├── eval.py                    # DeepEval integration
├── schemas.py                 # Pydantic schemas
├── graphs/
│   ├── supervisor_pattern.py
│   ├── sequential_pattern.py
│   └── reflexion_pattern.py
├── results/
│   ├── benchmark.py
│   ├── run_comparison.py
│   └── output/
│       ├── benchmark_*.json
│       └── *_workflow_*.md
├── analyze_benchmarks.py
├── test_gbeder.py
└── README.md
```

---

## 🚀 Instalación y Uso

### 1. Instalación

```bash
cd gbeder_system

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
cat > .env << EOF
TAVILY_API_KEY=tvly-dev-...
GOOGLE_API_KEY=...
OPENAI_API_KEY=sk-...  # Opcional para DeepEval
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
EOF
```

### 2. Test Rápido

```bash
python test_gbeder.py
```

### 3. Benchmark Completo

```bash
cd results
python run_comparison.py --query "Your research question"
```

### 4. Análisis Agregado

```bash
python analyze_benchmarks.py --dir "results/output"
```

---

## 📝 Conclusiones

### Hallazgos Clave

1. **Reflexion domina en todas las métricas** - mejor opción para producción
2. **Supervisor tiene overhead excesivo** - 12 iteraciones promedio sugiere ineficiencia
3. **MCP desacopla exitosamente** APIs de lógica de agentes
4. **DeepEval provee evaluación objetiva** sin anotación humana

### Recomendaciones

- **Producción**: Usar Reflexion por defecto
- **Queries exploratorias**: Sequential con feedback
- **Investigación compleja**: Optimizar Supervisor (reducir overhead)

### Lecciones Aprendidas

1. **Especialización de modelos** reduce costos sin sacrificar calidad
2. **Iterative refinement** (Reflexion) supera routing dinámico (Supervisor)
3. **MCP es crucial** para sistemas multi-agente escalables
4. **Tracking granular** de costos permite optimización informada

---

**Proyecto realizado como práctica de sistemas multi-agente con LangGraph.**  
**Fecha**: Enero 2026  
**Duración**: 1 mes
