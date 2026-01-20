"""
Gestión de ChromaDB para almacenar y recuperar recetas
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import pandas as pd
from pathlib import Path
import sys
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.config_loader import CHROMA_PERSIST_DIRECTORY, COLLECTION_NAME
from src.embeddings.embedding_generator import get_embedding_generator

class ChromaDBManager:
    """
    Clase para gestionar ChromaDB
    """
    
    def __init__(self, persist_directory: str = CHROMA_PERSIST_DIRECTORY, collection_name: str = COLLECTION_NAME):
        """
        Inicializa el gestor de ChromaDB
        
        Args:
            persist_directory: Directorio donde persistir la base de datos
            collection_name: Nombre de la colección
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Inicializar cliente de ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Obtener generador de embeddings
        self.embedding_generator = get_embedding_generator()
        
        # Crear o obtener colección
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"ChromaDB inicializado. Colección: {collection_name}")
        print(f"Documentos en la colección: {self.collection.count()}")
    
    def add_documents(self, df: pd.DataFrame, text_column: str = "text_to_embed", batch_size: int = 100):
        """
        Agrega documentos a la colección
        
        Args:
            df: DataFrame con los documentos
            text_column: Nombre de la columna con el texto
            batch_size: Tamaño del batch para inserción
        """
        print(f"Agregando {len(df)} documentos a ChromaDB...")
        
        # Preparar datos
        documents = df[text_column].tolist()

        # GESTIÓN DE IDs: Usar índice del dataframe
        ids = [f"doc_{i}" for i in range(len(df))]

        # PREPARAR METADATA
        # Excluir la columna de texto de la metadata para no duplicar info
        cols_to_exclude = [text_column,"name","recipie_collection_idx"]
        
        metadata_df = df.drop(columns=cols_to_exclude, errors='ignore')
        metadatas = metadata_df.to_dict('records')
        
        # Limpieza de tipos para Chroma (no acepta NaNs ni listas complejas)
        clean_metadatas = []
        for meta in metadatas:
            clean_meta = {}
            for k, v in meta.items():
                if pd.isna(v): continue  # Saltar NaNs
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)  # Convertir todo lo demás a string
            clean_metadatas.append(clean_meta)
        
        # Generar embeddings
        print("Generando embeddings...")
        embeddings = self.embedding_generator.encode(documents, batch_size=batch_size)
        
        # Insertar en batches
        print("Insertando en ChromaDB...")
        for i in tqdm(range(0, len(documents), batch_size)):
            end_idx = min(i + batch_size, len(documents))
            self.collection.add(
                embeddings=embeddings[i:end_idx].tolist(),
                documents=documents[i:end_idx],
                metadatas=clean_metadatas[i:end_idx],
                ids=ids[i:end_idx]
            )
        print(f"✓ {len(documents)} documentos agregados exitosamente")
    
    def query(self, query_text: str, n_results: int = 5, where_metadata: dict = None, where_text: dict = None) -> Dict[str, Any]:
        """
        Realiza una búsqueda en la colección
        
        Args:
            query_text: Texto de la consulta
            n_results: Número de resultados a retornar
            where_metadata: Diccionario para filtrar por metadata (ej: {"calories": {"$lt": 500}})
            where_text: Diccionario para filtrar por contenido del texto (ej: {"$contains": "quinoa"})
            
        Returns:
            Dict con los resultados
        """
        query_embedding = self.embedding_generator.encode_single(query_text)
        
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=where_metadata,      # Filtra en columnas como 'calories' o 'name'
            where_document=where_text   # Filtra dentro del texto del embedding (ingredientes/pasos)
        )
        return results

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la colección
        
        Returns:
            Dict con estadísticas
        """
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
            "persist_directory": self.persist_directory
        }
    
    def reset_collection(self):
        """
        Elimina y recrea la colección
        """
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"Colección {self.collection_name} reiniciada")


def setup_chroma_db(df: pd.DataFrame, reset: bool = False):
    """
    Configura ChromaDB con el dataset de recetas
    
    Args:
        df: DataFrame con las recetas
        reset: Si True, reinicia la colección antes de agregar documentos
    """
    manager = ChromaDBManager()
    
    if reset or manager.collection.count() == 0:
        if reset:
            manager.reset_collection()
        
        manager.add_documents(df)
    else:
        print(f"La colección ya contiene {manager.collection.count()} documentos")
        print("Usa reset=True para reiniciar la colección")
    
    return manager
