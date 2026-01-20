"""
Modular RAG - Arquitectura modular con componentes intercambiables
"""
from typing import Dict, Any, List, Protocol
from pathlib import Path
import sys
import time

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.rag_strategies.base_strategy import BaseRAGStrategy
from src.utils.llm_client import get_llm_client
from src.vector_db.chroma_manager import ChromaDBManager

# Definir interfaces para módulos
class Retriever(Protocol):
    """Interface para módulos de recuperación"""
    def retrieve(self, query: str, top_k: int) -> Dict[str, Any]:
        ...

class QueryProcessor(Protocol):
    """Interface para procesadores de consultas"""
    def process(self, query: str) -> str:
        ...

class ContextBuilder(Protocol):
    """Interface para constructores de contexto"""
    def build(self, documents: List[str], metadatas: List[Dict]) -> str:
        ...

# Implementaciones concretas
class VectorRetriever:
    """Recuperador basado en vector database"""
    def __init__(self):
        self.vector_db = ChromaDBManager()
    
    def retrieve(self, query: str, top_k: int) -> Dict[str, Any]:
        return self.vector_db.query(query, n_results=top_k)

class SimpleQueryProcessor:
    """Procesador simple de consultas"""
    def process(self, query: str) -> str:
        return query.strip()

class ExpandedQueryProcessor:
    """Procesador que expande consultas"""
    def __init__(self):
        self.llm_client = get_llm_client()
    
    def process(self, query: str) -> str:
        expansion_prompt = f"""Expande esta consulta sobre recetas vegetarianas con términos relacionados:
"{query}"
Solo devuelve la consulta expandida (máximo 2 oraciones)."""
        
        response = self.llm_client.generate(
            prompt=expansion_prompt,
            system_prompt="Experto en búsquedas.",
            max_tokens=80
        )
        return response.get("response", query).strip()

class StandardContextBuilder:
    """Constructor estándar de contexto"""
    def build(self, documents: List[str], metadatas: List[Dict]) -> str:
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"Receta {i}:\n{doc}\n")
        return "\n".join(context_parts)

class EnhancedContextBuilder:
    """Constructor mejorado con metadatos"""
    def build(self, documents: List[str], metadatas: List[Dict]) -> str:
        context_parts = []
        for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
            title = meta.get('title', f'Receta {i}')
            context_parts.append(f"### {title}\n{doc}\n")
        return "\n".join(context_parts)

class ModularRAGStrategy(BaseRAGStrategy):
    """
    RAG modular con componentes intercambiables
    """
    
    def __init__(self, 
                 retriever: Retriever = None,
                 query_processor: QueryProcessor = None,
                 context_builder: ContextBuilder = None,
                 top_k: int = 5):
        super().__init__("Modular RAG")
        
        # Usar implementaciones por defecto si no se proporcionan
        self.retriever = retriever or VectorRetriever()
        self.query_processor = query_processor or ExpandedQueryProcessor()
        self.context_builder = context_builder or EnhancedContextBuilder()
        self.llm_client = get_llm_client()
        self.top_k = top_k
    
    def generate_response(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Genera respuesta usando arquitectura modular
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Dict con respuesta y métricas
        """
        # 1. Procesar consulta
        process_start = time.time()
        processed_query = self.query_processor.process(query)
        process_time = (time.time() - process_start) * 1000
        
        # 2. Recuperar documentos
        retrieve_start = time.time()
        results = self.retriever.retrieve(processed_query, self.top_k)
        retrieve_time = (time.time() - retrieve_start) * 1000
        
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        # 3. Construir contexto
        build_start = time.time()
        context = self.context_builder.build(documents, metadatas)
        build_time = (time.time() - build_start) * 1000
        
        # 4. Generar respuesta
        system_prompt = """Eres un asistente experto en recetas vegetarianas y veganas.
Usa el contexto proporcionado para dar respuestas precisas y útiles."""
        
        prompt = f"""Contexto:
{context}

Pregunta: {query}

Responde basándote en el contexto."""
        
        response_data, generation_time = self._measure_latency(
            self.llm_client.generate,
            prompt=prompt,
            system_prompt=system_prompt
        )
        
        # Calcular latencia total
        total_latency = process_time + retrieve_time + build_time + generation_time
        
        # Extraer tokens
        input_tokens = response_data.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = response_data.get("usage", {}).get("completion_tokens", 0)
        
        # Registrar métricas
        self._track_metrics(total_latency, input_tokens, output_tokens)
        
        # Determinar si el query processor usa un modelo
        query_processor_model = None
        if isinstance(self.query_processor, ExpandedQueryProcessor):
            query_processor_model = self.llm_client.model
        
        return {
            "strategy": self.name,
            "query": query,
            "processed_query": processed_query,
            "response": response_data.get("response", ""),
            "context": documents,
            "context_metadata": metadatas,
            "relevance_scores": [1 - d for d in distances],
            "latency_ms": total_latency,
            "process_latency_ms": process_time,
            "retrieve_latency_ms": retrieve_time,
            "build_latency_ms": build_time,
            "generation_latency_ms": generation_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": response_data.get("model", self.llm_client.model),
            "provider": response_data.get("provider", self.llm_client.provider),
            "query_processor_model": query_processor_model,  # Modelo usado para procesar query (si aplica)
            "modules": {
                "retriever": type(self.retriever).__name__,
                "query_processor": type(self.query_processor).__name__,
                "context_builder": type(self.context_builder).__name__
            }
        }
