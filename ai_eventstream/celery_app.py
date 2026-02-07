"""
Configuración de Celery para procesamiento distribuido de tareas de IA.
Optimizado para tareas pesadas con rate limiting y reinicio automático.
"""

from celery import Celery
from kombu import Queue, Exchange
from config import settings

# Crear instancia de Celery
celery_app = Celery(
    "ai_eventstream",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["celery_tasks"]
)

# Configuración de Celery
celery_app.conf.update(
    # Serialización
    task_serializer=settings.celery_task_serializer,
    result_serializer=settings.celery_result_serializer,
    accept_content=settings.celery_accept_content,
    
    # Timezone
    timezone=settings.celery_timezone,
    enable_utc=settings.celery_enable_utc,
    
    # Optimización para tareas de IA pesadas
    worker_prefetch_multiplier=settings.worker_prefetch_multiplier,  # 1 tarea a la vez
    task_acks_late=True,  # Confirmar después de completar
    worker_max_tasks_per_child=settings.worker_max_tasks_per_child,  # Reiniciar después de N tareas
    
    # Timeouts
    task_soft_time_limit=300,  # 5 minutos soft limit
    task_time_limit=600,  # 10 minutos hard limit
    
    # Resultados
    result_expires=3600,  # Los resultados expiran en 1 hora
    result_extended=True,
    
    # Retry policy
    task_default_retry_delay=60,  # Reintentar después de 1 minuto
    task_max_retries=3,
    
    # Queues
    task_default_queue="default",
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("ai_processing", Exchange("ai_processing"), routing_key="ai.#"),
        Queue("kafka_events", Exchange("kafka_events"), routing_key="kafka.#"),
    ),
    
    # Routing
    task_routes={
        "celery_tasks.process_with_llm": {"queue": "ai_processing", "routing_key": "ai.llm"},
        "celery_tasks.process_kafka_event": {"queue": "kafka_events", "routing_key": "kafka.event"},
        "celery_tasks.generate_embedding": {"queue": "ai_processing", "routing_key": "ai.embedding"},
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Configuración de beat (tareas periódicas) - opcional
celery_app.conf.beat_schedule = {
    "cleanup-expired-cache": {
        "task": "celery_tasks.cleanup_expired_cache",
        "schedule": 3600.0,  # Cada hora
    },
}

if __name__ == "__main__":
    celery_app.start()
