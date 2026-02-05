"""
Configuración centralizada del proyecto AI-EventStream.
Carga variables de entorno y proporciona configuración para todos los componentes.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración principal de la aplicación."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_raw_data: str = "datos_crudos"
    kafka_topic_processed: str = "datos_procesados"
    kafka_consumer_group: str = "ai_eventstream_consumers"
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Gemini Configuration (opcional)
    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-exp"
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: list = ["json"]
    celery_timezone: str = "America/Argentina/Buenos_Aires"
    celery_enable_utc: bool = True
    
    # Worker Configuration
    worker_prefetch_multiplier: int = 1
    worker_max_tasks_per_child: int = 100
    worker_concurrency: int = 4
    
    # Semantic Cache Configuration
    semantic_similarity_threshold: float = 0.85
    cache_ttl: int = 3600
    vector_dimension: int = 1536
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    api_workers: int = 1
    
    # Flower Configuration
    flower_port: int = 5555
    flower_basic_auth: str = "admin:admin123"
    
    # Application Configuration
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = True
    
    # Rate Limiting
    rate_limit_calls: int = 60
    rate_limit_period: int = 60
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    @property
    def is_production(self) -> bool:
        """Verifica si está en modo producción."""
        return self.environment.lower() == "production"
    
    @property
    def redis_connection_kwargs(self) -> dict:
        """Retorna kwargs para conexión Redis."""
        kwargs = {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "decode_responses": True,
        }
        if self.redis_password:
            kwargs["password"] = self.redis_password
        return kwargs
    
    @property
    def kafka_config(self) -> dict:
        """Retorna configuración para Kafka."""
        return {
            "bootstrap_servers": self.kafka_bootstrap_servers.split(","),
            "group_id": self.kafka_consumer_group,
        }


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instancia singleton de Settings.
    Usa lru_cache para evitar recargar el archivo .env múltiples veces.
    """
    return Settings()


# Instancia global de configuración
settings = get_settings()
