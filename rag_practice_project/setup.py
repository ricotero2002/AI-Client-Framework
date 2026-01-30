"""
Script de setup completo: cargar datos y crear vector database
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

from src.data.load_dataset import main as load_data
from src.vector_db.chroma_manager import setup_chroma_db
from src.vector_db.visualize_db import visualize_rag_query
import pandas as pd
from rag_config.config import PROCESSED_DATA_DIR

def main():
    """
    Setup completo del proyecto
    """
    print("=" * 60)
    print("SETUP DEL PROYECTO RAG")
    print("=" * 60)
    
    # 1. Cargar y procesar dataset
    print("\n[1/2] Cargando dataset de Kaggle...")
    try:
        df = load_data()
    except Exception as e:
        print(f"Error cargando dataset: {e}")
        print("Intentando cargar desde archivo local...")
        df = pd.read_parquet(PROCESSED_DATA_DIR / "vegan_recipes_processed.parquet")
    
    print(f"✓ Dataset cargado: {len(df)} recetas")
    
    # 2. Crear vector database
    print("\n[2/2] Creando vector database con ChromaDB...")
    chroma_manager = setup_chroma_db(df, reset=True)
    
    stats = chroma_manager.get_collection_stats()
    print(f"\n✓ Vector database creada:")
    print(f"  - Colección: {stats['name']}")
    print(f"  - Documentos: {stats['count']}")
    print(f"  - Directorio: {stats['persist_directory']}")
    
    # 3. Probar búsqueda
    print("\n[3/3] Probando búsqueda...")
    test_query = "recetas con quinoa y verduras"
    results = chroma_manager.query(
        query_text=test_query,
        n_results=5,
        where_text={"$contains": "quinoa"}
    )
    
    print(f"\nResultados para: '{test_query}'")
    for i, doc in enumerate(results["documents"][0], 1):
        print(f"\n{i}. {doc[:200]}...")

    # Ejemplo de Query "Advanced RAG"
    results = chroma_manager.query(
        query_text="cena ligera con aguacate",
        where_text={"$contains": "avocado"},
        where_metadata={
            "$and": [
                {"calories": {"$lt": 400}},       # Filtro numérico real
                {"protein_g": {"$gt": 10}}        # Filtro numérico real
            ]
        }
    )

    print(f"\nResultados para: 'cena ligera con aguacate'")
    for i, doc in enumerate(results["documents"][0], 1):
        print(f"\n{i}. {doc[:200]}...")

    print("\n" + "=" * 60)
    print("✓ SETUP COMPLETADO EXITOSAMENTE")
    print("=" * 60)
    print("\nPróximos pasos:")
    print("1. Configurar API keys en .env")
    print("2. Ejecutar experimentos: python experiments/run_all_experiments.py")

if __name__ == "__main__":
    main()
