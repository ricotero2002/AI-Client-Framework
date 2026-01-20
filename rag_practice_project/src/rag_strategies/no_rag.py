"""
Estrategia No RAG - Baseline sin recuperación de contexto
"""
from typing import Dict, Any
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.rag_strategies.base_strategy import BaseRAGStrategy
from src.utils.llm_client import get_llm_client

class NoRAGStrategy(BaseRAGStrategy):
    """
    Estrategia baseline que no usa RAG, solo el LLM
    """
    
    def __init__(self):
        super().__init__("No RAG")
        self.llm_client = get_llm_client()
    
    def generate_response(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Genera respuesta sin usar contexto recuperado
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Dict con respuesta y métricas
        """
        # Import prompt template
        from src.utils.prompt_templates import create_no_rag_prompt
        
        # Crear prompt usando template
        # Nota: El template ya incluye system y user input estructurados
        # pero llm_client.generate() espera strings separados, así que
        # mantenemos la interfaz actual por compatibilidad
        system_prompt = """Eres un asistente experto en recetas vegetarianas y veganas.
Responde de manera clara, concisa y útil a las preguntas sobre recetas."""
        
        # Generar respuesta y medir latencia
        response_data, latency = self._measure_latency(
            self.llm_client.generate,
            prompt=query,
            system_prompt=system_prompt
        )
        
        # Extraer tokens (depende del cliente LLM)
        input_tokens = response_data.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = response_data.get("usage", {}).get("completion_tokens", 0)
        
        # Registrar métricas
        self._track_metrics(latency, input_tokens, output_tokens)
        
        return {
            "strategy": self.name,
            "query": query,
            "response": response_data.get("response", ""),
            "context": None,
            "latency_ms": latency,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": response_data.get("model", self.llm_client.model),
            "provider": response_data.get("provider", self.llm_client.provider)
        }
