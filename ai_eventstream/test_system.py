"""
Tests para el sistema AI-EventStream.
Incluye tests unitarios y de integración.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json

from config import settings
from redis_client import AsyncRedisClient, SemanticCache


class TestAsyncRedisClient:
    """Tests para el cliente Redis asíncrono."""
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Test de conexión a Redis."""
        client = AsyncRedisClient()
        
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_instance = AsyncMock()
            mock_redis.return_value = mock_instance
            
            await client.connect()
            
            assert client.redis is not None
            mock_instance.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_get(self):
        """Test de operaciones básicas set/get."""
        client = AsyncRedisClient()
        client.redis = AsyncMock()
        
        # Test set
        await client.set("test_key", "test_value")
        client.redis.set.assert_called_once_with("test_key", "test_value", ex=None)
        
        # Test get
        client.redis.get.return_value = "test_value"
        value = await client.get("test_key")
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_json_operations(self):
        """Test de operaciones JSON."""
        client = AsyncRedisClient()
        client.redis = AsyncMock()
        
        test_data = {"key": "value", "number": 42}
        
        # Test set_json
        await client.set_json("test_json", test_data)
        client.redis.set.assert_called_once()
        
        # Test get_json
        client.redis.get.return_value = json.dumps(test_data)
        result = await client.get_json("test_json")
        assert result == test_data


class TestSemanticCache:
    """Tests para la caché semántica."""
    
    @pytest.mark.asyncio
    async def test_store(self):
        """Test de almacenamiento en caché."""
        redis_mock = AsyncMock()
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


class TestCeleryTasks:
    """Tests para las tareas de Celery."""
    
    @patch('celery_tasks.openai_client')
    def test_generate_embedding(self, mock_openai):
        """Test de generación de embeddings."""
        from celery_tasks import generate_embedding
        
        # Mock de respuesta de OpenAI
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_openai.embeddings.create.return_value = mock_response
        
        # Ejecutar tarea
        result = generate_embedding("test text")
        
        assert len(result) == 1536
        mock_openai.embeddings.create.assert_called_once()
    
    @patch('celery_tasks.openai_client')
    def test_process_with_llm(self, mock_openai):
        """Test de procesamiento con LLM."""
        from celery_tasks import process_with_llm
        
        # Mock de respuesta de OpenAI
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_response.usage = Mock(
            total_tokens=100,
            prompt_tokens=50,
            completion_tokens=50
        )
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Ejecutar tarea (sin caché para simplificar)
        result = process_with_llm.apply(
            args=["Test text", "general_analysis"],
            kwargs={"use_cache": False}
        ).get()
        
        assert result["response"] == "Test response"
        assert result["from_cache"] is False
        assert result["metadata"]["tokens_used"] == 100


class TestAPI:
    """Tests para la API FastAPI."""
    
    @pytest.fixture
    def client(self):
        """Fixture para el cliente de test."""
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test del endpoint de health check."""
        with patch('main.get_redis_client') as mock_redis:
            mock_instance = AsyncMock()
            mock_redis.return_value = mock_instance
            
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
    
    def test_process_endpoint(self, client):
        """Test del endpoint de procesamiento."""
        with patch('main.process_with_llm') as mock_task:
            mock_task.apply_async.return_value = Mock(id="test-task-id")
            
            payload = {
                "text": "Test text",
                "task_type": "sentiment_analysis"
            }
            
            response = client.post("/process", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "pending"


class TestKafkaConsumer:
    """Tests para el consumidor de Kafka."""
    
    @patch('kafka_consumer.KafkaConsumer')
    def test_consumer_connect(self, mock_kafka):
        """Test de conexión del consumidor."""
        from kafka_consumer import KafkaEventConsumer
        
        consumer = KafkaEventConsumer()
        consumer.connect()
        
        mock_kafka.assert_called_once()
        assert consumer.consumer is not None
    
    @patch('kafka_consumer.process_kafka_event')
    @patch('kafka_consumer.KafkaConsumer')
    def test_consumer_process_message(self, mock_kafka, mock_task):
        """Test de procesamiento de mensajes."""
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
