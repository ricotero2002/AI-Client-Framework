"""
Tareas de Celery para procesamiento de IA.
Incluye integración con LLMs, embeddings y caché semántica.
"""

import time
from typing import Dict, Any, List, Optional
from celery import Task
from openai import OpenAI
import google.generativeai as genai
from loguru import logger

from celery_app import celery_app
from config import settings
from redis_client import AsyncRedisClient
import asyncio


# Configurar clientes de IA
openai_client = OpenAI(api_key=settings.openai_api_key)

if settings.google_api_key:
    genai.configure(api_key=settings.google_api_key)


class AITask(Task):
    """Clase base para tareas de IA con rate limiting."""
    
    _last_call_time = 0
    _min_interval = 1.0 / (settings.rate_limit_calls / settings.rate_limit_period)
    
    def __call__(self, *args, **kwargs):
        """Rate limiting antes de ejecutar la tarea."""
        current_time = time.time()
        time_since_last_call = current_time - self._last_call_time
        
        if time_since_last_call < self._min_interval:
            sleep_time = self._min_interval - time_since_last_call
            logger.debug(f"Rate limiting: esperando {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self._last_call_time = time.time()
        return super().__call__(*args, **kwargs)


@celery_app.task(
    bind=True,
    base=AITask,
    name="celery_tasks.generate_embedding",
    max_retries=3,
    default_retry_delay=30
)
def generate_embedding(self, text: str) -> List[float]:
    """
    Genera embedding para un texto usando OpenAI.
    
    Args:
        text: Texto para generar embedding
        
    Returns:
        Vector de embedding
    """
    try:
        logger.info(f"Generando embedding para texto de {len(text)} caracteres")
        
        response = openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text
        )
        
        embedding = response.data[0].embedding
        logger.info(f"Embedding generado: dimensión {len(embedding)}")
        
        return embedding
        
    except Exception as e:
        logger.error(f"Error generando embedding: {e}")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=AITask,
    name="celery_tasks.process_with_llm",
    max_retries=3,
    default_retry_delay=60
)
def process_with_llm(
    self,
    text: str,
    task_type: str,
    use_cache: bool = True,
    model: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Procesa texto con LLM, usando caché semántica cuando sea posible.
    
    Args:
        text: Texto a procesar
        task_type: Tipo de tarea (sentiment_analysis, summarization, etc.)
        use_cache: Si debe usar caché semántica
        model: Modelo a usar (por defecto usa el configurado)
        **kwargs: Argumentos adicionales para el LLM
        
    Returns:
        Resultado del procesamiento con metadata
    """
    try:
        start_time = time.time()
        logger.info(f"Procesando tarea tipo '{task_type}' con LLM")
        
        # Generar embedding para búsqueda en caché
        embedding = None
        cached_result = None
        
        if use_cache:
            try:
                # Generar embedding
                embedding = generate_embedding.apply_async(args=[text]).get(timeout=30)
                
                # Buscar en caché semántica
                redis = AsyncRedisClient()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(redis.connect())
                    cached_result = loop.run_until_complete(
                        redis.semantic_cache.search_similar(
                            query_embedding=embedding,
                            task_type=task_type
                        )
                    )
                finally:
                    loop.run_until_complete(redis.disconnect())
                    loop.close()
                
                if cached_result:
                    logger.info("✅ Resultado obtenido de caché semántica")
                    cached_result["processing_time"] = time.time() - start_time
                    return cached_result
                    
            except Exception as e:
                logger.warning(f"Error en caché semántica, continuando con LLM: {e}")
        
        # Si no hay caché, procesar con LLM
        model_to_use = model or settings.openai_model
        
        # Construir prompt según tipo de tarea
        prompt = _build_prompt(text, task_type)
        
        logger.info(f"Llamando a {model_to_use} para procesar")
        
        # Llamar al LLM
        response = openai_client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": _get_system_prompt(task_type)},
                {"role": "user", "content": prompt}
            ],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 1000)
        )
        
        result_text = response.choices[0].message.content
        processing_time = time.time() - start_time
        
        result = {
            "response": result_text,
            "task_type": task_type,
            "model": model_to_use,
            "processing_time": processing_time,
            "from_cache": False,
            "metadata": {
                "tokens_used": response.usage.total_tokens,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }
        }
        
        # Almacenar en caché si se generó embedding
        if use_cache and embedding:
            try:
                redis = AsyncRedisClient()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(redis.connect())
                    loop.run_until_complete(
                        redis.semantic_cache.store(
                            query=text,
                            query_embedding=embedding,
                            response=result_text,
                            task_type=task_type,
                            metadata=result["metadata"]
                        )
                    )
                finally:
                    loop.run_until_complete(redis.disconnect())
                    loop.close()
                    
            except Exception as e:
                logger.warning(f"Error almacenando en caché: {e}")
        
        logger.info(f"✅ Procesamiento completado en {processing_time:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"Error procesando con LLM: {e}")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="celery_tasks.process_kafka_event",
    max_retries=3
)
def process_kafka_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa un evento recibido de Kafka.
    
    Args:
        event_data: Datos del evento de Kafka
        
    Returns:
        Resultado del procesamiento
    """
    try:
        logger.info(f"Procesando evento de Kafka: {event_data.get('event_id', 'unknown')}")
        
        text = event_data.get("text", "")
        task_type = event_data.get("task_type", "general_analysis")
        metadata = event_data.get("metadata", {})
        
        # Delegar a la tarea de procesamiento de LLM
        result = process_with_llm.apply_async(
            args=[text, task_type],
            kwargs={"use_cache": True}
        ).get(timeout=300)
        
        # Agregar metadata del evento
        result["event_metadata"] = metadata
        result["event_id"] = event_data.get("event_id")
        
        # Almacenar resultado en Redis
        redis = AsyncRedisClient()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(redis.connect())
            result_key = f"result:{event_data.get('event_id')}"
            loop.run_until_complete(
                redis.set_json(result_key, result, ex=3600)
            )
        finally:
            loop.run_until_complete(redis.disconnect())
            loop.close()
        
        logger.info(f"✅ Evento procesado y almacenado: {event_data.get('event_id')}")
        return result
        
    except Exception as e:
        logger.error(f"Error procesando evento de Kafka: {e}")
        raise self.retry(exc=e)


@celery_app.task(name="celery_tasks.cleanup_expired_cache")
def cleanup_expired_cache():
    """Tarea periódica para limpiar caché expirada."""
    logger.info("Ejecutando limpieza de caché expirada")
    # Redis maneja la expiración automáticamente con TTL
    # Esta tarea puede usarse para métricas o limpieza adicional
    return {"status": "completed", "message": "Cache cleanup executed"}


def _get_system_prompt(task_type: str) -> str:
    """Retorna el prompt del sistema según el tipo de tarea."""
    prompts = {
        "sentiment_analysis": "Eres un experto en análisis de sentimientos. Analiza el texto y determina si el sentimiento es positivo, negativo o neutral, explicando tu razonamiento.",
        "summarization": "Eres un experto en resumir textos. Crea un resumen conciso y preciso del texto proporcionado.",
        "classification": "Eres un experto en clasificación de textos. Clasifica el texto en las categorías apropiadas.",
        "question_answering": "Eres un asistente útil que responde preguntas basándose en el contexto proporcionado.",
        "general_analysis": "Eres un asistente de IA experto. Analiza el texto y proporciona insights útiles."
    }
    return prompts.get(task_type, prompts["general_analysis"])


def _build_prompt(text: str, task_type: str) -> str:
    """Construye el prompt del usuario según el tipo de tarea."""
    if task_type == "sentiment_analysis":
        return f"Analiza el sentimiento del siguiente texto:\n\n{text}"
    elif task_type == "summarization":
        return f"Resume el siguiente texto:\n\n{text}"
    elif task_type == "classification":
        return f"Clasifica el siguiente texto:\n\n{text}"
    elif task_type == "question_answering":
        return f"Responde la siguiente pregunta:\n\n{text}"
    else:
        return f"Analiza el siguiente texto:\n\n{text}"
