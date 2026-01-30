"""
Comparación de Sistemas RAG

Compara el rendimiento entre:
1. Vector RAG (ChromaDB puro)
2. Graph RAG (Neo4j + ChromaDB + LlamaIndex)

Métricas:
- Tiempo de ingesta
- Costo de ingesta (tokens usados)
- Tiempo de consulta
- Calidad de respuestas
- Uso de memoria
"""
from pathlib import Path
import sys
# Setup paths
PROJECT_ROOT = Path(__file__).parent.absolute()
FRAMEWORK_ROOT = PROJECT_ROOT.parent.absolute()

# Add framework to path
if str(FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_ROOT))

# Add project root to path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import pandas as pd
import time
import json
from typing import Dict, Any, List
import matplotlib.pyplot as plt
import seaborn as sns

from src.vector_db.chroma_manager import ChromaDBManager
from src.graph_db.neo4j_manager import Neo4jManager
from src.graph_db.graph_builder import GraphBuilder
from src.graph_db.graph_retriever import GraphRetriever, SimpleGraphQueryEngine
from rag_config.config import PROCESSED_DATA_DIR, RESULTS_DIR


class SystemComparison:
    """
    Comparador de sistemas RAG
    """
    
    def __init__(self, sample_size: int = None):
        """
        Inicializa el comparador
        
        Args:
            sample_size: Número de documentos para la comparación
        """
        self.sample_size = sample_size
        self.results = {
            "vector_rag": {},
            "graph_rag": {},
            "comparison": {}
        }
        
        # Test queries
        self.test_queries = [
            "high protein quinoa recipes",
            "low calorie dinner with avocado",
            "breakfast recipes under 300 calories",
            "recipes with chickpeas and vegetables",
            "vegan desserts with chocolate"
        ]
    
    def load_data(self) -> pd.DataFrame:
        """Carga el dataset"""
        if self.sample_size:
            print(f"Cargando dataset (muestra de {self.sample_size} recetas)...")
        else:
            print(f"Cargando dataset completo...")
        df = pd.read_parquet(PROCESSED_DATA_DIR / "vegan_recipes_processed.parquet")
        df_sample = df.head(self.sample_size) if self.sample_size else df
        print(f"✓ {len(df_sample)} recetas cargadas\n")
        return df_sample
    
    def benchmark_vector_rag(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Benchmark del sistema Vector RAG
        
        Returns:
            Diccionario con métricas
        """
        print("=" * 70)
        print("BENCHMARK: VECTOR RAG (ChromaDB)")
        print("=" * 70)
        
        metrics = {
            "ingestion_time": 0,
            "ingestion_cost_tokens": 0,  # ChromaDB no usa LLM para indexar
            "query_times": [],
            "num_results": [],
            "system_type": "vector_rag"
        }
        
        # 1. Tiempo de ingesta
        print("\n[1/3] Midiendo tiempo de ingesta...")
        from src.vector_db.chroma_manager import setup_chroma_db
        
        start_time = time.time()
        chroma_manager = setup_chroma_db(df, reset=True)
        metrics["ingestion_time"] = time.time() - start_time
        
        print(f"✓ Ingesta completada en {metrics['ingestion_time']:.2f}s")
        print(f"  Costo en tokens: 0 (solo embeddings, no LLM)")
        
        # 2. Estadísticas
        stats = chroma_manager.get_collection_stats()
        metrics["total_documents"] = stats["count"]
        
        # 3. Tiempo de consulta
        print("\n[2/3] Midiendo tiempo de consulta...")
        for query in self.test_queries:
            start_time = time.time()
            results = chroma_manager.query(query_text=query, n_results=5)
            query_time = time.time() - start_time
            
            metrics["query_times"].append(query_time)
            metrics["num_results"].append(len(results["documents"][0]))
            
            print(f"  Query: '{query[:40]}...' - {query_time*1000:.1f}ms")
        
        metrics["avg_query_time"] = sum(metrics["query_times"]) / len(metrics["query_times"])
        
        print(f"\n✓ Tiempo promedio de consulta: {metrics['avg_query_time']*1000:.1f}ms")
        
        self.results["vector_rag"] = metrics
        return metrics
    
    def benchmark_graph_rag(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Benchmark del sistema Graph RAG
        
        Returns:
            Diccionario con métricas
        """
        print("\n" + "=" * 70)
        print("BENCHMARK: GRAPH RAG (Neo4j + ChromaDB + LlamaIndex)")
        print("=" * 70)
        
        metrics = {
            "ingestion_time": 0,
            "ingestion_cost_tokens": 0,  # Estimación basada en uso de Ollama
            "query_times": [],
            "num_results": [],
            "system_type": "graph_rag",
            "graph_stats": {}
        }
        
        # 1. Tiempo de ingesta
        print("\n[1/4] Midiendo tiempo de ingesta (con extracción de entidades)...")
        print("⚠️  Esto puede tardar varios minutos...\n")
        
        neo4j_manager = Neo4jManager()
        builder = GraphBuilder(
        neo4j_manager=neo4j_manager,
        llm_provider="gemini",      # Usar Gemini (gratis)
        llm_model="gemini-2.5-pro", # Modelo Gemini 2.5 Pro
        langsmith=False,             # Cambiar a True para habilitar tracing
        show_progress=True
    )
        
        documents = builder.prepare_documents(df)
        
        start_time = time.time()
        index = builder.build_graph(documents, reset=True)
        metrics["ingestion_time"] = time.time() - start_time
        
        # Obtener estadísticas de construcción
        build_stats = builder.get_build_stats()
        metrics["graph_stats"] = build_stats
        
        print(f"\n✓ Ingesta completada en {metrics['ingestion_time']:.2f}s")
        
        # Estimación de tokens (Ollama local = gratis pero tiene costo computacional)
        # Asumimos ~500 tokens por documento procesado
        estimated_tokens = len(df) * 500
        metrics["ingestion_cost_tokens"] = estimated_tokens
        print(f"  Tokens estimados (Ollama): ~{estimated_tokens:,}")
        print(f"  Costo real: $0 (modelo local)")
        
        # 2. Configurar retriever
        print("\n[2/4] Configurando retriever...")
        retriever = GraphRetriever(index)
        query_engine = SimpleGraphQueryEngine(retriever)
        
        # 3. Tiempo de consulta
        print("\n[3/4] Midiendo tiempo de consulta...")
        for query in self.test_queries:
            start_time = time.time()
            results = query_engine.query(query_text=query, n_results=5)
            query_time = time.time() - start_time
            
            metrics["query_times"].append(query_time)
            metrics["num_results"].append(len(results["documents"][0]))
            
            print(f"  Query: '{query[:40]}...' - {query_time*1000:.1f}ms")
        
        metrics["avg_query_time"] = sum(metrics["query_times"]) / len(metrics["query_times"])
        
        print(f"\n✓ Tiempo promedio de consulta: {metrics['avg_query_time']*1000:.1f}ms")
        
        # 4. Estadísticas del grafo
        graph_stats = neo4j_manager.get_statistics()
        metrics["graph_node_count"] = graph_stats["node_count"]
        metrics["graph_relationship_count"] = graph_stats["relationship_count"]
        
        print(f"\n[4/4] Estadísticas del grafo:")
        print(f"  - Nodos: {metrics['graph_node_count']}")
        print(f"  - Relaciones: {metrics['graph_relationship_count']}")
        
        self.results["graph_rag"] = metrics
        return metrics
    
    def compare_systems(self):
        """Compara los sistemas y genera reporte"""
        print("\n" + "=" * 70)
        print("COMPARACIÓN DE SISTEMAS")
        print("=" * 70)
        
        v = self.results["vector_rag"]
        g = self.results["graph_rag"]
        
        comparison = {
            "ingestion": {
                "vector_time_s": v["ingestion_time"],
                "graph_time_s": g["ingestion_time"],
                "speedup": v["ingestion_time"] / g["ingestion_time"],
                "winner": "Vector RAG" if v["ingestion_time"] < g["ingestion_time"] else "Graph RAG"
            },
            "cost": {
                "vector_tokens": v["ingestion_cost_tokens"],
                "graph_tokens": g["ingestion_cost_tokens"],
                "note": "Vector RAG no usa LLM. Graph RAG usa Ollama (gratis)"
            },
            "query_performance": {
                "vector_avg_ms": v["avg_query_time"] * 1000,
                "graph_avg_ms": g["avg_query_time"] * 1000,
                "speedup": v["avg_query_time"] / g["avg_query_time"],
                "winner": "Vector RAG" if v["avg_query_time"] < g["avg_query_time"] else "Graph RAG"
            }
        }
        
        self.results["comparison"] = comparison
        
        # Imprimir reporte
        print("\n📊 RESULTADOS:")
        print("\n1. TIEMPO DE INGESTA:")
        print(f"   Vector RAG: {comparison['ingestion']['vector_time_s']:.2f}s")
        print(f"   Graph RAG:  {comparison['ingestion']['graph_time_s']:.2f}s")
        print(f"   → Ganador:  {comparison['ingestion']['winner']}")
        print(f"   → Factor:   {comparison['ingestion']['speedup']:.2f}x")
        
        print("\n2. COSTO DE INGESTA:")
        print(f"   Vector RAG: {comparison['cost']['vector_tokens']:,} tokens (0)")
        print(f"   Graph RAG:  ~{comparison['cost']['graph_tokens']:,} tokens (Ollama = gratis)")
        print(f"   → {comparison['cost']['note']}")
        
        print("\n3. RENDIMIENTO DE CONSULTA:")
        print(f"   Vector RAG: {comparison['query_performance']['vector_avg_ms']:.1f}ms")
        print(f"   Graph RAG:  {comparison['query_performance']['graph_avg_ms']:.1f}ms")
        print(f"   → Ganador:  {comparison['query_performance']['winner']}")
        print(f"   → Factor:   {comparison['query_performance']['speedup']:.2f}x")
        
        print("\n4. CAPACIDADES:")
        print("   Vector RAG:")
        print("   ✓ Búsqueda semántica rápida")
        print("   ✓ Filtros por metadata")
        print("   ✗ No entiende relaciones entre entidades")
        print("\n   Graph RAG:")
        print("   ✓ Búsqueda semántica")
        print("   ✓ Navegación por relaciones (multi-hop)")
        print("   ✓ Descubrimiento de conexiones")
        print("   ✗ Más lento en ingesta (extracción de entidades)")
        
        print("\n💡 RECOMENDACIONES:")
        print("\n   Usa Vector RAG cuando:")
        print("   - Necesitas ingesta rápida")
        print("   - Solo haces búsqueda por similitud")
        print("   - Tu dataset cambia frecuentemente")
        
        print("\n   Usa Graph RAG cuando:")
        print("   - Necesitas entender relaciones entre entidades")
        print("   - Haces preguntas multi-hop (ej: 'ingredientes comunes entre X y Y')")
        print("   - Quieres explorar conexiones en tus datos")
        
        return comparison
    
    def save_results(self):
        """Guarda resultados en JSON"""
        output_path = RESULTS_DIR / "system_comparison.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Resultados guardados en: {output_path}")
    
    def create_visualizations(self):
        """Crea gráficos comparativos"""
        print("\nGenerando visualizaciones...")
        
        v = self.results["vector_rag"]
        g = self.results["graph_rag"]
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        # 1. Tiempo de ingesta
        axes[0].bar(
            ["Vector RAG", "Graph RAG"],
            [v["ingestion_time"], g["ingestion_time"]],
            color=["#3498db", "#e74c3c"]
        )
        axes[0].set_ylabel("Tiempo (segundos)")
        axes[0].set_title("Tiempo de Ingesta")
        axes[0].grid(axis='y', alpha=0.3)
        
        # 2. Tiempo de consulta
        axes[1].bar(
            ["Vector RAG", "Graph RAG"],
            [v["avg_query_time"] * 1000, g["avg_query_time"] * 1000],
            color=["#3498db", "#e74c3c"]
        )
        axes[1].set_ylabel("Tiempo (ms)")
        axes[1].set_title("Tiempo Promedio de Consulta")
        axes[1].grid(axis='y', alpha=0.3)
        
        # 3. Tokens de ingesta
        axes[2].bar(
            ["Vector RAG", "Graph RAG"],
            [v["ingestion_cost_tokens"], g["ingestion_cost_tokens"]],
            color=["#3498db", "#e74c3c"]
        )
        axes[2].set_ylabel("Tokens estimados")
        axes[2].set_title("Costo de Ingesta (Tokens)")
        axes[2].grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        output_path = RESULTS_DIR / "system_comparison.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Gráficos guardados en: {output_path}")
        
        plt.close()
    
    def run(self):
        """Ejecuta comparación completa"""
        print("\n" + "=" * 70)
        print("COMPARACIÓN DE SISTEMAS RAG")
        print("=" * 70)
        print(f"Muestra: {self.sample_size} documentos")
        print("=" * 70)
        
        # Cargar datos
        df = self.load_data()
        
        # Benchmark Vector RAG
        self.benchmark_vector_rag(df)
        
        # Benchmark Graph RAG
        self.benchmark_graph_rag(df)
        
        # Comparar
        self.compare_systems()
        
        # Guardar y visualizar
        self.save_results()
        self.create_visualizations()
        
        print("\n" + "=" * 70)
        print("✓ COMPARACIÓN COMPLETADA")
        print("=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Comparar sistemas RAG")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Número de documentos a usar (default: todos)"
    )
    
    args = parser.parse_args()
    
    comparator = SystemComparison(sample_size=args.sample)
    comparator.run()
