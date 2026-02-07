"""
Consumidor de Kafka que escucha eventos y dispara tareas de Celery.
Implementa el patrón de desacoplamiento: Kafka → Celery → Redis
"""

import json
import uuid
from typing import Dict, Any
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from loguru import logger

from config import settings
from celery_tasks import process_kafka_event


class KafkaEventConsumer:
    """Consumidor de eventos de Kafka que dispara tareas de procesamiento."""
    
    def __init__(self):
        self.consumer = None
        self.running = False
        
    def connect(self):
        """Establece conexión con Kafka."""
        try:
            self.consumer = KafkaConsumer(
                settings.kafka_topic_raw_data,
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                group_id=settings.kafka_consumer_group,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                max_poll_records=10,  # Procesar en lotes pequeños
            )
            logger.info(f"✅ Conectado a Kafka: {settings.kafka_bootstrap_servers}")
            logger.info(f"Escuchando tópico: {settings.kafka_topic_raw_data}")
            
        except KafkaError as e:
            logger.error(f"❌ Error conectando a Kafka: {e}")
            raise
    
    def start(self):
        """Inicia el consumo de eventos."""
        if not self.consumer:
            self.connect()
        
        self.running = True
        logger.info("🚀 Iniciando consumo de eventos de Kafka...")
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    event_data = message.value
                    
                    # Agregar metadata del mensaje
                    event_data["event_id"] = event_data.get(
                        "event_id",
                        str(uuid.uuid4())
                    )
                    event_data["kafka_metadata"] = {
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "timestamp": message.timestamp,
                    }
                    
                    logger.info(
                        f"📨 Evento recibido: {event_data['event_id']} "
                        f"(partition: {message.partition}, offset: {message.offset})"
                    )
                    
                    # Disparar tarea de Celery de forma asíncrona
                    task = process_kafka_event.apply_async(
                        args=[event_data],
                        task_id=event_data["event_id"]
                    )
                    
                    logger.info(f"✅ Tarea disparada: {task.id}")
                    
                except Exception as e:
                    logger.error(f"❌ Error procesando mensaje: {e}")
                    # Continuar con el siguiente mensaje
                    continue
                    
        except KeyboardInterrupt:
            logger.info("Deteniendo consumidor...")
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el consumidor."""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Consumidor de Kafka cerrado")


def run_consumer():
    """Función principal para ejecutar el consumidor."""
    consumer = KafkaEventConsumer()
    consumer.start()


if __name__ == "__main__":
    # Configurar logging
    logger.add(
        "logs/kafka_consumer.log",
        rotation="500 MB",
        retention="10 days",
        level=settings.log_level
    )
    
    run_consumer()
