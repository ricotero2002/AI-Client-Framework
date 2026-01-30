"""
Script de prueba rápida para verificar que el wrapper de AgenticRAG funciona
"""
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from rag_practice_project.src.rag_strategies.agentic_rag import AgenticRAGStrategy

def main():
    print("=" * 60)
    print("PRUEBA DEL WRAPPER AGENTIC RAG")
    print("=" * 60)
    
    # Crear instancia
    print("\n1. Creando instancia de AgenticRAGStrategy...")
    strategy = AgenticRAGStrategy(max_iterations=5)
    print(f"✓ Estrategia creada: {strategy.name}")
    
    # Prueba simple
    test_query = "Dame 2 recetas con garbanzos"
    print(f"\n2. Probando con query: '{test_query}'")
    print("   (Esto puede tomar unos segundos...)\n")
    
    result = strategy.generate_response(test_query)
    
    print("\n3. Resultados:")
    print(f"   - Strategy: {result.get('strategy')}")
    print(f"   - Query original: {result.get('query')}")
    print(f"   - Query optimizada: {result.get('optimized_query')}")
    print(f"   - Latencia: {result.get('latency_ms', 0):.2f} ms")
    print(f"   - Iteraciones: {result.get('iterations')}")
    print(f"   - Tools usados: {len(result.get('tools_used', []))}")
    print(f"   - Respuesta: {result.get('response')[:200]}...")
    
    if 'error' in result:
        print(f"\n⚠️  ERROR: {result['error']}")
    else:
        print("\n✓ Wrapper funcionando correctamente!")

if __name__ == "__main__":
    main()
