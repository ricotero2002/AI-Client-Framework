"""
Cliente Redis Asíncrono con soporte para caché semántica.
Implementa búsqueda vectorial usando RedisVL para optimizar costos de LLM.
"""

import asyncio
import json
from typing import Optional, List, Dict, Any
import numpy as np
from redis import asyncio as aioredis
from redis.asyncio import Redis
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.query.filter import Tag
from loguru import logger

from config import settings


class SemanticCache:
    """
    Caché semántica usando búsqueda vectorial en Redis.
    Evita llamadas redundantes a LLMs comparando embeddings.
    """
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.index_name = "semantic_cache_idx"
        self.index: Optional[SearchIndex] = None
        
    async def initialize(self):
        """Inicializa el índice de búsqueda vectorial."""
        try:
            # Definir el schema para el índice vectorial
            schema = {
                "index": {
                    "name": self.index_name,
                    "prefix": "cache:",
                    "storage_type": "hash",
                },
                "fields": [
                    {
                        "name": "query",
                        "type": "text"
                    },
                    {
                        "name": "embedding",
                        "type": "vector",
                        "attrs": {
                            "dims": settings.vector_dimension,
                            "distance_metric": "cosine",
                            "algorithm": "flat",
                        }
                    },
                    {
                        "name": "response",
                        "type": "text"
                    },
                    {
                        "name": "metadata",
                        "type": "text"
                    },
                    {
                        "name": "task_type",
                        "type": "tag"
                    }
                ]
            }
            
            self.index = SearchIndex.from_dict(schema)
            await asyncio.to_thread(self.index.connect, settings.redis_url)
            
            # Crear índice si no existe
            try:
                await asyncio.to_thread(self.index.create, overwrite=False)
                logger.info(f"Índice {self.index_name} creado exitosamente")
            except Exception as e:
                if "Index already exists" in str(e):
                    logger.info(f"Índice {self.index_name} ya existe")
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"Error inicializando caché semántica: {e}")
            raise
    
    async def search_similar(
        self,
        query_embedding: List[float],
        task_type: Optional[str] = None,
        top_k: int = 1,
        threshold: float = None
    ) -> Optional[Dict[str, Any]]:
        """
        Busca consultas similares en el caché.
        
        Args:
            query_embedding: Vector de embedding de la consulta
            task_type: Tipo de tarea para filtrar
            top_k: Número de resultados a retornar
            threshold: Umbral de similitud (usa config por defecto si no se especifica)
            
        Returns:
            Resultado del caché si existe y supera el umbral, None en caso contrario
        """
        if threshold is None:
            threshold = settings.semantic_similarity_threshold
            
        try:
            # Crear query vectorial
            query = VectorQuery(
                vector=query_embedding,
                vector_field_name="embedding",
                return_fields=["query", "response", "metadata", "task_type", "vector_distance"],
                num_results=top_k
            )
            
            # Aplicar filtro por tipo de tarea si se especifica
            if task_type:
                query.set_filter(Tag("task_type") == task_type)
            
            # Ejecutar búsqueda
            results = await asyncio.to_thread(self.index.query, query)
            
            if not results:
                logger.debug("No se encontraron resultados similares en caché")
                return None
            
            # Verificar umbral de similitud
            # La distancia coseno va de 0 (idéntico) a 2 (opuesto)
            # Convertimos a similitud: similarity = 1 - (distance / 2)
            best_result = results[0]
            distance = float(best_result.get("vector_distance", 2.0))
            similarity = 1 - (distance / 2)
            
            logger.debug(f"Mejor similitud encontrada: {similarity:.3f}")
            
            if similarity >= threshold:
                logger.info(f"Cache HIT! Similitud: {similarity:.3f}")
                return {
                    "query": best_result.get("query"),
                    "response": best_result.get("response"),
                    "metadata": json.loads(best_result.get("metadata", "{}")),
                    "similarity": similarity,
                    "from_cache": True
                }
            else:
                logger.debug(f"Similitud {similarity:.3f} por debajo del umbral {threshold}")
                return None
                
        except Exception as e:
            logger.error(f"Error buscando en caché semántica: {e}")
            return None
    
    async def store(
        self,
        query: str,
        query_embedding: List[float],
        response: str,
        task_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Almacena una consulta y su respuesta en el caché.
        
        Args:
            query: Texto de la consulta original
            query_embedding: Vector de embedding de la consulta
            response: Respuesta del LLM
            task_type: Tipo de tarea
            metadata: Metadatos adicionales
            
        Returns:
            True si se almacenó exitosamente, False en caso contrario
        """
        try:
            # Generar ID único
            cache_key = f"cache:{hash(query)}:{task_type}"
            
            # Preparar datos
            data = {
                "query": query,
                "embedding": np.array(query_embedding, dtype=np.float32).tobytes(),
                "response": response,
                "task_type": task_type,
                "metadata": json.dumps(metadata or {})
            }
            
            # Almacenar en Redis con TTL
            await self.redis.hset(cache_key, mapping=data)
            await self.redis.expire(cache_key, settings.cache_ttl)
            
            logger.info(f"Respuesta almacenada en caché: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error almacenando en caché: {e}")
            return False


class AsyncRedisClient:
    """Cliente Redis asíncrono con caché semántica integrada."""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.semantic_cache: Optional[SemanticCache] = None
        
    async def connect(self):
        """Establece conexión con Redis."""
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50
            )
            
            # Verificar conexión
            await self.redis.ping()
            logger.info("✅ Conexión a Redis establecida")
            
            # Inicializar caché semántica
            self.semantic_cache = SemanticCache(self.redis)
            await self.semantic_cache.initialize()
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Redis: {e}")
            raise
    
    async def disconnect(self):
        """Cierra la conexión con Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Conexión a Redis cerrada")
    
    async def get(self, key: str) -> Optional[str]:
        """Obtiene un valor de Redis."""
        return await self.redis.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """Almacena un valor en Redis con TTL opcional."""
        await self.redis.set(key, value, ex=ex)
    
    async def delete(self, key: str):
        """Elimina una clave de Redis."""
        await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Verifica si una clave existe."""
        return await self.redis.exists(key) > 0
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Obtiene un valor JSON de Redis."""
        value = await self.get(key)
        return json.loads(value) if value else None
    
    async def set_json(self, key: str, value: Dict[str, Any], ex: Optional[int] = None):
        """Almacena un valor JSON en Redis."""
        await self.set(key, json.dumps(value), ex=ex)


# Instancia global del cliente Redis
redis_client = AsyncRedisClient()


async def get_redis_client() -> AsyncRedisClient:
    """Dependency injection para FastAPI."""
    return redis_client
