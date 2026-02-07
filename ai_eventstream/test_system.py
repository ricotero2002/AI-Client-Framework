"""
Tests para el sistema AI-EventStream.
Incluye tests unitarios y de integración para garantizar el funcionamiento correcto
de los componentes de Redis, manejo de caché, tareas de Celery (IA) y endpoints de API.

Este archivo ha sido actualizado para corregir problemas de mocks asíncronos y configurar
correctamente las dependencias de FastAPI para los tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json

from config import settings
from redis_client import AsyncRedisClient, SemanticCache

# ==============================================================================
# TESTS REDIS CLIENT
# ==============================================================================
class TestAsyncRedisClient:
    """
    Tests para el cliente Redis asíncrono.
    Verifica que la conexión, operaciones básicas y manejo de JSON funcionen correctamente.
    """
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """
        Test de conexión a Redis (test_connect).
        
        Objetivo:
            Verificar que client.connect() llama correctamente a redis.asyncio.from_url.
            
        Corrección:
            Se configura mock_redis como AsyncMock para soportar 'await from_url(...)'.
            El valor de retorno (el cliente) es un MagicMock con métodos AsyncMock (ping).
            ADEMÁS: Se mockea 'redis_client.SearchIndex' para evitar que SemanticCache intente
            conectarse realmente a Redis vía redisvl.
        """
        client = AsyncRedisClient()
        
        # 'redis.asyncio.from_url' debe ser esperable (awaitable)
        with patch('redis.asyncio.from_url', new_callable=AsyncMock) as mock_from_url, \
             patch('redis_client.SearchIndex') as mock_search_index:
            
            # Mockear la instancia de SearchIndex y su método connect
            mock_index_instance = Mock()
            # connect es síncrono en redisvl pero se llama con asyncio.to_thread
            mock_index_instance.connect = Mock()
            mock_index_instance.create = Mock()
            mock_search_index.from_dict.return_value = mock_index_instance
            
            # El objeto cliente que retorna NO se espera (no se hace await sobre él),
            # pero sus métodos sí.
            mock_client_instance = MagicMock()
            mock_client_instance.ping = AsyncMock()
            
            mock_from_url.return_value = mock_client_instance
            
            await client.connect()
            
            assert client.redis is not None
            mock_client_instance.ping.assert_called_once()
            # Verificar que se inicializó el índice
            mock_search_index.from_dict.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_get(self):
        """
        Test de operaciones básicas set/get.
        """
        client = AsyncRedisClient()
        # Mockear client.redis con un MagicMock que tenga métodos AsyncMock
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock()
        client.redis = mock_redis
        
        # Test set
        await client.set("test_key", "test_value")
        client.redis.set.assert_called_once_with("test_key", "test_value", ex=None)
        
        # Test get
        client.redis.get.return_value = "test_value"
        value = await client.get("test_key")
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_json_operations(self):
        """
        Test de operaciones JSON.
        """
        client = AsyncRedisClient()
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock()
        client.redis = mock_redis
        
        test_data = {"key": "value", "number": 42}
        
        # Test set_json
        await client.set_json("test_json", test_data)
        client.redis.set.assert_called_once()
        
        # Test get_json
        client.redis.get.return_value = json.dumps(test_data)
        result = await client.get_json("test_json")
        assert result == test_data


# ==============================================================================
# TESTS SEMANTIC CACHE
# ==============================================================================
class TestSemanticCache:
    """
    Tests para la caché semántica.
    """
    
    @pytest.mark.asyncio
    async def test_store(self):
        """
        Test de almacenamiento en caché.
        """
        # redis_client debe ser un Mock cuyos métodos asíncronos (hset, expire) sean AsyncMock
        redis_mock = MagicMock()
        redis_mock.hset = AsyncMock()
        redis_mock.expire = AsyncMock()
        
        cache = SemanticCache(redis_mock)
        
        query = "¿Cuál es el mejor lenguaje de programación?"
        embedding = [0.1] * 1536
        response = "Python es considerado uno de los mejores..."
        
        result = await cache.store(
            query=query,
            query_embedding=embedding,
            response=response,
            task_type="question_answering"
        )
        
        assert result is True
        redis_mock.hset.assert_called_once()
        redis_mock.expire.assert_called_once()


# ==============================================================================
# TESTS CELERY TASKS (IA - GEMINI)
# ==============================================================================
class TestCeleryTasks:
    """
    Tests para las tareas de Celery.
    """
    
    @patch('celery_tasks.genai')
    def test_generate_embedding(self, mock_genai):
        """
        Test de generación de embeddings con Gemini.
        """
        from celery_tasks import generate_embedding
        
        # Mock de genai.embed_content
        mock_genai.embed_content.return_value = {
            'embedding': [0.1] * 1536
        }
        
        # Ejecutar tarea (síncronamente para el test)
        result = generate_embedding("test text")
        
        assert len(result) == 1536
        mock_genai.embed_content.assert_called_once()
    
    @patch('celery_tasks.genai')
    def test_process_with_llm(self, mock_genai):
        """
        Test de procesamiento con LLM Gemini.
        """
        from celery_tasks import process_with_llm
        
        # Mock del modelo y respuesta
        mock_model_instance = Mock()
        mock_response = Mock()
        mock_response.text = "Test response form Gemini"
        mock_response.usage_metadata = Mock(
            total_token_count=100,
            prompt_token_count=50,
            candidates_token_count=50
        )
        
        mock_model_instance.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model_instance
        
        # Mock de generate_embedding.apply_async para evitar llamadas reales si use_cache=True (aunque aquí usamos False)
        with patch('celery_tasks.generate_embedding.apply_async'):
            # Instanciamos la tarea directamente para probar su método 'run' (call) o usamos apply()
            # process_with_llm es un objeto Task. Su método __call__ ejecuta la lógica.
            
            # Nota: .apply() ejecuta la tarea localmente
            result = process_with_llm.apply(
                args=["Test text", "general_analysis"],
                kwargs={"use_cache": False}
            ).get()
        
        assert result["response"] == "Test response form Gemini"
        assert result["from_cache"] is False
        assert result["metadata"]["tokens_used"] == 100
        
        mock_genai.GenerativeModel.assert_called_once()


# ==============================================================================
# TESTS API (FASTAPI)
# ==============================================================================
class TestAPI:
    """
    Tests para la API FastAPI.
    """
    
    @pytest.fixture
    def app_client(self):
        """
        Fixture que crea el TestClient y configura overrides de dependencias.
        Esta es la clave para evitar errores 500 por conexión fallida a Redis.
        """
        from main import app, get_redis_client
        from fastapi.testclient import TestClient
        
        # Crear un mock del cliente Redis completo
        mock_redis_client = AsyncMock(spec=AsyncRedisClient)
        # Configurar método set_json para que sea awaitable
        mock_redis_client.set_json = AsyncMock()
        mock_redis_client.get_json = AsyncMock(return_value=None)
        
        # IMPORTANTE: Configurar .redis para que no sea None y tenga ping()
        mock_redis_client.redis = AsyncMock()
        mock_redis_client.redis.ping = AsyncMock(return_value=True)
        
        # IMPORTANTE: Sobreescribir la dependencia get_redis_client para FastAPI Depends
        app.dependency_overrides[get_redis_client] = lambda: mock_redis_client
        
        # ADEMÁS: Parchear la instancia global 'redis_client' en el módulo 'redis_client'
        # Esto es necesario porque el endpoint /health llama a get_redis_client() directamente,
        # sin usar Depends(), por lo que el override de FastAPI no aplica allí.
        with patch('redis_client.redis_client', mock_redis_client), \
             patch('main.startup_event', new_callable=AsyncMock), \
             patch('main.shutdown_event', new_callable=AsyncMock):
            
            client = TestClient(app)
            yield client
            
        # Limpiar overrides
        app.dependency_overrides = {}
    
    def test_health_check(self, app_client):
        """
        Test del endpoint de health check (GET /health).
        Este test debe pasar ahora que Redis está mockeado via dependency_overrides.
        """
        # Nota: app_client ya tiene el override hecho en el fixture.
        # Pero el health_check llama a get_redis_client() dentro.
        # Además llama a celery_app.control.inspect().
        
        with patch('celery_app.celery_app.control.inspect') as mock_inspect:
            mock_inspect.return_value.active.return_value = {}
            
            # También necesitamos asegurar que el mock de redis inyectado funcione
            # El fixture app_client ya lo hizo, pero necesitamos acceder al mock para verificar si queremos.
            # Simplemente llamamos al endpoint.
            
            response = app_client.get("/health")
            
            # Si falla con 500, imprimimos el error
            if response.status_code != 200:
                print(f"Health check failed: {response.json()}")
                
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
    
    def test_process_endpoint(self, app_client):
        """
        Test del endpoint de procesamiento (POST /process).
        """
        with patch('main.process_with_llm') as mock_task:
            mock_task.apply_async.return_value = Mock(id="test-task-id")
            
            payload = {
                "text": "Test text",
                "task_type": "sentiment_analysis"
            }
            
            response = app_client.post("/process", json=payload)
            
            if response.status_code != 200:
                print(f"Process endpoint failed: {response.json()}")
                
            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "pending"


# ==============================================================================
# TESTS KAFKA CONSUMER
# ==============================================================================
class TestKafkaConsumer:
    """
    Tests para el consumidor de Kafka.
    """
    
    @patch('kafka_consumer.KafkaConsumer')
    def test_consumer_connect(self, mock_kafka):
        """
        Test de conexión del consumidor.
        """
        from kafka_consumer import KafkaEventConsumer
        
        consumer = KafkaEventConsumer()
        consumer.connect()
        
        mock_kafka.assert_called_once()
        assert consumer.consumer is not None
    
    @patch('kafka_consumer.process_kafka_event')
    @patch('kafka_consumer.KafkaConsumer')
    def test_consumer_process_message(self, mock_kafka, mock_task):
        """
        Test de procesamiento de mensajes.
        """
        from kafka_consumer import KafkaEventConsumer
        
        # Mock de mensaje de Kafka
        mock_message = Mock()
        mock_message.value = {
            "text": "Test event",
            "task_type": "general_analysis"
        }
        mock_message.topic = "test_topic"
        mock_message.partition = 0
        mock_message.offset = 123
        mock_message.timestamp = 1234567890
        
        # Mock del consumidor
        mock_kafka_instance = Mock()
        mock_kafka_instance.__iter__ = Mock(return_value=iter([mock_message]))
        mock_kafka.return_value = mock_kafka_instance
        
        consumer = KafkaEventConsumer()
        consumer.consumer = mock_kafka_instance
        consumer.running = False  # Para que solo procese un mensaje
        
        # Ejecutar
        consumer.start()
        
        # Verificar que se disparó la tarea
        mock_task.apply_async.assert_called_once()


# Configuración de pytest
def pytest_configure(config):
    """Configuración de pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=.", "--cov-report=html"])
