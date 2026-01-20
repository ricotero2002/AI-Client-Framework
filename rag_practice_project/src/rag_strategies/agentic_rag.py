"""
Agentic RAG - RAG con agentes autónomos que toman decisiones
"""
from typing import Dict, Any, List
from pathlib import Path
import sys
import time
import json

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.rag_strategies.base_strategy import BaseRAGStrategy
from src.utils.llm_client import get_llm_client
from src.vector_db.chroma_manager import ChromaDBManager

class AgenticRAGStrategy(BaseRAGStrategy):
    """
    RAG con agentes que deciden:
    - Si necesitan recuperar información
    - Cuántos documentos recuperar
    - Si necesitan refinar la búsqueda
    - Cómo estructurar la respuesta
    """
    
    def __init__(self, max_iterations: int = 3):
        super().__init__("Agentic RAG")
        self.llm_client = get_llm_client()
        self.vector_db = ChromaDBManager()
        self.max_iterations = max_iterations
    
    def generate_response(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Genera respuesta usando agentes autónomos
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Dict con respuesta y métricas
        """
        total_start = time.time()
        
        # Historial de acciones del agente
        agent_actions = []
        retrieved_docs = []
        
        # 1. Agente decide si necesita recuperar información
        decision_start = time.time()
        needs_retrieval = self._decide_retrieval_need(query)
        decision_time = (time.time() - decision_start) * 1000
        
        agent_actions.append({
            "action": "decide_retrieval",
            "decision": needs_retrieval,
            "time_ms": decision_time
        })
        
        retrieve_time = 0
        refine_time = 0
        
        if needs_retrieval:
            # 2. Agente decide cuántos documentos recuperar
            num_docs = self._decide_num_documents(query)
            agent_actions.append({
                "action": "decide_num_docs",
                "num_docs": num_docs
            })
            
            # 3. Recuperar documentos
            retrieve_start = time.time()
            results = self.vector_db.query(query, n_results=num_docs)
            retrieve_time = (time.time() - retrieve_start) * 1000
            
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            retrieved_docs = documents
            
            agent_actions.append({
                "action": "retrieve",
                "num_retrieved": len(documents),
                "time_ms": retrieve_time
            })
            
            # 4. Agente decide si necesita refinar la búsqueda
            refine_start = time.time()
            needs_refinement = self._decide_refinement(query, documents)
            refine_time = (time.time() - refine_start) * 1000
            
            if needs_refinement:
                # Refinar consulta y buscar de nuevo
                refined_query = self._refine_query(query, documents)
                results = self.vector_db.query(refined_query, n_results=num_docs)
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                
                agent_actions.append({
                    "action": "refine_search",
                    "refined_query": refined_query,
                    "time_ms": refine_time
                })
        
        # 5. Generar respuesta
        if needs_retrieval and retrieved_docs:
            context = self._format_context(retrieved_docs)
            prompt = f"""Contexto de recetas:
{context}

Pregunta: {query}

Responde basándote en el contexto."""
        else:
            prompt = query
        
        system_prompt = """Eres un asistente experto en recetas vegetarianas y veganas.
Responde de manera clara, concisa y útil."""
        
        response_data, generation_time = self._measure_latency(
            self.llm_client.generate,
            prompt=prompt,
            system_prompt=system_prompt
        )
        
        # Calcular latencia total
        total_latency = (time.time() - total_start) * 1000
        
        # Extraer tokens
        input_tokens = response_data.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = response_data.get("usage", {}).get("completion_tokens", 0)
        
        # Registrar métricas
        self._track_metrics(total_latency, input_tokens, output_tokens)
        
        return {
            "strategy": self.name,
            "query": query,
            "response": response_data.get("response", ""),
            "context": retrieved_docs if needs_retrieval else None,
            "agent_actions": agent_actions,
            "latency_ms": total_latency,
            "generation_latency_ms": generation_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": response_data.get("model", self.llm_client.model),
            "provider": response_data.get("provider", self.llm_client.provider),
            "agent_decision_model": self.llm_client.model  # Modelo usado para decisiones del agente
        }
    
    def _decide_retrieval_need(self, query: str) -> bool:
        """
        Agente decide si necesita recuperar información
        """
        decision_prompt = f"""Analiza esta consulta: "{query}"

¿Necesitas buscar recetas específicas para responder? 
Responde solo "SÍ" o "NO"."""
        
        response = self.llm_client.generate(
            prompt=decision_prompt,
            system_prompt="Eres un agente que decide si necesita información adicional.",
            max_tokens=10,
            temperature=0.1
        )
        
        answer = response.get("response", "").strip().upper()
        return "SÍ" in answer or "SI" in answer or "YES" in answer
    
    def _decide_num_documents(self, query: str) -> int:
        """
        Agente decide cuántos documentos recuperar
        """
        decision_prompt = f"""Para esta consulta: "{query}"

¿Cuántas recetas deberías recuperar? (entre 3 y 10)
Responde solo con un número."""
        
        response = self.llm_client.generate(
            prompt=decision_prompt,
            system_prompt="Decides cuántos documentos recuperar.",
            max_tokens=5,
            temperature=0.1
        )
        
        try:
            num = int(response.get("response", "5").strip())
            return max(3, min(10, num))  # Entre 3 y 10
        except:
            return 5  # Default
    
    def _decide_refinement(self, query: str, documents: List[str]) -> bool:
        """
        Agente decide si necesita refinar la búsqueda
        """
        # Simplificado: refinar si los documentos parecen poco relevantes
        if len(documents) < 3:
            return True
        return False
    
    def _refine_query(self, query: str, documents: List[str]) -> str:
        """
        Refina la consulta basándose en resultados previos
        """
        refine_prompt = f"""Consulta original: "{query}"

Los resultados no fueron muy relevantes. Reformula la consulta para mejorar la búsqueda.
Solo devuelve la consulta refinada."""
        
        response = self.llm_client.generate(
            prompt=refine_prompt,
            system_prompt="Refinas consultas de búsqueda.",
            max_tokens=50
        )
        
        return response.get("response", query).strip()
    
    def _format_context(self, documents: List[str]) -> str:
        """Formatea contexto"""
        return "\n\n".join([f"Receta {i+1}:\n{doc}" for i, doc in enumerate(documents)])
