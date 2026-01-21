from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Literal
from langchain_core.tools import tool
from pathlib import Path
import sys
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

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


# Función helper para testing (sin decorador @tool)
def _optimize_query_impl(query: str, llm_client) -> str:
    """
    Implementación de optimización de query.
    Esta función puede ser llamada directamente para testing.
    """
    system_prompt = """Eres un experto en optimización de búsquedas de recetas.
    
METADATOS DISPONIBLES: calories, protein_g, fat_g, carbs_g, sugar_g, fiber_g, sodium_mg

REGLAS CRÍTICAS:
1. **user_asked_for**: Extrae el número EXACTO que el usuario pidió (ej: "3 recetas" → 3). Si no menciona cantidad, usa 1. Si usa la palabra en plural "Recetas" es al menos 2.
2. **n_for_query**: Calcula automáticamente como user_asked_for * 3 (para re-ranking)
3. **nutritional_filters**: Si menciona valores nutricionales, crea filtros con:
   - field: nombre exacto del campo (ej: "protein_g", NO "protein")
   - operator: "$gt", "$lt", "$gte", "$lte", "$eq"
   - value: número extraído
   - **nutritional_filter_operator**: Si hay más de un filtro, indica si deben cumplirse todos ("$and") o al menos uno ("$or") basándote en conectores como "y" o "o". Por defecto usa "$and".
4. **ingredient_filter**: Si menciona un ingrediente específico, extráelo (ej: "quinoa")
5. **query**: Expande con sinónimos (ej: "sopas" → "sopas caldos consomés")

EJEMPLOS:
- "Dame 3 recetas con mucha proteína" → user_asked_for=3, n_for_query=9, nutritional_filters=[{"field":"protein_g", "operator":"$gt", "value":15}]
- "Recetas de quinoa bajas en calorías" → user_asked_for=1, ingredient_filter="quinoa", nutritional_filters=[{"field":"calories", "operator":"$lt", "value":300}]
"""
    
    expansion_prompt = f'Analiza esta consulta: "{query}"'
    
    response = llm_client.generate(
        prompt=expansion_prompt,
        system_prompt=system_prompt,
        structured_output=QueryOptimization,
        temperature=0.2
    )
    
    # Parsear y validar
    params = QueryOptimization.model_validate_json(response["response"])
    return params.model_dump_json()


# Decorador @tool para uso en LangGraph
@tool("optimize_query", description="Optimiza la consulta del usuario para mejorar la recuperación")
def optimize_query(query: str) -> str:
    """
    Optimiza la consulta del usuario para mejorar la recuperación.
    Retorna JSON con parámetros validados.
    
    Args:
        query: Consulta del usuario
        
    Returns:
        JSON string con QueryOptimization validado
    """
    # Esta función será llamada por LangGraph con el cliente ya configurado
    # Por ahora, retorna un placeholder que será reemplazado en la implementación real
    from src.utils.llm_client import get_llm_client
    from src.utils.config_loader import EXPANSION_LLM_PROVIDER, EXPANSION_MODEL
    
    expansion_client = get_llm_client(
        provider=EXPANSION_LLM_PROVIDER,
        model=EXPANSION_MODEL
    )
    
    return _optimize_query_impl(query, expansion_client)

@tool("retrieve_documents", description="Recupera documentos de ChromaDB usando parámetros optimizados",args_schema=QueryOptimization)
def retrieve_documents(query_params: QueryOptimization) -> dict:
    """
    Recupera documentos de ChromaDB usando parámetros optimizados.
    """
    from src.vector_db.chroma_manager import ChromaDBManager
    vector_db = ChromaDBManager()
    
    where_metadata, where_document = query_params.to_chroma_filters()
    
    results = vector_db.query(
        query_text=query_params.query,
        n_results=query_params.n_for_query,
        where_metadata=where_metadata,
        where_text=where_document
    )
    
    return {
        "documents": results["documents"][0],
        "metadatas": results["metadatas"][0],
        "distances": results["distances"][0],
        "user_asked_for": query_params.user_asked_for
    }

def _retrieve_documents_impl(query_params: QueryOptimization) -> dict:
    """Helper para testear retrieval sin depender del decorador tool de langchain."""
    from src.vector_db.chroma_manager import ChromaDBManager
    vector_db = ChromaDBManager()
    
    where_metadata, where_document = query_params.to_chroma_filters()
    results = vector_db.query(
        query_text=query_params.query,
        n_results=query_params.n_for_query,
        where_metadata=where_metadata,
        where_text=where_document
    )
    return {
        "documents": results["documents"][0],
        "metadatas": results["metadatas"][0],
        "distances": results["distances"][0],
        "user_asked_for": query_params.user_asked_for
    }


if __name__ == "__main__":
    # Test con cliente LLM real
    print("🧪 Testing Query Optimization Tool\n")
    
    try:
        from src.utils.llm_client import get_llm_client
        from src.utils.config_loader import EXPANSION_LLM_PROVIDER, EXPANSION_MODEL
        
        expansion_client = get_llm_client(
            provider=EXPANSION_LLM_PROVIDER,
            model=EXPANSION_MODEL
        )
        
        test_queries = [
            "Dime 3 recetas con mucha proteína",
            "Recetas de quinoa bajas en calorías",
            "Dame 5 recetas con mucha proteína y poca grasa",
            "Dame una receta con queso"
        ]
        
        for query in test_queries:
            print(f"📝 Query: {query}")
            
            # 1. OPTIMIZE
            opt_result_json = _optimize_query_impl(query, expansion_client)
            query_params = QueryOptimization.model_validate_json(opt_result_json)
            
            print(f"✅ Optimization Result:")
            print(f"   - user_asked_for: {query_params.user_asked_for}")
            print(f"   - n_for_query: {query_params.n_for_query}")
            print(f"   - query: {query_params.query}")
            if query_params.nutritional_filters:
                print(f"   - nutritional_filters: {query_params.nutritional_filters}")
            if query_params.ingredient_filter:
                print(f"   - ingredient_filter: {query_params.ingredient_filter}")
            
            # 2. RETRIEVE
            print(f"🔍 Testing Retrieval for query parameters...")
            retrieval_result = _retrieve_documents_impl(query_params)
            docs = retrieval_result["documents"]
            print(f"✅ Retrieved {len(docs)} documents.")
            for i, doc in enumerate(docs[:2]): # Mostrar solo los 2 primeros para no saturar
                print(f"   [{i+1}] {doc[:100]}...")
            print()
            
    except ImportError as e:
        print(f"❌ Error: No se pudo importar el cliente LLM: {e}")
        print("💡 Asegúrate de estar en el directorio correcto y tener las dependencias instaladas")
    except Exception as e:
        print(f"❌ Error durante el test: {e}")

