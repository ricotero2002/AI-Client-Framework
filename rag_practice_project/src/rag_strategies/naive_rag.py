"""
Naive RAG - Recuperación → Lectura → Generación básica
"""
from typing import Dict, Any, List
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.rag_strategies.base_strategy import BaseRAGStrategy
from src.utils.llm_client import get_llm_client
from src.vector_db.chroma_manager import ChromaDBManager

class NaiveRAGStrategy(BaseRAGStrategy):
    """
    Implementación básica de RAG: Retrieve → Read → Generate
    """
    
    def __init__(self, top_k: int = 5):
        super().__init__("Naive RAG")
        self.llm_client = get_llm_client()
        self.vector_db = ChromaDBManager()
        self.top_k = top_k
    
    def generate_response(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Genera respuesta usando RAG básico
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Dict con respuesta y métricas
        """
        # 1. RETRIEVE: Recuperar documentos relevantes
        retrieve_start = time.time()
        results = self.vector_db.query(query, n_results=self.top_k)
        retrieve_time = (time.time() - retrieve_start) * 1000
        
        # Extraer documentos
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        # 2. READ: Formatear contexto
        context = self._format_context(documents, metadatas)
        
        # 3. GENERATE: Generar respuesta con contexto usando template
        # Import prompt template
        from src.utils.prompt_templates import create_naive_rag_prompt
        
        # System Prompt: Define el rol y las reglas de estilo permanentes
        system_prompt = """Eres un asistente experto en nutrición y cocina vegana/vegetariana. 
Tu objetivo es ayudar al usuario basándote EXCLUSIVAMENTE en las recetas proporcionadas.

REGLAS DE ORO:
1. IDIOMA: Responde siempre en español. Traduce los nombres de las recetas de forma natural (ej: 'Chickpea Curry' -> 'Curry de garbanzos').
2. ESTILO: Usa un tono profesional y amable. Utiliza formato Markdown (negritas, listas) para mejorar la legibilidad.
3. RESTRICCIÓN DE ORIGEN: No menciones frases como "según el contexto" o "en la información proporcionada". Responde directamente.
4. CARACTERES: Usa gramática española correcta, incluyendo tildes y la letra ñ.
5. DATOS NUTRICIONALES: Si la consulta pide características específicas (proteína, calorías, grasa), debes incluir obligatoriamente el valor numérico por porción que aparece en el contexto.
INSTRUCCIONES DE SALIDA:
- Si encontraste recetas que coincidan, enumera sus nombres traducidos. 
- Si preguntaron por una característica nutricional, resalta el valor en negrita.
- Si no hay ninguna receta que encaje con la búsqueda, di que no la tienes y sugiere una búsqueda externa.
- Responde directamente a la pregunta.
"""

# Few-shot: Ejemplos claros de la estructura esperada
        few_shot_examples = [
            {
                "query": "¿Tienes algo con mucha proteína?",
                "response": "Una excelente opción es el **Espagueti de Calabaza con Vegetales Balsámicos**. Esta receta aporta **13g de proteína** por porción."
            },
            {
                "query": "¿Cómo hago un postre sin azúcar?",
                "response": "Actualmente no cuento con recetas de postres en mi base de datos. Te sugiero buscar en internet opciones como un 'Mousse de chocolate con aguacate y stevia'."
            }
        ]

        # Prompt Final: Estructura para evitar que el modelo se pierda
        prompt = f"""Toma las siguientes recetas como tu única fuente de verdad:

CONTEXTO:
{context}

PREGUNTA DEL USUARIO: 
{query}
"""
        
        response_data, generation_time = self._measure_latency(
            self.llm_client.generate,
            prompt=prompt,
            system_prompt=system_prompt,
            few_shot_examples=few_shot_examples
        )
        
        # Calcular latencia total
        total_latency = retrieve_time + generation_time
        
        # Extraer tokens
        input_tokens = response_data.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = response_data.get("usage", {}).get("completion_tokens", 0)
        
        # Registrar métricas
        self._track_metrics(total_latency, input_tokens, output_tokens)
        
        print(response_data.get("response", ""))
        return {
            "strategy": self.name,
            "query": query,
            "response": response_data.get("response", ""),
            "context": documents,
            "context_metadata": metadatas,
            "relevance_scores": [1 - d for d in distances],  # Convertir distancia a score
            "latency_ms": total_latency,
            "retrieve_latency_ms": retrieve_time,
            "generation_latency_ms": generation_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": response_data.get("model", self.llm_client.model),
            "provider": response_data.get("provider", self.llm_client.provider)
        }
    
    def _format_context(self, documents: List[str], metadatas: List[Dict]) -> str:
        """
        Formatea los documentos recuperados como contexto
        
        Args:
            documents: Lista de documentos
            metadatas: Lista de metadatos
            
        Returns:
            str: Contexto formateado
        """
        context_parts = []
        for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
            context_parts.append(f"Receta {i}:\n{doc}\n")
        
        return "\n".join(context_parts)

import time
