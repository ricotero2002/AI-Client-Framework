"""
Test script for multi-ingredient support in Agentic RAG
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.llm_client import get_llm_client
from src.utils.config_loader import EXPANSION_LLM_PROVIDER, EXPANSION_MODEL, LANGCHAIN_TRACING_V2

# Import from the agentic_rag module
sys.path.insert(0, str(Path(__file__).parent))
from tools import QueryOptimization, _optimize_query_impl

def test_multi_ingredient():
    """Test the new multi-ingredient feature"""
    
    print("=" * 60)
    print("TESTING MULTI-INGREDIENT SUPPORT")
    print("=" * 60)
    
    # Create LLM client
    expansion_client = get_llm_client(
        provider=EXPANSION_LLM_PROVIDER,
        model=EXPANSION_MODEL,
        langsmith=LANGCHAIN_TRACING_V2
    )
    
    # Test queries
    test_queries = [
        "Tengo garbanzos y berenjena, ¿qué receta puedo hacer?",  # Should use $or (flexible)
        "Dame recetas con quinoa Y espinacas",  # Should use $and (strict)
        "Recetas de tomate o cebolla",  # Should use $or (explicit OR)
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"📝 Query: {query}")
        print("=" * 60)
        
        try:
            # Run optimization
            result_json = _optimize_query_impl(query, expansion_client)
            params = QueryOptimization.model_validate_json(result_json)
            
            print(f"\n✅ Optimization Result:")
            print(f"   - Query: {params.query}")
            print(f"   - User asked for: {params.user_asked_for}")
            print(f"   - N for query: {params.n_for_query}")
            
            if params.ingredient_filters:
                print(f"   - Ingredients: {params.ingredient_filters}")
                print(f"   - Ingredient operator: {params.ingredient_filter_operator}")
            
            if params.nutritional_filters:
                print(f"   - Nutritional filters: {params.nutritional_filters}")
                print(f"   - Nutritional operator: {params.nutritional_filter_operator}")
            
            # Test ChromaDB filter generation
            where_metadata, where_document = params.to_chroma_filters()
            print(f"\n🔍 ChromaDB Filters:")
            print(f"   - where_metadata: {where_metadata}")
            print(f"   - where_document: {where_document}")
            
        except Exception as e:
            print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_multi_ingredient()
