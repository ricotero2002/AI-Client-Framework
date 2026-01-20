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
from rag_practice_project.src.rag_strategies.modular_rag import ModularRAGStrategy
from rag_practice_project.src.rag_strategies.agentic_rag import AgenticRAGStrategy
from rag_practice_project.src.rag_strategies.graph_rag import GraphRAGStrategy
from rag_practice_project.src.evaluation.evaluator import ExperimentRunner
from rag_practice_project.config.config import RESULTS_DIR

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
    #"Dime algunas recetas que combinen frijoles negros y maíz.",
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
    strategies = [
        #NoRAGStrategy(),
        #NaiveRAGStrategy(top_k=3),
        AdvancedRAGStrategy(top_k=20),
        #ModularRAGStrategy(top_k=5),
        #AgenticRAGStrategy(max_iterations=3),
        #GraphRAGStrategy(top_k=5)
    ]
    
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
