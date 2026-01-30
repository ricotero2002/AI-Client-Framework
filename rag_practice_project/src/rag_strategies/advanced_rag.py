"""
Advanced RAG - Con optimización de consultas y re-ranking
"""
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
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

class NutritionalFilter(BaseModel):
    """Filtro para valores nutricionales"""
    field: Literal["calories", "protein_g", "fat_g", "carbs_g", "sugar_g", "fiber_g", "sodium_mg"] = Field(..., description="Campo nutricional a filtrar")
    operator: Literal["$gt", "$lt", "$gte", "$lte", "$eq"] = Field(..., description="Operador de comparación")
    value: float = Field(..., description="Valor numérico para el filtro")
    
class QueryOptimization(BaseModel):
    """Parámetros optimizados de query"""
    query: str = Field(..., description="Query expandida con sinónimos")
    user_asked_for: int = Field(..., description="Cantidad exacta que el usuario pidió", ge=1, le=50)
    n_for_query: int = Field(..., description="Cantidad a recuperar para re-ranking (3x user_asked_for)", ge=3, le=50)
    nutritional_filters: Optional[list[NutritionalFilter]] = Field(default=None, description="Filtros nutricionales, si se mencionan valores nutricionales")
    nutritional_filter_operator: Literal["$and", "$or"] = Field(default="$and", description="Operador lógico para combinar múltiples filtros nutricionales")
    ingredient_filter: Optional[str] = Field(default=None, description="Ingrediente específico a buscar, si se menciona un ingrediente específico")
    
    @field_validator('n_for_query')
    @classmethod
    def validate_n_for_query(cls, v: int, info) -> int:
        """Asegurar que n_for_query >= user_asked_for * 3"""
        user_asked = info.data.get('user_asked_for', 1)
        min_n = user_asked * 3
        return max(v, min_n)

    def to_chroma_filters(self) -> tuple:
        """Convierte a formato ChromaDB"""
        where_metadata = None
        where_document = None
        
        # Construir where_metadata
        if self.nutritional_filters:
            if len(self.nutritional_filters) == 1:
                f = self.nutritional_filters[0]
                where_metadata = {f.field: {f.operator: f.value}}
            else:
                where_metadata = {
                    self.nutritional_filter_operator: [
                        {f.field: {f.operator: f.value}} for f in self.nutritional_filters
                    ]
                }
        
        # Construir where_document
        if self.ingredient_filter:
            where_document = {"$contains": self.ingredient_filter.lower()}
        
        return where_metadata, where_document



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
        print("[ADVANCED RAG] EXPANSION_MODEL", EXPANSION_MODEL)
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
        where_metadata, where_document = query_params.to_chroma_filters()
        # Realizar query con todos los parámetros
        results = self.vector_db.query(
            query_text=query_params.query,
            n_results=query_params.n_for_query,
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
        ranked_docs, ranked_meta, ranked_scores = self.reranker.rerank(query, documents, metadatas, query_params.user_asked_for)
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
7. RESPUESTA: Siempre contesta en base a las recetas proporcionadas, si no hay ninguna receta que encaje con la búsqueda, di que no la tienes y sugiere una búsqueda externa.

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
            "optimized_query": query_params.query,
            "query_params": query_params,  # Incluir todos los parámetros de optimización
            "response": response_data.get("response", ""),
            "context": context,
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
                    "optimized_query": query_params.query,
                    "where_metadata_filter": where_metadata,
                    "where_document_filter": where_document,
                    "n_results_requested": query_params.n_for_query,
                    "user_asked_for": query_params.user_asked_for
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
        # Función helper para testing (sin decorador @tool)
    def _optimize_query(self, query: str) -> QueryOptimization:
        """
        Implementación de optimización de query.
        Esta función puede ser llamada directamente para testing.
        """
        system_prompt = """Eres un experto en optimización de búsquedas de recetas.
    
METADATOS DISPONIBLES: calories, protein_g, fat_g, carbs_g, sugar_g, fiber_g, sodium_mg

REGLAS CRÍTICAS:
1. **user_asked_for**: 
   - Si el usuario especifica un número EXACTO (ej: "Dame 3 recetas", "una receta", "2 opciones") → usa ese número
   - Si hace una pregunta abierta (ej: "¿Qué recetas...?", "¿Cuáles son...?", "Recetas que...") → usa 5 (para mostrar varias opciones)
   - Si solo dice "recetas" en plural sin número ni pregunta → usa 3
   - Si dice "receta" en singular → usa 1
2. **n_for_query**: Calcula automáticamente como user_asked_for * 3 (para re-ranking, mínimo 9)
3. **nutritional_filters**: Si menciona valores nutricionales, crea filtros con:
   - field: nombre exacto del campo (ej: "protein_g", NO "protein")
   - operator: "$gt", "$lt", "$gte", "$lte", "$eq"
   - value: número extraído
   - **nutritional_filter_operator**: Si hay más de un filtro, indica si deben cumplirse todos ("$and") o al menos uno ("$or") basándote en conectores como "y" o "o". Por defecto usa "$and".
4. **ingredient_filter**: Si menciona un ingrediente específico, extráelo (ej: "quinoa") Y escribilo en ingles siempre. quinoa -> quinoa, lentejas -> lentils, garbanzos -> chickpeas, etc.
5. **query**: Expande con sinónimos, escribilo en ingles (ej: "sopas" → "soups broths consommés")

EJEMPLOS:
- "Dame 3 recetas con mucha proteína" → user_asked_for=3, n_for_query=9, nutritional_filters=[{"field":"protein_g", "operator":"$gt", "value":15}]
- "¿Qué recetas tienen más de 15g de proteína?" → user_asked_for=5, n_for_query=15, nutritional_filters=[{"field":"protein_g", "operator":"$gt", "value":15}]
- "Recetas de quinoa bajas en calorías" → user_asked_for=3, ingredient_filter="quinoa", nutritional_filters=[{"field":"calories", "operator":"$lt", "value":300}]
- "Dame una receta de sopa" → user_asked_for=1, n_for_query=3, query="soup broth"
"""
    
        expansion_prompt = f'Analiza esta consulta: "{query}"'
        
        response = self.expansion_client.generate(
            prompt=expansion_prompt,
            system_prompt=system_prompt,
            structured_output=QueryOptimization,
            temperature=0.2
        )
        
        # Parsear y validar
        params = QueryOptimization.model_validate_json(response["response"])
        return params
    
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
                f"Receta {i} (Relevancia: {score:.2f}):\n{doc}\n{meta}\n"
            )
        
        return "\n".join(context_parts)


##-------------------------------------------------------------------------------------------------------------
