from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Literal
from langchain_core.tools import tool
from pathlib import Path
import sys
import json
from sentence_transformers import CrossEncoder
import numpy as np

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# --- MODELS (No changes here) ---
class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        print(f"Cargando modelo de Reranking: {model_name}...")
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: list, metadatas: list, top_n: int = 3):
        if not documents:
            return [], [], []
        pairs = [[query, doc] for doc in documents]
        scores = self.model.predict(pairs)
        sorted_indices = np.argsort(scores)[::-1]
        reranked_docs = [documents[i] for i in sorted_indices[:top_n]]
        reranked_metadatas = [metadatas[i] for i in sorted_indices[:top_n]] 
        reranked_scores = [float(scores[i]) for i in sorted_indices[:top_n]]
        return reranked_docs, reranked_metadatas, reranked_scores

class NutritionalFilter(BaseModel):
    field: Literal["calories", "protein_g", "fat_g", "carbs_g", "sugar_g", "fiber_g", "sodium_mg"] = Field(..., description="Campo nutricional")
    operator: Literal["$gt", "$lt", "$gte", "$lte", "$eq"] = Field(..., description="Operador")
    value: float = Field(..., description="Valor")
    
class QueryOptimization(BaseModel):
    query: str = Field(..., description="Query expandida")
    user_asked_for: int = Field(3, description="Cantidad pedida")
    n_for_query: int = Field(9, description="Cantidad a buscar")
    nutritional_filters: Optional[list[NutritionalFilter]] = Field(None, description="Filtros nutricionales")
    nutritional_filter_operator: Literal["$and", "$or"] = Field("$and", description="Operador nutricional")
    ingredient_filters: Optional[list[str]] = Field(None, description="Ingredientes específicos")
    ingredient_filter_operator: Literal["$and", "$or"] = Field("$and", description="Operador ingredientes")
    
    @field_validator('n_for_query')
    @classmethod
    def validate_n_for_query(cls, v: int, info) -> int:
        user_asked = info.data.get('user_asked_for', 1)
        return max(v, user_asked * 3)

    def to_chroma_filters(self) -> tuple:
        where_metadata = None
        where_document = None
        
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
        
        if self.ingredient_filters:
            ingredients = [ing.lower() for ing in self.ingredient_filters]
            if len(ingredients) == 1:
                where_document = {"$contains": ingredients[0]}
            else:
                where_document = {
                    self.ingredient_filter_operator: [
                        {"$contains": ing} for ing in ingredients
                    ]
                }
        return where_metadata, where_document

# --- IMPLEMENTATION ---

def _optimize_query_impl(query: str, llm_client, **overrides) -> str:
    """
    1. Generates base parameters using LLM.
    2. Overwrites them with any specific 'overrides' passed by the agent.
    """
    system_prompt = """You are a search optimization expert.
    INPUT: User Query.
    OUTPUT: JSON with search parameters.
    
    CRITICAL RULES FOR ingredient_filter_operator:
    1. DEFAULT to "$and" (recipes must have ALL ingredients).
    2. Use "$or" (recipes with ANY ingredient) ONLY if:
       - Query contains "OR" (e.g., "chickpeas OR eggplant", "recipes with X OR Y")
       - Query says "any", "either", "alternative" (e.g., "recipes with either X or Y")
       - Query uses "/" between ingredients (e.g., "chickpeas/eggplant recipes")
    
    3. ingredient_filters: Extract ALL mentioned ingredients as a list in English.
       Examples:
       - "garbanzos" -> ["chickpeas"]
       - "chickpeas and eggplant" -> ["chickpeas", "eggplant"]  (operator: "$and")
       - "chickpeas OR eggplant" -> ["chickpeas", "eggplant"]   (operator: "$or")
       - "recipes with chickpeas or quinoa" -> ["chickpeas", "quinoa"]  (operator: "$or")
    
    4. When user says "Tengo X y Y", they usually mean they HAVE those ingredients and want flexible search -> use "$or"
    
    Common translations: garbanzos=chickpeas, lentejas=lentils, berenjena=eggplant
    """
    
    # 1. LLM Generation
    response = llm_client.generate(
        prompt=f'Analyze: "{query}"',
        system_prompt=system_prompt,
        structured_output=QueryOptimization,
        temperature=0.1
    )
    
    # 2. Parse Response
    if isinstance(response, dict) and "response" in response:
        try:
            params = QueryOptimization.model_validate_json(response["response"])
        except:
            params = QueryOptimization(**response)
    else:
        params = response

    # 3. CRITICAL: APPLY OVERRIDES (The Fix)
    # If the agent passed explicit args (like ingredient_filter_operator="$or"), we force them here.
    
    if overrides:
        print(f"   ⚠️ Applying Manual Overrides: {list(overrides.keys())}")
        current_data = params.model_dump()
        
        for key, value in overrides.items():
            if value is not None and key in current_data:
                # Special handling for operators to ensure they are valid
                if key == "ingredient_filter_operator" and value in ["$or", "$and"]:
                    print(f"      ↳ Forcing {key}: {current_data[key]} -> {value}")
                    current_data[key] = value
                
                elif key == "ingredient_filters" and isinstance(value, list):
                    current_data[key] = value
                    
                # Allow overriding query if needed
                elif key == "query":
                    current_data[key] = value
                    
                # Allow overriding nutritional filters (e.g. setting to None)
                elif key == "nutritional_filters":
                    current_data[key] = value

        # Re-validate with Pydantic to ensure integrity
        params = QueryOptimization(**current_data)

    return params.model_dump_json()


# --- TOOLS ---

@tool("optimize_query", description="Optimiza búsqueda. Argumentos opcionales invalidan la decisión del LLM.")
def optimize_query(query: str, **kwargs) -> str:
    """
    Optimiza la consulta.
    Puede recibir argumentos extra (ingredient_filter_operator, nutritional_filters, etc.)
    que SOBRESCRIBIRÁN lo que decida el LLM.
    """
    from src.utils.llm_client import get_llm_client
    from src.utils.config_loader import EXPANSION_LLM_PROVIDER, EXPANSION_MODEL,LANGCHAIN_TRACING_V2
    
    expansion_client = get_llm_client(
        provider=EXPANSION_LLM_PROVIDER,
        model=EXPANSION_MODEL,
        langsmith=LANGCHAIN_TRACING_V2
    )
    try:
        # Pass kwargs as overrides to the implementation
        return _optimize_query_impl(query, expansion_client, **kwargs)
    except Exception as e:
        return f"Error optimizing query: {str(e)}"

@tool("retrieve_documents", description="Recupera documentos de ChromaDB", args_schema=QueryOptimization)
def retrieve_documents(**kwargs) -> dict:
    from src.vector_db.chroma_manager import ChromaDBManager
    try:
        # Reconstruct Pydantic object
        query_params = QueryOptimization(**kwargs)
        
        vector_db = ChromaDBManager()
        where_metadata, where_document = query_params.to_chroma_filters()
        
        # Log active filters
        mode = query_params.ingredient_filter_operator
        print(f"DEBUG TOOL: Executing Retrieval | Mode: {mode} | Ingredients: {query_params.ingredient_filters}")
        
        results = vector_db.query(
            query_text=query_params.query,
            n_results=query_params.n_for_query,
            where_metadata=where_metadata,
            where_text=where_document
        )
        
        if not results or not results["documents"]:
             return {"documents": [], "metadatas": [], "user_asked_for": query_params.user_asked_for}
             
        return {
            "documents": results["documents"][0],
            "metadatas": results["metadatas"][0],
            "distances": results["distances"][0],
            "user_asked_for": query_params.user_asked_for
        }
    except Exception as e:
        return f"Error executing retrieval: {str(e)}"

@tool("rerank_documents", description="Re-rankea documentos.")
def rerank_documents(query: str, retrieval_results_json: str) -> str:
    try:
        # If retrieval returned string error or empty, handle it
        if isinstance(retrieval_results_json, str) and "Error" in retrieval_results_json:
             return "[]"
             
        results = json.loads(retrieval_results_json)
        if not results.get("documents"):
            return "[]"

        reranker = Reranker("cross-encoder/ms-marco-MiniLM-L-12-v2")
        ranked_docs, ranked_meta, ranked_scores = reranker.rerank(
            query, results["documents"], results["metadatas"], top_n=results["user_asked_for"]
        )
        
        return json.dumps({
            "documents": ranked_docs,
            "metadatas": ranked_meta,
            "scores": ranked_scores
        })
    except Exception as e:
        return f"Error reranking: {str(e)}"