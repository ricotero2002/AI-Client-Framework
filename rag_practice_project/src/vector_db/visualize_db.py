import sys
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
import numpy as np

# Ajusta los imports a tu estructura de carpetas
sys.path.append(str(Path(__file__).parent.parent))
from src.vector_db.chroma_manager import ChromaDBManager

def visualize_rag_query(query_text: str):
    print(f"--- Visualizando query: '{query_text}' ---")
    
    # 1. Inicializar Manager y obtener TODO la data
    manager = ChromaDBManager()
    
    # Obtenemos todos los documentos y embeddings de la colección
    # Nota: Chroma a veces limita el get(), asegúrate de traer todo si son pocos datos
    data = manager.collection.get(include=['embeddings', 'metadatas', 'documents'])
    
    all_embeddings = data['embeddings']
    all_metadatas = data['metadatas']
    count = len(all_embeddings)
    
    if count == 0:
        print("La base de datos está vacía. Ejecuta el setup primero.")
        return

    print(f"Recuperados {count} documentos para visualizar.")

    # 2. Embeddear la Query
    # Usamos el MISMO generador que usa el manager internamente
    query_embedding = manager.embedding_generator.encode_single(query_text)
    
    # 3. Reducción de Dimensionalidad (PCA) a 2D
    # Juntamos los embeddings de las recetas + el de la query para transformarlos juntos
    combined_embeddings = all_embeddings + [query_embedding.tolist()]
    
    pca = PCA(n_components=2)
    reduced_dims = pca.fit_transform(combined_embeddings)
    
    # Separamos: Las recetas son todos menos el último, la query es el último
    recipes_2d = reduced_dims[:-1]
    query_2d = reduced_dims[-1]

    # 4. Hacer la búsqueda real para saber cuáles resaltar (los vecinos cercanos)
    results = manager.collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=3 # Top 3
    )
    
    # Obtenemos los IDs de los resultados para pintarlos de otro color
    top_ids = results['ids'][0]
    
    # 5. GRAFICAR
    plt.figure(figsize=(12, 8))
    
    # A) Pintar todas las recetas (puntos grises/azules tenues)
    plt.scatter(recipes_2d[:, 0], recipes_2d[:, 1], c='lightgray', alpha=0.6, label='Otras recetas')
    
    # B) Pintar y etiquetar los Top Results (puntos verdes)
    # Necesitamos encontrar el índice de estos resultados en la lista original
    all_ids = data['ids']
    
    for idx, doc_id in enumerate(all_ids):
        if idx >= len(recipes_2d):  # Protección contra índices fuera de rango
            break
            
        x, y = recipes_2d[idx]
        
        # Si es uno de los resultados ganadores
        if doc_id in top_ids:
            plt.scatter(x, y, c='green', s=100, label='Resultado RAG' if doc_id == top_ids[0] else "")
            # Ponemos el nombre de la receta
            name = all_metadatas[idx].get('collection', 'Sin nombre')
            plt.text(x, y, f"  {name}", fontsize=9, fontweight='bold', color='darkgreen')
        else:
            # Opcional: poner nombre a todo (se puede ver desordenado)
            # plt.text(x, y, all_metadatas[idx].get('name', '')[:10], fontsize=6, alpha=0.5)
            pass

    # C) Pintar la Query (Estrella Roja)
    plt.scatter(query_2d[0], query_2d[1], c='red', marker='*', s=200, label=f'Query: "{query_text}"')
    
    plt.title(f"Visualización del Espacio Vectorial (PCA)\nQuery: '{query_text}'")
    plt.xlabel("Dimensión Principal 1")
    plt.ylabel("Dimensión Principal 2")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.3)
    
    print("Generando gráfico...")
    plt.show()

if __name__ == "__main__":
    # Prueba con algo que tenga sentido en tu dataset
    visualize_rag_query("plato con garbanzos y curry")