"""
Graph Builder - Construcción Libre (Flexible)

- Usa SimpleLLMPathExtractor.
- Permite al LLM definir las relaciones libremente.
- Solo impone el formato "Sujeto -> PREDICADO -> Objeto" para asegurar la inserción.
"""
import sys
import os
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm
import time
import pandas as pd

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from llama_index.core import Document, PropertyGraphIndex, Settings
from llama_index.core.indices.property_graph import SimpleLLMPathExtractor
from llama_index.core.prompts import PromptTemplate
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from src.graph_db.neo4j_manager import Neo4jManager
from rag_config.config import (
    EMBEDDING_MODEL,
    GRAPH_CHUNK_SIZE,
    GRAPH_CHUNK_OVERLAP,
    CHROMA_GRAPH_DIRECTORY,
    DEFAULT_MODEL
)

# --- PROMPT FLEXIBLE ---
# Solo forzamos el formato de salida, no el contenido.
FREE_EXTRACT_TEMPLATE = """
Extract meaningful knowledge triplets from the text.
Use the format: Subject -> PREDICATE -> Object

Guidelines:
1. Identify the main Recipe.
2. Connect ingredients, nutrients, flavors, and techniques to the recipe.
3. Use concise predicates (e.g., HAS_INGREDIENT, CONTAINS, IS_HIGH_IN, COOKED_WITH).
4. One triplet per line. No extra text.

Example:
Pancakes -> HAS_INGREDIENT -> Flour
Pancakes -> HAS_NUTRIENT -> High Protein
Pancakes -> TASTES -> Sweet

Text:
{text}

Output:
"""

class GraphBuilder:
    def __init__(
        self,
        neo4j_manager: Optional[Neo4jManager] = None,
        llm_model: str = DEFAULT_MODEL,
        embedding_model: str = EMBEDDING_MODEL,
        show_progress: bool = True
    ):
        self.neo4j_manager = neo4j_manager or Neo4jManager()
        self.show_progress = show_progress
        
        # Configurar LLM
        print(f"Configurando Builder con LLM: {llm_model}")
        self.llm = Gemini(
            model=f"models/{llm_model}",
            api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.0
        )
        
        # Configurar Embeddings
        print(f"Configurando HuggingFace Embeddings: {embedding_model}")
        self.embed_model = HuggingFaceEmbedding(model_name=embedding_model)
        
        # ⭐ CRITICAL: Set global LlamaIndex settings to use HuggingFace
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        print("✓ LlamaIndex Settings configurado con HuggingFace embeddings")
        
        # Configurar Extractor Libre
        print("Configurando Extractor Flexible...")
        self.kg_extractor = SimpleLLMPathExtractor(
            llm=self.llm,
            max_paths_per_chunk=30, # Permitir muchas relaciones por receta
            num_workers=4
        )

        # Configurar Vector Store
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_GRAPH_DIRECTORY))
        chroma_collection = chroma_client.get_or_create_collection("knowledge_graph_vectors")
        self.vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        self.index = None

    def prepare_documents(self, df: pd.DataFrame) -> List[Document]:
        documents = []
        print(f"Preparando {len(df)} documentos...")
        
        for idx, row in tqdm(df.iterrows(), total=len(df), disable=not self.show_progress):
            text_content = row.get('text_to_embed', '')
            if not isinstance(text_content, str) or len(text_content) < 10:
                continue

            metadata = {
                "recipe_id": str(row.get('recipie_collection_idx', idx)),
                "name": row.get('name', 'Unknown'),
                "calories": float(row.get('calories', 0)),
                "protein_g": float(row.get('protein_g', 0)),
                # Añadimos entity_type para ayudar, aunque sea libre
                "entity_type": "Recipe"
            }
            
            doc = Document(text=text_content, metadata=metadata, id_=f"recipe_{metadata['recipe_id']}")
            documents.append(doc)
            
        return documents

    def build_graph(self, documents: List[Document], reset: bool = False) -> PropertyGraphIndex:
        if reset:
            print("⚠️ Limpiando base de datos...")
            self.neo4j_manager.clear_database(confirm=True)
            try: self.vector_store._collection.delete()
            except: pass

        print("=== CONSTRUYENDO GRAFO (MODO LIBRE) ===")
        self.index = PropertyGraphIndex.from_documents(
            documents=documents,
            kg_extractors=[self.kg_extractor], 
            llm=self.llm,
            embed_model=self.embed_model,
            property_graph_store=self.neo4j_manager.graph_store,
            vector_store=self.vector_store,
            show_progress=self.show_progress,
        )
        print("✓ Construcción finalizada.")
        return self.index

    def save_stats(self, path):
        # Implementación simple para guardar stats
        import json
        stats = self.neo4j_manager.get_statistics()
        with open(path, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def load_existing_index(self):
        """Carga el índice desde Neo4j sin reconstruir"""
        print("Cargando índice existente desde Neo4j...")
        
        self.index = PropertyGraphIndex(
            nodes=[],
            llm=self.llm,
            embed_model=self.embed_model,
            property_graph_store=self.neo4j_manager.graph_store,
            vector_store=self.vector_store,
            show_progress=self.show_progress
        )
        
        return self.index
