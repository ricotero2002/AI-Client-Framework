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
from datetime import datetime


# Configurar clientes de IA
# openai_client = OpenAI(api_key=settings.openai_api_key) # Deprecated

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


def _generate_embedding(text: str) -> List[float]:
    """
    Función helper síncrona para generar embeddings.
    Usada tanto por la tarea de Celery como directamente por otras tareas.
    """
    try:
        logger.info(f"Generando embedding para texto de {len(text)} caracteres usando Gemini")
        
        # Usar el modelo configurado (ahora gemini-embedding-001)
        model = settings.embedding_model
        if "gemini" not in model and "embedding" not in model:
             model = "models/gemini-embedding-001"
             
        # Llamada a Gemini
        result = genai.embed_content(
            model=model,
            content=text,
            task_type="semantic_similarity" # Default task type
        )
        
        # Extraer embedding
        if 'embedding' in result:
            embedding = result['embedding']
        else:
            # Manejar estructura alternativa si es necesario
            embedding = result
            
        logger.info(f"Embedding generado: dimensión {len(embedding)}")
        return embedding
        
    except Exception as e:
        logger.error(f"Error generando embedding con Gemini: {e}")
        raise e


@celery_app.task(
    bind=True,
    base=AITask,
    name="celery_tasks.generate_embedding",
    max_retries=3,
    default_retry_delay=30
)
def generate_embedding(self, text: str) -> List[float]:
    """Celery task wrapper for embedding generation."""
    try:
        return _generate_embedding(text)
    except Exception as e:
        raise self.retry(exc=e)




async def _update_metrics(
    redis_client: AsyncRedisClient, 
    hit: bool = False, 
    miss: bool = False, 
    processing_time: float = 0.0,
    success: bool = True,
    failure: bool = False
):
    """Helper para actualizar métricas en Redis de forma atómica."""
    try:
        pipeline = redis_client.redis.pipeline()
        
        if hit:
            pipeline.incr("metrics:cache_hits")
        if miss:
            pipeline.incr("metrics:cache_misses")
        if success:
            pipeline.incr("metrics:completed_tasks")
        if failure:
            pipeline.incr("metrics:failed_tasks")
        if processing_time > 0:
            # incrbyfloat es vital para sumar tiempos
            pipeline.incrbyfloat("metrics:total_processing_time", processing_time)
            
        await pipeline.execute()
    except Exception as e:
        logger.error(f"Error actualizando métricas: {e}")


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
                # Generar embedding directamente (sin blocking call a Celery)
                embedding = _generate_embedding(text)
                
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
                    processing_time = time.time() - start_time
                    cached_result["processing_time"] = processing_time
                    
                    # [NUEVO] Actualizar métricas (Hit y Success)
                    try:
                        loop.run_until_complete(
                            _update_metrics(redis, hit=True, success=True, processing_time=processing_time)
                        )
                    except Exception as e:
                        logger.error(f"Error metrics: {e}")
                        
                    return cached_result
                    
            except Exception as e:
                logger.warning(f"Error en caché semántica, continuando con LLM: {e}")
        
        # Si no hay caché, procesar con LLM (Gemini)
        model_to_use = model or settings.gemini_model
        
        # Construir prompt según tipo de tarea
        prompt = _build_prompt(text, task_type)
        system_prompt = _get_system_prompt(task_type)
        
        logger.info(f"Llamando a {model_to_use} (Gemini) para procesar")
        
        # Configurar generación
        generation_config = genai.types.GenerationConfig(
            temperature=kwargs.get("temperature", 0.7),
            max_output_tokens=kwargs.get("max_tokens", 1000)
        )
        
        # Instanciar modelo Gemini
        # Nota: system_instruction está soportado en versiones recientes (>0.3.0)
        gemini_model = genai.GenerativeModel(
            model_name=model_to_use,
            system_instruction=system_prompt
        )
        
        # Llamar al LLM
        response = gemini_model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        result_text = response.text
        processing_time = time.time() - start_time
        
        # Estimación de tokens (Gemini provee usage_metadata en versiones recientes)
        usage = response.usage_metadata
        prompt_tokens = usage.prompt_token_count if usage else 0
        completion_tokens = usage.candidates_token_count if usage else 0
        total_tokens = usage.total_token_count if usage else 0
        
        result = {
            "response": result_text,
            "task_type": task_type,
            "model": model_to_use,
            "processing_time": processing_time,
            "from_cache": False,
            "metadata": {
                "tokens_used": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
        }
        
        # --- GUARDADO Y MÉTRICAS FINALES ---
        
        # Almacenar en caché y actualizar métricas
        try:
            redis_metrics = AsyncRedisClient() # Cliente nuevo para asegurar limpieza
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(redis_metrics.connect())
                
                # 1. Guardar en Semantic Cache (tu código existente)
                if use_cache and embedding:
                    try:
                        loop.run_until_complete(
                            redis_metrics.semantic_cache.store(
                                query=text,
                                query_embedding=embedding,
                                response=result_text,
                                task_type=task_type,
                                metadata=result["metadata"]
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Error almacenando en caché: {e}")

                # 2. [NUEVO] Actualizar métricas (Miss si usamos caché, Success, Tiempo)
                is_miss = use_cache # Si llegamos aquí y usábamos caché, fue un miss
                loop.run_until_complete(
                    _update_metrics(
                        redis_metrics, 
                        miss=is_miss, 
                        success=True, 
                        processing_time=processing_time
                    )
                )

                # 3. [NUEVO] Actualizar estado de tarea en Redis
                task_id = self.request.id
                if task_id:
                    logger.info(f"Actualizando estado de tarea {task_id} a 'completed'")
                    meta_key = f"task_meta:{task_id}"
                    loop.run_until_complete(
                        redis_metrics.set_json(
                            meta_key,
                            {
                                "task_id": task_id,
                                "task_type": task_type,
                                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
                                "completed_at": datetime.utcnow().isoformat(),
                                "status": "completed",
                                "result": result
                            },
                            ex=3600
                        )
                    )
                else:
                    logger.warning("No se pudo obtener task_id de self.request")
                
            finally:
                loop.run_until_complete(redis_metrics.disconnect())
                loop.close()
                
        except Exception as e:
            logger.warning(f"Error en post-procesamiento (caché/métricas): {e}")
        
        logger.info(f"✅ Procesamiento completado en {processing_time:.2f}s")
        return result
        
    except Exception as e:
        # [NUEVO] Capturar métrica de fallo antes de reintentar
        try:
             # Necesitamos un loop efímero solo para registrar el fallo en Redis
             r_fail = AsyncRedisClient()
             l_fail = asyncio.new_event_loop()
             asyncio.set_event_loop(l_fail)
             l_fail.run_until_complete(r_fail.connect())
             l_fail.run_until_complete(_update_metrics(r_fail, failure=True))
             
             # Actualizar estado de fallo en Redis
             task_id = self.request.id
             logger.info(f"Actualizando estado de fallo para task_id: {task_id}")
             if task_id:
                 l_fail.run_until_complete(
                     r_fail.set_json(
                         f"task_meta:{task_id}",
                         {
                             "task_id": task_id,
                             "status": "failed", 
                             "error": str(e),
                             "failed_at": datetime.utcnow().isoformat()
                         },
                         ex=3600
                     )
                 )
             
             l_fail.run_until_complete(r_fail.disconnect())
             l_fail.close()
        except:
            pass # No queremos que falle el retry por culpa de las métricas
            
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
