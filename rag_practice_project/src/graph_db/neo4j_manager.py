"""
Neo4j Manager - Gestión de conexión y graph store

Maneja la conexión a Neo4j Aura y proporciona utilidades para
interactuar con el grafo de conocimiento.
"""
import sys
from pathlib import Path

# Setup paths para que funcione ejecutando desde cualquier lugar
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from typing import Optional, Dict, Any
from neo4j import GraphDatabase
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from rag_config.config import (
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    NEO4J_DATABASE
)


class Neo4jManager:
    """
    Administrador de conexiones Neo4j y operaciones básicas del grafo
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None
    ):
        """
        Inicializa el Neo4j Manager
        
        Args:
            uri: URI de Neo4j (ej: neo4j+s://xxx.databases.neo4j.io)
            username: Usuario de Neo4j
            password: Contraseña de Neo4j
            database: Nombre de la base de datos
        """
        self.uri = uri or NEO4J_URI
        self.username = username or NEO4J_USERNAME
        self.password = password or NEO4J_PASSWORD
        self.database = database or NEO4J_DATABASE
        # Validar credenciales
        if not self.password:
            raise ValueError(
                "Neo4j password no configurado. "
                "Agrega NEO4J_PASSWORD a tu archivo .env"
            )
        
        self._driver = None
        self._graph_store = None
    
    @property
    def driver(self):
        """Lazy loading del driver de Neo4j"""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
        return self._driver
    
    @property
    def graph_store(self) -> Neo4jPropertyGraphStore:
        """Lazy loading del LlamaIndex Neo4j Property Graph Store"""
        if self._graph_store is None:
            self._graph_store = Neo4jPropertyGraphStore(
                username=self.username,
                password=self.password,
                url=self.uri,
                database=self.database
            )
        return self._graph_store
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión a Neo4j
        
        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS num")
                record = result.single()
                if record and record["num"] == 1:
                    print(f"✓ Conexión exitosa a Neo4j Aura: {self.uri}")
                    return True
        except Exception as e:
            print(f"✗ Error conectando a Neo4j: {e}")
            return False
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del grafo
        
        Returns:
            Diccionario con estadísticas del grafo
        """
        stats = {
            "uri": self.uri,
            "database": self.database,
            "node_count": 0,
            "relationship_count": 0,
            "labels": [],
            "relationship_types": []
        }
        
        try:
            with self.driver.session(database=self.database) as session:
                # Contar nodos
                result = session.run("MATCH (n) RETURN count(n) AS count")
                stats["node_count"] = result.single()["count"]
                
                # Contar relaciones
                result = session.run("MATCH ()-[r]->() RETURN count(r) AS count")
                stats["relationship_count"] = result.single()["count"]
                
                # Obtener labels
                result = session.run("CALL db.labels()")
                stats["labels"] = [record["label"] for record in result]
                
                # Obtener tipos de relaciones
                result = session.run("CALL db.relationshipTypes()")
                stats["relationship_types"] = [
                    record["relationshipType"] for record in result
                ]
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
        
        return stats
    
    def clear_database(self, confirm: bool = False):
        """
        Limpia completamente la base de datos (CUIDADO!)
        
        Args:
            confirm: Debe ser True para ejecutar (seguridad)
        """
        if not confirm:
            print("⚠️  Para limpiar la base de datos, pasa confirm=True")
            return
        
        try:
            with self.driver.session(database=self.database) as session:
                # Eliminar todas las relaciones y nodos
                session.run("MATCH (n) DETACH DELETE n")
                print("✓ Base de datos limpiada")
        except Exception as e:
            print(f"Error limpiando base de datos: {e}")
    
    def execute_query(self, query: str, parameters: dict = None):
        """
        Ejecuta una query Cypher y retorna los resultados
        
        Args:
            query: Query Cypher a ejecutar
            parameters: Parámetros opcionales para la query
            
        Returns:
            Lista de registros (dicts) con los resultados
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                # Convertir records a dicts
                return [record.data() for record in result]
        except Exception as e:
            print(f"Error ejecutando query: {e}")
            raise
    
    def close(self):
        """Cierra la conexión a Neo4j"""
        if self._driver:
            self._driver.close()
            self._driver = None
            print("✓ Conexión a Neo4j cerrada")


def test_neo4j_connection():
    """Función de utilidad para probar la conexión"""
    manager = Neo4jManager()
    if manager.test_connection():
        stats = manager.get_statistics()
        print(f"\nEstadísticas del grafo:")
        print(f"  - Nodos: {stats['node_count']}")
        print(f"  - Relaciones: {stats['relationship_count']}")
        print(f"  - Labels: {stats['labels']}")
        print(f"  - Tipos de relaciones: {stats['relationship_types']}")
    manager.close()


if __name__ == "__main__":
    test_neo4j_connection()
