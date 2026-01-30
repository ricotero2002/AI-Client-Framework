"""
Graph RAG - Estrategia RAG mejorada usando Knowledge Graph

Combina:
- Query expansion con gemini-2.5-flash  
- Graph retrieval con routing inteligente (CYPHER/VECTOR/HYBRID)
- Response generation con DEFAULT_MODEL
- Knowledge Graph traversal para contexto enriquecido
"""
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from pathlib import Path
import sys
import time

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.rag_strategies.base_strategy import BaseRAGStrategy
from src.utils.llm_client import get_llm_client
from src.graph_db.graph_retriever import GraphRetriever
from src.graph_db.neo4j_manager import Neo4jManager
from src.graph_db.graph_builder import GraphBuilder
from rag_config.config import (
    EXPANSION_MODEL,
    EXPANSION_LLM_PROVIDER,
    DEFAULT_MODEL,
    DEFAULT_LLM_PROVIDER,
    GRAPH_RETRIEVAL_TOP_K
)


class GraphRAGStrategy(BaseRAGStrategy):
    """
    Graph RAG con routing inteligente y expansión de queries
    
    Pipeline:
    1. Query Analysis: Decide retrieve() vs query()
    2. Query Expansion: Expande con términos del grafo
    3. Graph Retrieval: Obtiene nodos/relaciones
    4. Response Generation: Genera respuesta contextual
    """
    
    def __init__(
        self, 
        top_k: int = GRAPH_RETRIEVAL_TOP_K,
        graph_index=None,
        graph_retriever=None
    ):
        super().__init__("Graph RAG")
        
        # LLM clients
        self.expansion_client = get_llm_client(
            provider=EXPANSION_LLM_PROVIDER,
            model=EXPANSION_MODEL
        )
        self.response_client = get_llm_client(
            provider=DEFAULT_LLM_PROVIDER,
            model=DEFAULT_MODEL
        )
        
        # Graph components
        self.top_k = top_k
        self.graph_retriever = graph_retriever
        self.graph_index = graph_index
        
        # Lazy loading indicator
        self._initialized = graph_retriever is not None
        
        print(f"✓ Graph RAG Strategy initialized (expansion: {EXPANSION_MODEL}, response: {DEFAULT_MODEL})")
    
    def _ensure_graph_loaded(self):
        """Lazy loading del grafo si es necesario"""
        if not self._initialized:
            print("⚠️  Graph RAG requires a pre-loaded Knowledge Graph")
            print("   Please run setup_graph.py first or pass graph_retriever to constructor")
            raise RuntimeError("Knowledge Graph not loaded. Run setup_graph.py first.")
    
    def generate_response(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Genera respuesta usando Graph RAG
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Dict con respuesta y métricas
        """
        self._ensure_graph_loaded()
        
        # 1. QUERY EXPANSION: Expandir query para mejor retrieval
        expansion_start = time.time()
        expanded_query = self._expand_query(query)
        expansion_time = (time.time() - expansion_start) * 1000
        
        # 2. RETRIEVE: Obtener contextos del grafo con routing inteligente
        retrieve_start = time.time()
        
        print(f"\n[Graph RAG]")
        print(f"  Original query: {query}")
        print(f"  Expanded query: {expanded_query}")
        
        try:
            # Usar retrieve() del graph_retriever (con routing CYPHER/VECTOR/HYBRID)
            retrieval_result = self.graph_retriever.retrieve(expanded_query)
            
            # Extraer información (nuevo formato: 'cypher' en vez de 'generated_cypher')
            contexts = retrieval_result.get("contexts", [])
            routing_strategy = retrieval_result.get("strategy", "UNKNOWN")
            cypher_query = retrieval_result.get("cypher", None)  # Cambio aquí
            
            print(f"  Retrieved: {len(contexts)} contexts")
            print(f"  Routing: {routing_strategy}")
            if cypher_query:
                print(f"  Cypher: {cypher_query[:100]}...")
            
            # Formatear contexto
            context = "\n\n".join([f"Context {i+1}:\n{ctx}" for i, ctx in enumerate(contexts)])
            
        except Exception as e:
            print(f"  ⚠️  Error en retrieval: {e}")
            import traceback
            traceback.print_exc()
            context = f"Error recuperando del grafo: {str(e)}"
            contexts = []
            routing_strategy = "ERROR"
            cypher_query = None
        
        retrieve_time = (time.time() - retrieve_start) * 1000
        
        # 3. GENERATE: Generar respuesta final con el contexto
        system_prompt = """Eres un asistente experto en nutrición y cocina vegana/vegetariana.
Debes responder basándote EXCLUSIVAMENTE en la información del Knowledge Graph proporcionado.

REGLAS:
1. IDIOMA: Responde siempre en español
2. ESTILO: Tono profesional, usa Markdown para mejor legibilidad
3. DATOS: Si mencionas propiedades nutricionales, incluye los valores numéricos
4. PRIORIDAD: Los contextos están ordenados por relevancia
5. HONESTIDAD: Si no hay información relevante en el grafo, indícalo claramente, nunca inventes recetas que no tengas.
6. Si conseguis respuestas con menos ingredientes o que no convinen todos menciona las alternativas.
7. No menciones el grafo en la respuesta, a lo sumo indica que no tenes conocimiento de ciertos ingredientes.

FORMATO DE RESPUESTA:
- Enumera recetas/información en orden de relevancia
- Usa contexto del grafo (ingredientes, relaciones, propiedades)
- Sé conciso y directo
"""
        
        prompt = f"""Basándote en el siguiente contexto del Knowledge Graph:

CONTEXTO:
{context}

PREGUNTA:
{query}

Responde la pregunta usando únicamente la información del grafo."""
        
        response_data, generation_time = self._measure_latency(
            self.response_client.generate,
            prompt=prompt,
            system_prompt=system_prompt
        )
        
        response_text = response_data.get("response", "")
        input_tokens = response_data.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = response_data.get("usage", {}).get("completion_tokens", 0)
        
        # Calcular latencia total
        total_latency = expansion_time + retrieve_time + generation_time
        
        # Registrar métricas
        self._track_metrics(total_latency, input_tokens, output_tokens)
        
        return {
            "strategy": self.name,
            "query": query,
            "expanded_query": expanded_query,
            "response": response_text,
            "context": context,
            "retrieval_method": f"retrieve_{routing_strategy.lower()}",
            "routing_strategy": routing_strategy,
            "cypher_query": cypher_query,
            "latency_ms": total_latency,
            "expansion_latency_ms": expansion_time,
            "retrieve_latency_ms": retrieve_time,
            "generation_latency_ms": generation_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": DEFAULT_MODEL,
            "provider": DEFAULT_LLM_PROVIDER,
            "expansion_model": EXPANSION_MODEL,
            # Extra info para análisis
            "extra_info": {
                "num_contexts_retrieved": len(contexts),
                "contexts": contexts[:5],  # Solo primeros 5 para no sobrecargar
                "query_expansion": {
                    "original_query": query,
                    "expanded_query": expanded_query,
                    "expansion_model": EXPANSION_MODEL
                },
                "retrieval_info": {
                    "routing_strategy": routing_strategy,
                    "cypher_query": cypher_query,
                    "num_contexts": len(contexts),
                    "contexts_preview": [ctx[:200] for ctx in contexts[:3]]
                },
                "latency_breakdown": {
                    "expansion_ms": expansion_time,
                    "retrieve_ms": retrieve_time,
                    "generation_ms": generation_time,
                    "total_ms": total_latency,
                    "expansion_percentage": (expansion_time / total_latency * 100) if total_latency > 0 else 0,
                    "retrieve_percentage": (retrieve_time / total_latency * 100) if total_latency > 0 else 0,
                    "generation_percentage": (generation_time / total_latency * 100) if total_latency > 0 else 0
                }
            }
        }
    
    def _expand_query(self, query: str) -> str:
        """
        Expande la query con términos relevantes para mejorar el retrieval
        
        Args:
            query: Query del usuario
            
        Returns:
            Query expandida
        """
        system_prompt = """Eres un experto en expandir queries de búsqueda para Knowledge Graphs de recetas veganas/vegetarianas.

Tu tarea es expandir la query del usuario con términos relevantes EN INGLÉS (el grafo está en inglés).

REGLAS:
1. Mantén la intención original de la query
2. Agrega sinónimos y términos relacionados
3. Incluye variaciones de nombres de ingredientes
4. Responde SOLO con la query expandida, sin explicaciones

EJEMPLOS:
- "sopas" → "soup broth stew vegetable soup"
- "proteína alta" → "high protein protein-rich protein content"
- "quinoa" → "quinoa grain quinoa seeds quinoa recipe"
- "desayuno rápido" → "quick breakfast fast breakfast morning meal"
"""
        
        expansion_prompt = f'Expande esta query: "{query}"'
        
        response = self.expansion_client.generate(
            prompt=expansion_prompt,
            system_prompt=system_prompt,
            temperature=0.2
        )
        
        expanded = response["response"].strip()
        return expanded
    
    def _format_graph_context(self, nodes: List) -> str:
        """
        Formatea nodos del grafo en contexto legible
        
        Args:
            nodes: Lista de NodeWithScore
            
        Returns:
            Contexto formateado
        """
        if not nodes:
            return "No se encontraron nodos relevantes en el grafo."
        
        context_parts = []
        for i, node in enumerate(nodes, 1):
            metadata = node.node.metadata
            text = node.node.text
            score = node.score if hasattr(node, 'score') else 0.0
            
            context_parts.append(
                f"Nodo {i} (Relevancia: {score:.3f}):\n"
                f"Contenido: {text}\n"
                f"Metadata: {metadata}\n"
            )
        
        return "\n".join(context_parts)


# Helper function para cargar el grafo
def load_graph_for_experiments():
    """
    Carga el Knowledge Graph para experimentos
    
    Returns:
        tuple: (graph_index, graph_retriever)
    """
    print("\n[Graph RAG] Cargando Knowledge Graph...")
    
    # Conectar a Neo4j y cargar el grafo construido
    neo4j_manager = Neo4jManager()
    
    # Verificar que existe
    stats = neo4j_manager.get_statistics()
    if stats["node_count"] == 0:
        raise RuntimeError(
            "No hay Knowledge Graph construido. Ejecuta setup_graph.py primero."
        )
    
    print(f"✓ Grafo cargado: {stats['node_count']} nodos, {stats['relationship_count']} relaciones")
    
    # Reconstruir el índice
    builder = GraphBuilder(neo4j_manager=neo4j_manager)
    # Aquí necesitaríamos cargar el índice desde Neo4j
    # Por simplicidad, asumimos que está construido
    
    print("⚠️  Nota: GraphRAGStrategy requiere que el grafo esté pre-construido")
    print("   Ejecuta setup_graph.py antes de usar esta estrategia")
    
    return None, None


if __name__ == "__main__":
    print("Graph RAG Strategy module loaded")
    print("Use with run_all_experiments.py or import directly")
