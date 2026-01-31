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

# ============================================================================
# IMPORTANTE: Formato para DeepEval (ACTUALIZADO)
# ============================================================================
# TEST_QUERIES ahora requiere el formato:
# [
#     {"query": "Pregunta del usuario", "expected_output": "Respuesta esperada"},
#     {"query": "Otra pregunta", "expected_output": "Otra respuesta esperada"}
# ]
#
# El "expected_output" (Ground Truth) es necesario para que DeepEval evalúe:
# - Contextual Recall: ¿El contexto tiene la info necesaria?
# - Faithfulness: ¿La respuesta alucina información?
# - Answer Relevancy: ¿La respuesta es relevante a la query?
#
# Si NO tienes Ground Truth, puedes usar un placeholder:
# {"query": "...", "expected_output": "Respuesta detallada sobre la consulta."}
#
# Ver: src/evaluation/test_queries_example.py para ejemplos completos
# Ver: src/evaluation/DEEPEVAL_GUIDE.md para documentación completa
# ============================================================================

# TODO: Actualizar a nuevo formato con expected_output para cada query
# Lista de consultas de prueba para estresar el sistema RAG
# ============================================================================
# DATASET DE PRUEBA (Ground Truth)
# Basado en análisis de 'vegan_recipes_processed.csv'
# ============================================================================

TEST_QUERIES = [
    {
        "query": "Menciona exactamente 3 recetas que contengan garbanzos.",
        "expected_output": "Aquí tienes 3 recetas con garbanzos disponibles en la base de datos: 1) Chickpea & Potato Curry, 2) Roasted Curried Chickpeas and Cauliflower, 3) Lemony Chickpeas (o Mediterranean Chickpeas)."
    },
    {
        "query": "Dame solo una receta de sopa que tenga menos de 200 calorías.",
        "expected_output": "Puedes preparar la 'Creamy Cauliflower Pakora Soup', que tiene solo 135 calorías por porción."
    },
    {
        "query": "Necesito recetas con quinoa que tengan al menos 12g de proteína.",
        "expected_output": "Tengo estas opciones con quinoa y buena proteína: 'Garden Quinoa Salad' que cuenta con 16g de proteína y 'Black Bean & Corn Quinoa' que cuenta con 13g de proteína."
    },
    {
        "query": "¿Cómo preparar tacos de carne de res con crema?",
        "expected_output": "Soy vegano, por lo que no conozco recetas con carne de res. Como alternativa de estilo mexicano sin carne, te sugiero probar las 'No-Fry Black Bean Chimichangas' o el 'Black Bean-Tomato Chili'."
    },
    {
        "query": "Tengo berenjena y garbanzos, ¿qué receta puedo hacer?",
        "expected_output": "No tengo ninguna receta que combine específicamente berenjena y garbanzos. Sin embargo, tengo varias recetas excelentes solo con garbanzos, como el 'Chickpea & Potato Curry' o los 'Garbanzo-Stuffed Mini Peppers'."
    },
    {
        "query": "Dame dos opciones de platos que sean picantes.",
        "expected_output": "Dos opciones con perfil de sabor picante o especiado son: 1) 'Chickpea & Potato Curry' y 2) 'Tropical Fusion Salad with Spicy Tortilla Ribbons' (o el 'Black Bean-Tomato Chili')."
    }
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
        NaiveRAGStrategy(top_k=3),
        AdvancedRAGStrategy(top_k=20),
        AgenticRAGStrategy(max_iterations=15),
    ]
    
    # Add Graph RAG if loaded``
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
