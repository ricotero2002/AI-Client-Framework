"""
Utilidades para generar embeddings
"""
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.config_loader import EMBEDDING_MODEL, EMBEDDING_DIMENSION

class EmbeddingGenerator:
    """
    Clase para generar embeddings usando sentence-transformers
    """
    
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        """
        Inicializa el generador de embeddings
        
        Args:
            model_name: Nombre del modelo de sentence-transformers
        """
        print(f"Cargando modelo de embeddings: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"Modelo cargado. Dimensión de embeddings: {self.dimension}")
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32, show_progress: bool = True) -> np.ndarray:
        """
        Genera embeddings para uno o más textos
        
        Args:
            texts: Texto o lista de textos
            batch_size: Tamaño del batch para procesamiento
            show_progress: Mostrar barra de progreso
            
        Returns:
            np.ndarray: Array de embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def encode_single(self, text: str) -> np.ndarray:
        """
        Genera embedding para un solo texto
        
        Args:
            text: Texto a codificar
            
        Returns:
            np.ndarray: Embedding del texto
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def get_dimension(self) -> int:
        """
        Retorna la dimensión de los embeddings
        
        Returns:
            int: Dimensión de los embeddings
        """
        return self.dimension

# Instancia global del generador
_embedding_generator = None

def get_embedding_generator() -> EmbeddingGenerator:
    """
    Obtiene la instancia global del generador de embeddings (singleton)
    
    Returns:
        EmbeddingGenerator: Instancia del generador
    """
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator