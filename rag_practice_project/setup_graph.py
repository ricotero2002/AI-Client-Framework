"""
Setup Knowledge Graph RAG

Este script:
1. Conecta a Neo4j Aura
2. Construye un PropertyGraphIndex usando LlamaIndex
3. Extrae entidades con Gemini 2.5 Pro (gratis)
4. Almacena en Neo4j + ChromaDB
"""
import nest_asyncio
nest_asyncio.apply()

from pathlib import Path
import sys

# Setup paths
PROJECT_ROOT = Path(__file__).parent.absolute()
FRAMEWORK_ROOT = PROJECT_ROOT.parent.absolute()

# Add framework to path if not already there
if str(FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_ROOT))

# Add project root to path (at the end to avoid shadowing framework)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Ahora sí importar módulos
import time
import pandas as pd

from src.graph_db.neo4j_manager import Neo4jManager
from src.graph_db.graph_builder import GraphBuilder
from src.graph_db.graph_retriever import GraphRetriever
from rag_config.config import PROCESSED_DATA_DIR, RESULTS_DIR


def main(sample_size: int = None, reset: bool = True):
    """
    Setup completo del Knowledge Graph
    
    Args:
        sample_size: Número de recetas a procesar (None = todas)
        reset: Si True, limpia la base de datos antes de construir
    """
    print("=" * 70)
    print("SETUP DE KNOWLEDGE GRAPH RAG")
    print("=" * 70)
    
    # 1. Test conexión a Neo4j
    print("\n[1/5] Verificando conexión a Neo4j Aura...")
    neo4j_manager = Neo4jManager()
    
    if not neo4j_manager.test_connection():
        print("\n❌ ERROR: No se pudo conectar a Neo4j Aura")
        print("\nVerifica:")
        print("1. Que tu instancia de Neo4j Aura esté activa")
        print("2. Que las credenciales en .env sean correctas:")
        print("   NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io")
        print("   NEO4J_USERNAME=neo4j")
        print("   NEO4J_PASSWORD=tu_password")
        return
    
    # Mostrar estadísticas actuales
    stats = neo4j_manager.get_statistics()
    print(f"\nEstadísticas actuales:")
    print(f"  - Nodos: {stats['node_count']}")
    print(f"  - Relaciones: {stats['relationship_count']}")
    
    # 2. Cargar dataset
    print("\n[2/5] Cargando dataset...")
    try:
        df = pd.read_parquet(PROCESSED_DATA_DIR / "vegan_recipes_processed.parquet")
        print(f"✓ Dataset cargado: {len(df)} recetas")
        
        # Limitar tamaño si se especifica
        if sample_size:
            df = df.head(sample_size)
            print(f"  (Usando muestra de {sample_size} recetas para prueba)")
    except Exception as e:
        print(f"❌ Error cargando dataset: {e}")
        return
    
    # 3. Construir Knowledge Graph
    print(f"\n[3/5] Construyendo Knowledge Graph...")
    print("⚠️  NOTA: Este proceso puede tardar varios minutos")
    print("⚠️  Gemini 2.5 Pro extraerá entidades de cada documento\n")
    
    builder = GraphBuilder(
        neo4j_manager=neo4j_manager,
        llm_model="gemini-2.5-pro", # Modelo Gemini 2.5 Pro
        show_progress=True
    )
    
    # Preparar documentos
    documents = builder.prepare_documents(df)
    
    # Construir grafo (esto tarda!)
    start_time = time.time()
    try:
        index = builder.build_graph(documents, reset=reset)
        build_time = time.time() - start_time
        
        print(f"\n✓ Grafo construido en {build_time:.2f}s")
        
        # Guardar estadísticas
        stats_path = RESULTS_DIR / "graph_build_stats.json"
        builder.save_stats(stats_path)
        
    except Exception as e:
        print(f"\n❌ Error construyendo grafo: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n[4/5] Configurando Graph Retriever...")
    try:
        # Import config to get default provider
        from rag_config.config import DEFAULT_LLM_PROVIDER
        retriever = GraphRetriever(index, llm_provider=DEFAULT_LLM_PROVIDER)
        print("✓ Retriever configurado")
    except Exception as e:
        print(f"❌ Error configurando retriever: {e}")
        return
    
    # 5. Probar consultas
    print("\n[5/5] Probando consultas...")
    
    test_queries = [
        "recipes with quinoa and high protein",
        "dinner recipes with avocado",
        "low calorie breakfast ideas"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Query {i}: '{query}' ---")
        try:
            result = retriever.query(query, return_metadata=True)
            print(f"Respuesta: {result['response'][:300]}...")
            print(f"Nodos recuperados: {result['num_nodes_retrieved']}")
        except Exception as e:
            print(f"Error en query: {e}")
    
    # Estadísticas finales
    final_stats = neo4j_manager.get_statistics()
    
    print("\n" + "=" * 70)
    print("✓ SETUP COMPLETADO EXITOSAMENTE")
    print("=" * 70)
    print(f"\nKnowledge Graph:")
    print(f"  - Nodos: {final_stats['node_count']}")
    print(f"  - Relaciones: {final_stats['relationship_count']}")
    print(f"  - Labels: {final_stats['labels']}")
    print(f"  - Tipos de relaciones: {final_stats['relationship_types']}")
    
    print(f"\nTiempo de construcción: {build_time:.2f}s")
    print(f"Estadísticas guardadas en: {stats_path}")
    
    print("\n" + "=" * 70)
    print("Próximos pasos:")
    print("1. Explorar el grafo en Neo4j Browser:")
    print("   - Abre tu Neo4j Aura console")
    print("   - Ejecuta: MATCH (n) RETURN n LIMIT 25")
    print("2. Comparar con vector RAG:")
    print("   - python compare_systems.py")
    print("=" * 70)
    
    # No cerrar la conexión para que el índice siga disponible
    # neo4j_manager.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Knowledge Graph RAG")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Número de recetas a procesar (default: todas)"
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="No limpiar la base de datos antes de construir"
    )
    
    args = parser.parse_args()
    
    main(sample_size=args.sample, reset=not args.no_reset)
