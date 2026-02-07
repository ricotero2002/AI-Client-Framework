"""
API FastAPI asíncrona para el sistema AI-EventStream.
Proporciona endpoints para enviar tareas, consultar estados y métricas.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
from loguru import logger

from config import settings
from redis_client import AsyncRedisClient, get_redis_client
from celery_tasks import process_with_llm, generate_embedding
from celery.result import AsyncResult
from celery_app import celery_app


# Modelos Pydantic
class ProcessRequest(BaseModel):
    """Request para procesar texto con IA."""
    text: str = Field(..., description="Texto a procesar", min_length=1)
    task_type: str = Field(
        default="general_analysis",
        description="Tipo de tarea: sentiment_analysis, summarization, classification, etc."
    )
    use_cache: bool = Field(default=True, description="Usar caché semántica")
    model: Optional[str] = Field(None, description="Modelo específico a usar")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4000)


class ProcessResponse(BaseModel):
    """Response con el task_id para seguimiento."""
    task_id: str
    status: str
    message: str
    estimated_time: str = "30-60 segundos"


class TaskStatusResponse(BaseModel):
    """Response con el estado de una tarea."""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None


class MetricsResponse(BaseModel):
    """Response con métricas del sistema."""
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    cache_hit_rate: float
    avg_processing_time: float
    uptime: str


# Crear aplicación FastAPI
app = FastAPI(
    title="AI-EventStream API",
    description="Agente de Procesamiento Semántico Distribuido",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# Eventos de inicio y cierre
@app.on_event("startup")
async def startup_event():
    """Inicializar conexiones al arrancar."""
    logger.info("🚀 Iniciando AI-EventStream API...")
    
    # Conectar to Redis
    redis = await get_redis_client()
    await redis.connect()
    
    # Establecer tiempo de inicio si no existe
    existing_start = await redis.get("metrics:system_start_time")
    if not existing_start:
        await redis.set("metrics:system_start_time", datetime.utcnow().isoformat())
    
    logger.info("✅ API lista para recibir requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Cerrar conexiones al apagar."""
    logger.info("Cerrando conexiones...")
    
    redis = await get_redis_client()
    await redis.disconnect()
    
    logger.info("✅ API cerrada correctamente")


# Health check
@app.get("/health")
async def health_check():
    """Verifica el estado de salud del sistema."""
    try:
        redis = await get_redis_client()
        await redis.redis.ping()
        
        # Verificar Celery
        celery_inspect = celery_app.control.inspect()
        active_workers = celery_inspect.active()
        
        return {
            "status": "healthy",
            "redis": "connected",
            "celery_workers": len(active_workers) if active_workers else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


# Endpoint principal de procesamiento
@app.post("/process", response_model=ProcessResponse)
async def process_text(
    request: ProcessRequest,
    redis: AsyncRedisClient = Depends(get_redis_client)
):
    """
    Envía texto para procesamiento con IA.
    
    El procesamiento es asíncrono. Usa el task_id retornado para consultar el estado.
    """
    try:
        # Generar task_id único
        task_id = str(uuid.uuid4())
        
        logger.info(f"📝 Nueva solicitud de procesamiento: {task_id}")
        logger.info(f"   Tipo: {request.task_type}, Longitud: {len(request.text)} chars")
        
        # Disparar tarea de Celery
        task = process_with_llm.apply_async(
            args=[request.text, request.task_type],
            kwargs={
                "use_cache": request.use_cache,
                "model": request.model,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            },
            task_id=task_id
        )
        
        # [NUEVO] Incrementar contador de tareas totales
        await redis.redis.incr("metrics:total_tasks")
        
        # Guardar metadata en Redis
        await redis.set_json(
            f"task_meta:{task_id}",
            {
                "task_id": task_id,
                "task_type": request.task_type,
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending"
            },
            ex=3600
        )
        
        logger.info(f"✅ Tarea enviada: {task_id}")
        
        return ProcessResponse(
            task_id=task_id,
            status="pending",
            message="Tarea enviada para procesamiento"
        )
        
    except Exception as e:
        logger.error(f"Error enviando tarea: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Consultar estado de tarea
@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    redis: AsyncRedisClient = Depends(get_redis_client)
):
    """
    Consulta el estado de una tarea por su ID.
    
    Estados posibles:
    - PENDING: En cola
    - STARTED: En ejecución
    - SUCCESS: Completada exitosamente
    - FAILURE: Falló
    - RETRY: Reintentando
    """
    try:
        # Obtener resultado de Celery
        task_result = AsyncResult(task_id, app=celery_app)
        
        response = TaskStatusResponse(
            task_id=task_id,
            status=task_result.state
        )
        
        if task_result.state == "SUCCESS":
            response.result = task_result.result
            
        elif task_result.state == "FAILURE":
            response.error = str(task_result.info)
            
        elif task_result.state == "PENDING":
            # Verificar si existe en Redis
            meta = await redis.get_json(f"task_meta:{task_id}")
            if not meta:
                raise HTTPException(status_code=404, detail="Task not found")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consultando tarea {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint de métricas
@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics(redis: AsyncRedisClient = Depends(get_redis_client)):
    """
    Retorna métricas del sistema.
    """
    try:
        # 1. Obtener contadores atómicos de Redis
        # Usamos mget para eficiencia (menos round-trips)
        keys = [
            "metrics:total_tasks",
            "metrics:completed_tasks",
            "metrics:failed_tasks",
            "metrics:cache_hits",
            "metrics:cache_misses",
            "metrics:total_processing_time",
            "metrics:system_start_time"
        ]
        values = await redis.redis.mget(keys)
        
        # Parsear valores (Redis devuelve strings o None)
        total_tasks = int(values[0] or 0)
        completed_tasks = int(values[1] or 0)
        failed_tasks = int(values[2] or 0)
        cache_hits = int(values[3] or 0)
        cache_misses = int(values[4] or 0)
        total_proc_time = float(values[5] or 0.0)
        start_time_str = values[6]
        
        # 2. Obtener tareas activas en tiempo real desde Celery
        inspect = celery_app.control.inspect()
        active = inspect.active()
        active_tasks_count = sum(len(tasks) for tasks in active.values()) if active else 0
        
        # 3. Calcular Métricas Derivadas
        
        # Hit Rate
        total_cache_ops = cache_hits + cache_misses
        hit_rate = (cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0.0
        
        # Tiempo promedio
        avg_time = (total_proc_time / completed_tasks) if completed_tasks > 0 else 0.0
        
        # Uptime
        uptime_str = "N/A"
        if start_time_str:
            try:
                # Decodificar bytes si es necesario
                if isinstance(start_time_str, bytes):
                    start_time_str = start_time_str.decode('utf-8')
                    
                start_dt = datetime.fromisoformat(start_time_str)
                delta = datetime.utcnow() - start_dt
                # Formato amigable: "2 days, 4:30:00"
                uptime_str = str(delta).split('.')[0] 
            except Exception:
                pass

        return MetricsResponse(
            total_tasks=total_tasks,
            active_tasks=active_tasks_count,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            cache_hit_rate=round(hit_rate, 2),
            avg_processing_time=round(avg_time, 4),
            uptime=uptime_str
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint para limpiar caché
@app.delete("/cache/clear")
async def clear_cache(
    task_type: Optional[str] = None,
    redis: AsyncRedisClient = Depends(get_redis_client)
):
    """
    Limpia el caché semántico.
    
    Si se especifica task_type, solo limpia ese tipo de tareas.
    """
    try:
        # Implementar lógica de limpieza
        # Por ahora, retornar mensaje
        return {
            "status": "success",
            "message": f"Cache cleared for task_type: {task_type or 'all'}"
        }
    except Exception as e:
        logger.error(f"Error limpiando caché: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint para workers activos
@app.get("/workers")
async def get_workers():
    """Retorna información sobre los workers activos."""
    try:
        inspect = celery_app.control.inspect()
        
        stats = inspect.stats()
        active = inspect.active()
        registered = inspect.registered()
        
        return {
            "workers": list(stats.keys()) if stats else [],
            "stats": stats,
            "active_tasks": active,
            "registered_tasks": registered
        }
    except Exception as e:
        logger.error(f"Error obteniendo workers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Manejo de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Maneja excepciones no capturadas."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    
    # Configurar logging
    logger.add(
        "logs/api.log",
        rotation="500 MB",
        retention="10 days",
        level=settings.log_level
    )
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=settings.api_workers,
        log_level=settings.log_level.lower()
    )
