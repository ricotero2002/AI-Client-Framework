"""
Graph RAG - RAG basado en grafos de conocimiento
"""
from typing import Dict, Any, List, Set
from pathlib import Path
import sys
import time
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.rag_strategies.base_strategy import BaseRAGStrategy
from src.utils.llm_client import get_llm_client
from src.vector_db.chroma_manager import ChromaDBManager

class RecipeKnowledgeGraph:
    """
    Grafo de conocimiento simple para recetas
    """
    
    def __init__(self):
        self.nodes = {}  # id -> {type, data}
        self.edges = defaultdict(list)  # source_id -> [(relation, target_id)]
    
    def add_recipe_node(self, recipe_id: str, recipe_data: Dict):
        """Agrega nodo de receta"""
        self.nodes[recipe_id] = {
            "type": "recipe",
            "data": recipe_data
        }
    
    def add_ingredient_node(self, ingredient: str):
        """Agrega nodo de ingrediente"""
        ing_id = f"ing_{ingredient.lower().replace(' ', '_')}"
        if ing_id not in self.nodes:
            self.nodes[ing_id] = {
                "type": "ingredient",
                "data": {"name": ingredient}
            }
        return ing_id
    
    def add_edge(self, source_id: str, relation: str, target_id: str):
        """Agrega arista entre nodos"""
        self.edges[source_id].append((relation, target_id))
    
    def get_neighbors(self, node_id: str, relation: str = None) -> List[str]:
        """Obtiene vecinos de un nodo"""
        if node_id not in self.edges:
            return []
        
        neighbors = []
        for rel, target in self.edges[node_id]:
            if relation is None or rel == relation:
                neighbors.append(target)
        return neighbors
    
    def traverse(self, start_node: str, max_depth: int = 2) -> Set[str]:
        """Traversa el grafo desde un nodo"""
        visited = set()
        queue = [(start_node, 0)]
        
        while queue:
            node, depth = queue.pop(0)
            if node in visited or depth > max_depth:
                continue
            
            visited.add(node)
            
            # Agregar vecinos
            for rel, neighbor in self.edges.get(node, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        
        return visited

class GraphRAGStrategy(BaseRAGStrategy):
    """
    RAG basado en grafos de conocimiento
    Construye un grafo de recetas e ingredientes para navegación contextual
    """
    
    def __init__(self, top_k: int = 5):
        super().__init__("Graph RAG")
        self.llm_client = get_llm_client()
        self.vector_db = ChromaDBManager()
        self.top_k = top_k
        self.knowledge_graph = None
    
    def build_knowledge_graph(self, recipes_df):
        """
        Construye el grafo de conocimiento desde el dataset
        
        Args:
            recipes_df: DataFrame con recetas
        """
        print("Construyendo grafo de conocimiento...")
        self.knowledge_graph = RecipeKnowledgeGraph()
        
        for idx, row in recipes_df.iterrows():
            recipe_id = f"recipe_{idx}"
            
            # Agregar nodo de receta
            self.knowledge_graph.add_recipe_node(recipe_id, row.to_dict())
            
            # Extraer y agregar ingredientes (si existen)
            if 'ingredients' in row and row['ingredients']:
                ingredients = str(row['ingredients']).split(',')
                for ingredient in ingredients[:10]:  # Limitar a 10 ingredientes
                    ingredient = ingredient.strip()
                    if ingredient:
                        ing_id = self.knowledge_graph.add_ingredient_node(ingredient)
                        self.knowledge_graph.add_edge(recipe_id, "has_ingredient", ing_id)
                        self.knowledge_graph.add_edge(ing_id, "used_in", recipe_id)
        
        print(f"Grafo construido: {len(self.knowledge_graph.nodes)} nodos")
    
    def generate_response(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Genera respuesta usando Graph RAG
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Dict con respuesta y métricas
        """
        # 1. Recuperación inicial por similitud vectorial
        retrieve_start = time.time()
        results = self.vector_db.query(query, n_results=self.top_k)
        retrieve_time = (time.time() - retrieve_start) * 1000
        
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        # 2. Expansión por grafo (si está disponible)
        graph_time = 0
        expanded_docs = documents.copy()
        
        if self.knowledge_graph:
            graph_start = time.time()
            # Simular expansión por grafo
            # En producción, traversar el grafo para encontrar recetas relacionadas
            expanded_docs = self._expand_via_graph(documents, metadatas)
            graph_time = (time.time() - graph_start) * 1000
        
        # 3. Generar respuesta con contexto expandido
        context = self._format_context(expanded_docs)
        
        system_prompt = """Eres un asistente experto en recetas vegetarianas y veganas.
Usa el contexto (que incluye recetas relacionadas) para dar respuestas completas."""
        
        prompt = f"""Contexto de recetas (incluyendo relacionadas):
{context}

Pregunta: {query}

Responde usando el contexto proporcionado."""
        
        response_data, generation_time = self._measure_latency(
            self.llm_client.generate,
            prompt=prompt,
            system_prompt=system_prompt
        )
        
        # Calcular latencia total
        total_latency = retrieve_time + graph_time + generation_time
        
        # Extraer tokens
        input_tokens = response_data.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = response_data.get("usage", {}).get("completion_tokens", 0)
        
        # Registrar métricas
        self._track_metrics(total_latency, input_tokens, output_tokens)
        
        return {
            "strategy": self.name,
            "query": query,
            "response": response_data.get("response", ""),
            "initial_context": documents,
            "expanded_context": expanded_docs,
            "context_metadata": metadatas,
            "relevance_scores": [1 - d for d in distances],
            "latency_ms": total_latency,
            "retrieve_latency_ms": retrieve_time,
            "graph_expansion_latency_ms": graph_time,
            "generation_latency_ms": generation_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": response_data.get("model", self.llm_client.model),
            "provider": response_data.get("provider", self.llm_client.provider),
            "graph_enabled": self.knowledge_graph is not None
        }
    
    def _expand_via_graph(self, documents: List[str], metadatas: List[Dict]) -> List[str]:
        """
        Expande documentos usando el grafo de conocimiento
        
        Args:
            documents: Documentos iniciales
            metadatas: Metadatos de documentos
            
        Returns:
            Lista expandida de documentos
        """
        # Simplificado: en producción, traversar el grafo
        # Por ahora, solo retornar los documentos originales
        return documents
    
    def _format_context(self, documents: List[str]) -> str:
        """Formatea contexto"""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"Receta {i}:\n{doc}\n")
        return "\n".join(context_parts)
