import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from llama_index.core import PropertyGraphIndex, Settings
from llama_index.core.indices.property_graph import VectorContextRetriever
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from src.graph_db.neo4j_manager import Neo4jManager
from rag_config.config import DEFAULT_MODEL, EMBEDDING_MODEL

class GraphRetriever:
    def __init__(
        self,
        index: PropertyGraphIndex,
        llm_model: str = DEFAULT_MODEL, 
        similarity_top_k: int = 15,
    ):
        self.index = index
        self.neo4j_manager = Neo4jManager() 
        self.llm = Gemini(model=f"models/{llm_model}", temperature=0.0)
        
        embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL)
        Settings.llm = self.llm
        Settings.embed_model = embed_model
        
        self.vector_retriever = VectorContextRetriever(
            self.index.property_graph_store,
            vector_store=self.index._vector_store,
            similarity_top_k=similarity_top_k
        )
        
        # --- CARGA DINÁMICA DEL ESQUEMA ---
        print("🔍 Inspeccionando esquema detallado...")
        self.schema_context = self._get_graph_schema()
        print(f"✓ Esquema cargado:\n{self.schema_context}")

    def _get_graph_schema(self) -> str:
        """
        Obtiene Labels, Relaciones y un Muestreo Inteligente de 'Recetas'.
        Busca nodos con propiedades nutritivas para entender la estructura de la Receta.
        """
        try:
            # 1. Labels
            nodes = self.neo4j_manager.execute_query("CALL db.labels()")
            node_labels = [r['label'] for r in nodes] if nodes else []

            # 2. Relaciones
            rels = self.neo4j_manager.execute_query("CALL db.relationshipTypes()")
            rel_types = [r['relationshipType'] for r in rels] if rels else []
            
            # 3. Muestreo Inteligente de RECETAS (Nodes with calories/protein)
            # Esto es vital para que el LLM vea qué propiedades tiene una receta real
            recipe_sample_query = """
            MATCH (n)
            WHERE n.calories IS NOT NULL OR n.protein_g IS NOT NULL
            RETURN labels(n) as labels, keys(n) as keys, n.name as name_example, n.calories as cal_example
            LIMIT 3
            """
            recipe_samples = self.neo4j_manager.execute_query(recipe_sample_query)
            
            # 4. Muestreo de INGREDIENTES (Nodes connected to recipes)
            ingredient_sample_query = """
            MATCH (r)-[:`Has ingredient`|`Contains ingredient`]->(i)
            RETURN labels(i) as labels, i.name as name_example
            LIMIT 3
            """
            ing_samples = self.neo4j_manager.execute_query(ingredient_sample_query)

            schema_desc = f"""
            --- DATABASE SCHEMA ---
            AVAILABLE NODE LABELS: {node_labels}
            AVAILABLE RELATIONSHIPS: {rel_types}
            
            --- RECIPE NODE STRUCTURE (Nodes that have calories/macros) ---
            {json.dumps(recipe_samples[:2], default=str)}
            
            --- INGREDIENT NODE STRUCTURE ---
            {json.dumps(ing_samples[:2], default=str)}
            
            NOTE: Use the keys found above (e.g. 'protein_g', 'calories') strictly.
            """
            return schema_desc
            
        except Exception as e:
            print(f"⚠️ Error esquema: {e}")
            return "Schema unavailable."

    def _route_query(self, query: str) -> str:
        prompt = f"""
        Router for Recipe RAG. Select strategy:
        1. CYPHER: Specific filters (ingredients, calories, distinct counts, names).
        2. VECTOR: Abstract themes (romantic dinner, comfort food).
        
        Query: "{query}"
        Return ONLY: CYPHER or VECTOR.
        """
        res = self.llm.complete(prompt).text.strip().upper()
        return "CYPHER" if "CYPHER" in res else "VECTOR"

    def _generate_cypher(self, query: str) -> str:
        """
        Genera Cypher forzando la estructura de grafo correcta.
        """
        
        prompt = f"""
        Act as a Neo4j Cypher Expert. Generate a query for the user.

        {self.schema_context}

        CRITICAL RULES:
        1. **IDENTIFYING RECIPES**: 
           - To find a Recipe, DO NOT just use `MATCH (n:Entity)`. It's too broad.
           - **BEST PRACTICE**: Use the pattern `MATCH (r)-[:`Has ingredient`]->()` to ensure 'r' is a recipe.
           - Example for "Soup": 
             `MATCH (r)-[:`Has ingredient`]->() WHERE toLower(r.name) CONTAINS 'soup' ...`
        
        2. **RELATIONSHIP SYNTAX**: 
           - Use backticks for spaces: [:`Has ingredient`]
           - Combine types with pipe: [:`Has ingredient`|`Contains ingredient`]
        
        3. **FILTERS & PROPERTIES**:
           - Check 'RECIPE NODE STRUCTURE' above. Use exact keys (e.g. `protein_g`, `calories`).
           - Ensure numerical comparisons use the correct type (usually numbers in DB).
        
        4. **MULTIPLE INGREDIENTS**:
           - Use multiple MATCH clauses for "AND".
           - Ex: `MATCH (r)-[:`Has ingredient`]->(i1), (r)-[:`Has ingredient`]->(i2) WHERE ...`
        
        5. **RICH RETURN**:
           - Return `r.name`, `r.calories`, `r.protein_g` and `collect(distinct i.name)`.
           - ALWAYS return the ingredients list so the user knows what's in it.
        
        User Query: "{query}"
        
        OUTPUT: Only Cypher query.
        """
        response = self.llm.complete(prompt).text.strip()
        return response.replace("```cypher", "").replace("```", "").strip()

    def retrieve(self, query: str) -> Dict[str, Any]:
        strategy = self._route_query(query)
        print(f"🔄 Estrategia: {strategy}")
        
        contexts = []
        cypher_query = ""
        
        if strategy == "CYPHER":
            cypher_query = self._generate_cypher(query)
            print(f"📝 Cypher: {cypher_query}")
            try:
                results = self.neo4j_manager.execute_query(cypher_query)
                if results:
                    contexts.extend([f"DB: {json.dumps(r, default=str)}" for r in results])
                    print(f"✅ Cypher encontró {len(results)} registros.")
                else:
                    print("⚠️ Cypher ejecutó pero dio 0 resultados.")
            except Exception as e:
                print(f"❌ Error Cypher: {e}")

        # Fallback Vectorial
        if not contexts:
            print("🔍 Fallback Vectorial (Cypher vacío o fallido)...")
            nodes = self.vector_retriever.retrieve(query)
            contexts.extend([n.node.text for n in nodes])
            
        return {"contexts": contexts, "strategy": strategy, "cypher": cypher_query}

    def generate_response(self, query: str) -> str:
        retrieval = self.retrieve(query)
        contexts = retrieval["contexts"]
        
        if not contexts:
            return "No encontré recetas con esos criterios en la base de datos."

        prompt = f"""
        Eres un Chef Asistente experto. Usa el contexto para responder.
        
        SI EL CONTEXTO ES DATA DE BASE DE DATOS (JSON):
        - Describe la receta de forma apetitosa.
        - Menciona sus calorías y proteínas si están disponibles.
        - Lista los ingredientes clave.
        
        Query: {query}
        Contexto: {json.dumps(contexts[:15], ensure_ascii=False)}
        Respuesta:
        """
        return self.llm.complete(prompt).text