import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Setup paths (Igual que antes)
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
        Obtiene Labels, Relaciones y, CRUCIALMENTE, las PROPIEDADES (Keys) de los nodos.
        """
        try:
            # 1. Labels
            nodes = self.neo4j_manager.execute_query("CALL db.labels()")
            node_labels = [r['label'] for r in nodes] if nodes else []

            # 2. Relaciones
            rels = self.neo4j_manager.execute_query("CALL db.relationshipTypes()")
            rel_types = [r['relationshipType'] for r in rels] if rels else []
            
            # 3. Propiedades de los Nodos (Para evitar el error .Name vs .name)
            # Tomamos una muestra de un nodo 'Entity' y un nodo 'Chunk' (o genérico)
            props_query = """
            MATCH (n)
            WITH labels(n) as lbl, keys(n) as k
            RETURN distinct lbl, k
            LIMIT 5
            """
            props = self.neo4j_manager.execute_query(props_query)
            prop_context = [f"Label: {p['lbl']} -> Properties: {p['k']}" for p in props]

            # 4. Muestreo de datos (Para idioma)
            sample_query = """
            MATCH (n) 
            WHERE n.name IS NOT NULL 
            RETURN n.name as name LIMIT 3
            """
            samples = self.neo4j_manager.execute_query(sample_query)
            sample_data = [s['name'] for s in samples] if samples else []

            schema_desc = f"""
            --- DATABASE SCHEMA ---
            AVAILABLE NODE LABELS: {node_labels}
            AVAILABLE RELATIONSHIPS: {rel_types}
            
            --- NODE PROPERTIES (STRICTLY FOLLOW THESE KEYS) ---
            {prop_context}
            
            --- DATA SAMPLES (Use for Language Detection) ---
            {sample_data}
            """
            return schema_desc
            
        except Exception as e:
            print(f"⚠️ Error esquema: {e}")
            return "Schema unavailable."

    def _route_query(self, query: str) -> str:
        # (El router estaba bien, lo mantenemos igual o simplificado)
        prompt = f"""
        Router for Recipe RAG. Select strategy:
        1. CYPHER: Specific filters (ingredients, calories, distinct counts).
        2. VECTOR: Abstract themes (romantic dinner, comfort food).
        
        Query: "{query}"
        Return ONLY: CYPHER or VECTOR.
        """
        res = self.llm.complete(prompt).text.strip().upper()
        return "CYPHER" if "CYPHER" in res else "VECTOR"

    def _generate_cypher(self, query: str) -> str:
        """
        Genera Cypher priorizando RELACIONES sobre LABELS de nodo para evitar fallos por esquemas sucios.
        """
        
        prompt = f"""
        Act as a Neo4j Cypher Expert. Generate a query for the user.

        {self.schema_context}

        CRITICAL RULES:
        1. **NODE LABELS (SAFETY FIRST)**: 
           - **DO NOT** assume specific labels like `:Chunk`, `:Recipe` or `:Ingredient` unless you see them in the schema samples.
           - **SAFER STRATEGY**: Use generic `(n)` or `(n:Entity)` and rely on the RELATIONSHIP to define the node.
           - Example: Instead of `MATCH (r:Recipe)-[:Has]->(i:Ingredient)`, use `MATCH (r)-[:Has]->(i)`.
        
        2. **RELATIONSHIP SYNTAX**: 
           - Use backticks for spaces: [:`Has ingredient`]
           - Combine types with pipe: [:`Has ingredient`|`Contains ingredient`]
        
        3. **MULTIPLE INGREDIENTS ("AND" LOGIC)**:
           - Use multiple MATCH clauses.
           - Example: 
             MATCH (r)-[:`Has ingredient`]->(i1)
             MATCH (r)-[:`Has ingredient`]->(i2)
             WHERE toLower(i1.name) CONTAINS 'garbanzo' AND toLower(i2.name) CONTAINS 'berenjena'
        
        4. **RICH RETURN**:
           - Return `r.name`, `r.calories`, and `collect(distinct i.name)` (or similar properties found in schema).
           - Do NOT filter strictly by `r.entity_type` unless you are sure.
        
        5. **TRANSLATION**: Translate English/Spanish terms if needed.
        
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
                else:
                    print("⚠️ Cypher ok, pero 0 resultados.")
            except Exception as e:
                print(f"❌ Error Cypher: {e}")

        # Fallback Vectorial
        if not contexts:
            print("🔍 Fallback Vectorial...")
            nodes = self.vector_retriever.retrieve(query)
            contexts.extend([n.node.text for n in nodes])
            
        return {"contexts": contexts, "strategy": strategy, "cypher": cypher_query}

    def generate_response(self, query: str) -> str:
        retrieval = self.retrieve(query)
        contexts = retrieval["contexts"]
        
        if not contexts:
            return "No encontré recetas con esos ingredientes exactos en la base de datos."

        prompt = f"""
        Eres un Chef Asistente. Usa el contexto para responder.
        Query: {query}
        Contexto: {json.dumps(contexts[:15], ensure_ascii=False)}
        Respuesta:
        """
        return self.llm.complete(prompt).text