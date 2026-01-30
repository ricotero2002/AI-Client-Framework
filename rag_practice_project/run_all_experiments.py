"""
Script principal para ejecutar todos los experimentos RAG
"""
from pathlib import Path
import sys
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent))

from rag_practice_project.src.rag_strategies.no_rag import NoRAGStrategy
from rag_practice_project.src.rag_strategies.naive_rag import NaiveRAGStrategy
from rag_practice_project.src.rag_strategies.advanced_rag import AdvancedRAGStrategy
from rag_practice_project.src.rag_strategies.agentic_rag import AgenticRAGStrategy
from rag_practice_project.src.rag_strategies.graph_rag import GraphRAGStrategy
from rag_practice_project.src.evaluation.evaluator import ExperimentRunner
from rag_practice_project.config.config import RESULTS_DIR, PROCESSED_DATA_DIR

# Consultas de prueba

# Lista de consultas de prueba para estresar el sistema RAG
TEST_QUERIES = [
    #"¿Cómo preparar un brownie de chocolate vegano y sin gluten?",
    #"¿Cuál es el procedimiento para hacer leche de soja casera?",
    "Menciona exactamente 3 recetas que contengan garbanzos.",
    "¿Qué recetas tienen más de 15g de proteína por porción?",
    "Dame solo una receta de sopa que tenga menos de 200 calorías.",
    #"Dame una receta rápida para un desayuno con avena.",
    "Necesito recetas con quinoa que tengan al menos 12g de proteína.",
    #"¿Cómo preparar tacos de carne de res con crema?",
    "Tengo berenjena y garbanzos, ¿qué receta puedo hacer?",
    "Dame dos opciones de platos que sean picantes."
]

def main():
    """
    Función principal para ejecutar experimentos
    """
    print("=" * 60)
    print("EXPERIMENTOS RAG - RECETAS VEGETARIANAS")
    print("=" * 60)
    
    # Inicializar estrategias
    print("\nInicializando estrategias RAG...")
    
    # Cargar Knowledge Graph si se va a usar Graph RAG
    graph_index = None
    graph_retriever = None
    
    # Check if GraphRAGStrategy is needed
    use_graph_rag = True  # Set to False to skip graph loading
    
    if use_graph_rag:
        print("\n[Graph RAG] Cargando Knowledge Graph...")
        try:
            from src.graph_db.neo4j_manager import Neo4jManager
            from src.graph_db.graph_builder import GraphBuilder
            from src.graph_db.graph_retriever import GraphRetriever
            import pandas as pd
            
            # Conectar a Neo4j
            neo4j_manager = Neo4jManager()
            stats = neo4j_manager.get_statistics()
            
            if stats["node_count"] > 0:
                print(f"✓ Grafo encontrado: {stats['node_count']} nodos, {stats['relationship_count']} relaciones")
                
                # Cargar dataset
                df = pd.read_parquet(PROCESSED_DATA_DIR / "vegan_recipes_processed.parquet")
                
                # Reconstruir índice
                builder = GraphBuilder(
                    neo4j_manager=neo4j_manager,
                    llm_model="gemini-2.5-pro",
                    show_progress=False
                )
                
                documents = builder.prepare_documents(df)
                print("⚠️  Cargando índice existente (sin reconstruir)...")
                graph_index = builder.load_existing_index()
                
                # Initialize GraphRetriever with llm_provider from config
                from rag_config.config import EXPANSION_MODEL
                graph_retriever = GraphRetriever(
                    graph_index, 
                    llm_model=EXPANSION_MODEL
                )
                print("✓ Graph RAG listo")
            else:
                print("⚠️  No hay Knowledge Graph. GraphRAGStrategy no estará disponible.")
                use_graph_rag = False
        except Exception as e:
            print(f"⚠️  Error cargando grafo: {e}")
            print("   GraphRAGStrategy no estará disponible")
            use_graph_rag = False
    
    strategies = [
        #NoRAGStrategy(),
        #NaiveRAGStrategy(top_k=3),
        #AdvancedRAGStrategy(top_k=20),
        #AgenticRAGStrategy(max_iterations=15),
    ]
    
    # Add Graph RAG if loaded
    if use_graph_rag and graph_retriever is not None:
        strategies.append(GraphRAGStrategy(
            top_k=10, 
            graph_index=graph_index,
            graph_retriever=graph_retriever
        ))
    
    print(f"✓ {len(strategies)} estrategias inicializadas")
    
    # Crear runner de experimentos
    runner = ExperimentRunner(strategies, TEST_QUERIES)
    
    # Ejecutar experimentos
    results = runner.run_experiments()
    
    # Guardar resultados
    output_path = RESULTS_DIR / f"experiment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    runner.save_results(output_path)
    
    # Mostrar resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE RESULTADOS")
    print("=" * 60)
    
    from rag_practice_project.src.evaluation.analyzer import ResultsAnalyzer
    analyzer = ResultsAnalyzer(results)
    analyzer.print_summary()
    
    # Generar visualizaciones
    print("\nGenerando visualizaciones...")
    analyzer.generate_visualizations(RESULTS_DIR)
    
    print("\n✓ Experimentos completados exitosamente")
    print(f"Resultados guardados en: {RESULTS_DIR}")

if __name__ == "__main__":
    from datetime import datetime
    main()
