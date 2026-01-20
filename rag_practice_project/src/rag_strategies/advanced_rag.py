"""
Advanced RAG - Con optimización de consultas y re-ranking
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from pathlib import Path
import sys
import time

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.rag_strategies.base_strategy import BaseRAGStrategy
from src.utils.llm_client import get_llm_client
from src.vector_db.chroma_manager import ChromaDBManager
from src.utils.config_loader import EXPANSION_LLM_PROVIDER, EXPANSION_MODEL
from sentence_transformers import CrossEncoder
import numpy as np

class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Modelos recomendados:
        - "cross-encoder/ms-marco-MiniLM-L-6-v2" (Rápido y ligero)
        - "cross-encoder/ms-marco-MiniLM-L-12-v2" (Más preciso)
        - "BAAI/bge-reranker-base" (Excelente rendimiento actual)
        """
        print(f"Cargando modelo de Reranking: {model_name}...")
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: list, metadatas: list, top_n: int = 3):
        """
        Reordena los documentos recuperados por relevancia.
        """
        if not documents:
            return [], [], []

        # 1. Preparar los pares (Query, Documento) para el modelo
        pairs = [[query, doc] for doc in documents]

        # 2. Obtener los scores de relevancia (sigmoid scores)
        scores = self.model.predict(pairs)

        # 3. Ordenar índices de mayor a menor score
        sorted_indices = np.argsort(scores)[::-1]

        # 4. Seleccionar los mejores N
        reranked_docs = [documents[i] for i in sorted_indices[:top_n]]
        reranked_metadatas = [metadatas[i] for i in sorted_indices[:top_n]] 
        # Convertir numpy float32 a Python float para JSON serialization
        reranked_scores = [float(scores[i]) for i in sorted_indices[:top_n]]
        
        return reranked_docs, reranked_metadatas, reranked_scores


class AdvancedRAGStrategy(BaseRAGStrategy):
    """
    RAG avanzado con:
    - Pre-recuperación: Optimización de consultas
    - Post-recuperación: Re-ranking y filtrado
    """
    
    def __init__(self, top_k: int = 10, final_k: int = 5):
        super().__init__("Advanced RAG")
        self.llm_client = get_llm_client()  # Modelo principal para respuestas
        self.reranker = Reranker("cross-encoder/ms-marco-MiniLM-L-12-v2")
        # Modelo específico para expansión de queries
        self.expansion_client = get_llm_client(
            provider=EXPANSION_LLM_PROVIDER,
            model=EXPANSION_MODEL
        )
        self.vector_db = ChromaDBManager()
        self.top_k = top_k  # Recuperar más documentos inicialmente
        self.final_k = final_k  # Número final después de re-ranking
    
    def generate_response(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Genera respuesta usando RAG avanzado
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Dict con respuesta y métricas
        """
        # 1. PRE-RETRIEVAL: Optimizar consulta
        optimize_start = time.time()
        query_params = self._optimize_query(query)
        optimize_time = (time.time() - optimize_start) * 1000
        
        # 2. RETRIEVE: Recuperar documentos usando parámetros optimizados
        retrieve_start = time.time()
        
        # Extraer parámetros del structured output
        optimized_query_text = query_params.get("query", query)
        n_results = min(query_params.get("n_for_query", self.top_k), self.top_k)
        user_asked_for = query_params.get("n_for_query", 1)
        where_metadata = query_params.get("where_metadata", None)
        where_document = query_params.get("where_document", None)
        
        # Realizar query con todos los parámetros
        results = self.vector_db.query(
            query_text=optimized_query_text,
            n_results=n_results,
            where_metadata=where_metadata,
            where_text=where_document
        )
        retrieve_time = (time.time() - retrieve_start) * 1000
        
        # Extraer resultados
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        # 3. POST-RETRIEVAL: Re-ranking y filtrado
        rerank_start = time.time()
        ranked_docs, ranked_meta, ranked_scores = self.reranker.rerank(query, documents, metadatas, user_asked_for)
        rerank_time = (time.time() - rerank_start) * 1000 
        
        # 4. GENERATE: Generar respuesta con contexto optimizado
        context = self._format_context(ranked_docs, ranked_meta, ranked_scores)
        
        # System Prompt: Define el rol y las reglas de estilo permanentes
        system_prompt = """Eres un asistente experto en nutrición y cocina vegana/vegetariana. 
Tu objetivo es ayudar al usuario basándote EXCLUSIVAMENTE en las recetas proporcionadas, que han sido cuidadosamente seleccionadas y re-rankeadas por relevancia.

REGLAS DE ORO:
1. IDIOMA: Responde siempre en español. Traduce los nombres de las recetas de forma natural (ej: 'Chickpea Curry' -> 'Curry de garbanzos').
2. ESTILO: Usa un tono profesional y amable. Utiliza formato Markdown (negritas, listas) para mejorar la legibilidad.
3. RESTRICCIÓN DE ORIGEN: No menciones frases como "según el contexto" o "en la información proporcionada". Responde directamente.
4. CARACTERES: Usa gramática española correcta, incluyendo tildes y la letra ñ.
5. DATOS NUTRICIONALES: Si la consulta pide características específicas (proteína, calorías, grasa), debes incluir obligatoriamente el valor numérico por porción que aparece en el contexto.
6. PRIORIZACIÓN: Las recetas están ordenadas por relevancia. Prioriza las primeras en tu respuesta.

INSTRUCCIONES DE SALIDA:
- Si encontraste recetas que coincidan, enumera sus nombres traducidos en orden de relevancia.
- Si preguntaron por una característica nutricional, resalta el valor en negrita.
- Si no hay ninguna receta que encaje con la búsqueda, di que no la tienes y sugiere una búsqueda externa.
- Responde directamente a la pregunta sin rodeos.
"""

        # Few-shot: Ejemplos claros de la estructura esperada
        few_shot_examples = [
            {
                "query": "¿Tienes algo con mucha proteína?",
                "response": "Te recomiendo estas opciones altas en proteína:\n\n1. Espagueti de Calabaza con Vegetales Balsámicos - 13g de proteína por porción\n2. Curry de Garbanzos - 12g de proteína por porción\n\nAmbas son excelentes opciones para aumentar tu ingesta proteica."
            },
            {
                "query": "Dame 2 recetas con quinoa",
                "response": "Aquí tienes 2 recetas con quinoa:\n\n1. Tabulé de Quinoa - Una versión sin gluten del tabulé tradicional, sustituyendo el cuscús por quinoa.\n2. Bowl de Quinoa con Vegetales Asados - Quinoa combinada con vegetales de temporada.\n\nAmbas son nutritivas y fáciles de preparar."
            },
            {
                "query": "¿Cómo hago un postre sin azúcar?",
                "response": "Actualmente no cuento con recetas de postres sin azúcar en mi base de datos. Te sugiero buscar en internet opciones como 'Mousse de chocolate con aguacate y stevia' o 'Brownies de frijoles negros sin azúcar'."
            }
        ]

        # Prompt Final: Estructura para evitar que el modelo se pierda
        prompt = f"""Toma las siguientes recetas como tu única fuente de verdad (ordenadas por relevancia):

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
        total_latency = optimize_time + retrieve_time + rerank_time + generation_time
        
        # Extraer tokens
        input_tokens = response_data.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = response_data.get("usage", {}).get("completion_tokens", 0)
        
        # Registrar métricas
        self._track_metrics(total_latency, input_tokens, output_tokens)
        
        return {
            "strategy": self.name,
            "query": query,
            "optimized_query": optimized_query_text,
            "query_params": query_params,  # Incluir todos los parámetros de optimización
            "response": response_data.get("response", ""),
            "context": ranked_docs,
            "context_metadata": ranked_meta,
            "relevance_scores": ranked_scores,
            "latency_ms": total_latency,
            "optimize_latency_ms": optimize_time,
            "retrieve_latency_ms": retrieve_time,
            "rerank_latency_ms": rerank_time,
            "generation_latency_ms": generation_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": response_data.get("model", self.llm_client.model),
            "provider": response_data.get("provider", self.llm_client.provider),
            "query_optimization_model": self.expansion_client.model,  # Modelo usado para optimizar query
            # Extra info con todos los datos intermedios del pipeline
            "extra_info": {
                "original_retrieved_documents": documents,  # Documentos antes del re-ranking
                "original_retrieved_metadata": metadatas,  # Metadata antes del re-ranking
                "original_distances": distances,  # Distancias de similitud originales
                "num_retrieved": len(documents),  # Cantidad de documentos recuperados
                "num_after_rerank": len(ranked_docs),  # Cantidad después del re-ranking
                "documentos_recuperados": ranked_docs,  # Documentos después del re-ranking
                "documentos_metadata": ranked_meta,  # Metadata después del re-ranking
                "documentos_scores": ranked_scores,  # Scores después del re-ranking
                "query_optimization": {
                    "original_query": query,
                    "optimized_query": optimized_query_text,
                    "where_metadata_filter": where_metadata,
                    "where_document_filter": where_document,
                    "n_results_requested": n_results,
                    "user_asked_for": user_asked_for
                },
                "latency_breakdown": {
                    "optimize_ms": optimize_time,
                    "retrieve_ms": retrieve_time,
                    "rerank_ms": rerank_time,
                    "generation_ms": generation_time,
                    "total_ms": total_latency,
                    "optimize_percentage": (optimize_time / total_latency * 100) if total_latency > 0 else 0,
                    "retrieve_percentage": (retrieve_time / total_latency * 100) if total_latency > 0 else 0,
                    "rerank_percentage": (rerank_time / total_latency * 100) if total_latency > 0 else 0,
                    "generation_percentage": (generation_time / total_latency * 100) if total_latency > 0 else 0
                },
                "reranking_info": {
                    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-12-v2",
                    "score_improvements": [
                        {
                            "doc_index": i,
                            "original_score": 1 - distances[i] if i < len(distances) else 0,
                            "reranked_score": ranked_scores[i] if i < len(ranked_scores) else 0
                        }
                        for i in range(min(len(documents), len(ranked_scores)))
                    ]
                }
            }
        }
    
    def _optimize_query(self, query: str) -> Dict[str, Any]:
        """
        Optimiza la consulta para mejorar la recuperación
        
        Args:
            query: Consulta original
            
        Returns:
            Dict: Parámetros optimizados de query (query, where_metadata, where_document, n_for_query, user_asked_for)
        """
        # Expandir consulta con términos relacionados
        system_prompt = f"""Eres un experto en optimización de búsquedas en bases de datos vectoriales Y un experto en ChromaDB.
Tu objetivo es expandir la consulta del usuario para mejorar la recuperación de documentos.

PARÁMETROS DISPONIBLES:
- query: La consulta expandida con sinónimos y términos relacionados
- where_metadata: Filtro JSON para metadatos numéricos (ej: {{"calories": {{"$lt": 400}}, "protein_g": {{"$gt": 10}}}})
- where_document: Filtro para buscar texto específico en el documento (ej: {{"$contains": "quinoa"}})
- n_for_query: Cantidad de documentos a recuperar (máximo {self.top_k}), siempre mayor o igual a user_asked_for para poder hacer re-ranking posterior
- user_asked_for: Cantidad de recetas que el usuario pidió explícitamente

METADATOS DISPONIBLES: calories, protein_g, fat_g, carbs_g, cholesterol, sugar_g, fiber_g, sodium_mg, ingredients_text

REGLAS:
1. Si el usuario pide características nutricionales específicas, usa where_metadata
2. Si el usuario pide ingredientes específicos, usa where_document
3. Si pide más de {self.top_k} recetas, establece n_for_query en {self.top_k}
4. Si pide menos, puedes pedir hasta {self.top_k} para re-ranking posterior
5. where_metadata debe ser un dict válido de Python o null
6. where_document debe ser un dict válido de Python o null"""
        
        expansion_prompt = f"""Analiza esta consulta sobre recetas vegetarianas:
"{query}"

Genera:
1. Una query expandida con sinónimos y términos relacionados (máximo 2-3 oraciones)
2. Filtros where_metadata si hay requisitos nutricionales específicos
3. Filtros where_document si hay ingredientes específicos mencionados
4. El número apropiado de documentos a recuperar

Ejemplos:
- "recetas con mucha proteína" → where_metadata: {{"protein_g": {{"$gt": 15}}}}
- "algo con quinoa" → where_document: {{"$contains": "quinoa"}}
- "dame 3 recetas de sopas de menos de 200 calorias" Aqui tiene 3 recetas de sopas de menos de 200 calorias ... → where_document: {{"$contains": "sopa"}}, where_metadata: {{"$lt": 200}}, n_for_query: 9, user_asked_for: 3"""

        class QueryExpansion(BaseModel):
            query: str
            where_metadata: Optional[Dict[str, Any]] = None
            where_document: Optional[Dict[str, Any]] = None
            n_for_query: int = 10
            user_asked_for: int = 1
        
        # Usar el cliente de expansión específico
        response_data = self.expansion_client.generate(
            prompt=expansion_prompt,
            system_prompt=system_prompt,
            max_tokens=300,
            temperature=0.3,  # Más determinístico para structured output
            structured_output=QueryExpansion
        )
        
        # El response debería contener el objeto validado
        # Parsear el JSON response
        import json
        try:
            response_text = response_data.get("response", "{}")
            parsed_response = json.loads(response_text)
            return parsed_response
        except json.JSONDecodeError:
            # Fallback si no se puede parsear
            print(f"Warning: No se pudo parsear la respuesta estructurada. Usando query original.")
            return {
                "query": query,
                "where_metadata": None,
                "where_document": None,
                "n_for_query": self.top_k,
                "user_asked_for": 1
            }
    
    def _format_context(self, documents: List[str], metadatas: List[Dict], 
                       scores: List[float]) -> str:
        """
        Formatea contexto con información de relevancia
        
        Args:
            documents: Documentos
            metadatas: Metadatos
            scores: Scores de relevancia
            
        Returns:
            str: Contexto formateado
        """
        context_parts = []
        for i, (doc, meta, score) in enumerate(zip(documents, metadatas, scores), 1):
            context_parts.append(
                f"Receta {i} (Relevancia: {score:.2f}):\n{doc}\n"
            )
        
        return "\n".join(context_parts)
