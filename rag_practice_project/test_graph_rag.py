"""
Test script for Graph RAG Strategy

Este script carga el Knowledge Graph y prueba la estrategia Graph RAG
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.graph_db.neo4j_manager import Neo4jManager
from src.graph_db.graph_builder import GraphBuilder
from src.graph_db.graph_retriever import GraphRetriever
from src.rag_strategies.graph_rag import GraphRAGStrategy
import pandas as pd
from rag_config.config import PROCESSED_DATA_DIR


def main():
    print("==" * 40)
    print("TEST GRAPH RAG STRATEGY")
    print("==" * 40)
    
    # 1. Conectar a Neo4j y verificar grafo
    print("\n[1/4] Conectando a Neo4j...")
    neo4j_manager = Neo4jManager()
    stats = neo4j_manager.get_statistics()
    
    if stats["node_count"] == 0:
        print("❌ No hay Knowledge Graph construido")
        print("   Ejecuta: python setup_graph.py")
        return
    
    print(f"✓ Grafo encontrado: {stats['node_count']} nodos, {stats['relationship_count']} relaciones")
    
    # 2. Reconstruir el índice
    print("\n[2/4] Reconstruyendo PropertyGraphIndex...")
    df = pd.read_parquet(PROCESSED_DATA_DIR / "vegan_recipes_processed.parquet")
    
    builder = GraphBuilder(
        neo4j_manager=neo4j_manager,
        llm_model="gemini-2.5-pro",
        show_progress=False
    )
    
    # Preparar documentos
    documents = builder.prepare_documents(df)
    
    # Cargar el índice existente (no reconstruir)
    print("⚠️  Cargando índice existente (sin reconstruir)...")
    index = builder.load_existing_index()
    print("✓ Índice cargado")
    
    # 3. Crear Graph Retriever
    print("\n[3/4] Creando Graph Retriever...")
    graph_retriever = GraphRetriever(index, llm_model="gemini-2.5-flash")
    
    # 4. Inicializar y probar Graph RAG Strategy
    print("\n[4/4] Inicializando Graph RAG Strategy...")
    strategy = GraphRAGStrategy(
        top_k=5,
        graph_index=index,
        graph_retriever=graph_retriever
    )
    
    # Test queries
    test_queries = [
        "recetas con quinoa",
        "¿Qué recetas tienen alta proteína?",
        "Dame 3 recetas veganas para el desayuno"
    ]
    
    print("\n" + "==" * 40)
    print("PROBANDO GRAPH RAG")
    print("==" * 40)
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 80)
        
        result = strategy.generate_response(query)
        
        print(f"🔍 Método: {result['retrieval_decision']['method']}")
        print(f"📊 Nodos recuperados: {result['extra_info']['num_nodes_retrieved']}")
        print(f"⏱️  Latencia: {result['latency_ms']:.0f}ms")
        print(f"\n💬 Respuesta:\n{result['response']}\n")
    
    print("\n" + "==" * 40)
    print("✓ TEST COMPLETADO")
    print("==" * 40)
    
    # Cerrar conexión
    neo4j_manager.close()


if __name__ == "__main__":
    main()
