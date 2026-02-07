"""
Script de ejemplo para enviar eventos a Kafka.
Simula la ingesta masiva de datos para procesamiento de IA.
"""

import json
import time
import uuid
from kafka import KafkaProducer
from kafka.errors import KafkaError
from loguru import logger

from config import settings


class EventProducer:
    """Productor de eventos para Kafka."""
    
    def __init__(self):
        self.producer = None
        
    def connect(self):
        """Establece conexión con Kafka."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks='all',  # Esperar confirmación de todos los brokers
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            logger.info(f"✅ Productor conectado a Kafka: {settings.kafka_bootstrap_servers}")
            
        except KafkaError as e:
            logger.error(f"❌ Error conectando a Kafka: {e}")
            raise
    
    def send_event(self, text: str, task_type: str = "general_analysis", metadata: dict = None):
        """
        Envía un evento a Kafka.
        
        Args:
            text: Texto a procesar
            task_type: Tipo de tarea
            metadata: Metadatos adicionales
        """
        if not self.producer:
            self.connect()
        
        event_id = str(uuid.uuid4())
        
        event_data = {
            "event_id": event_id,
            "text": text,
            "task_type": task_type,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        
        try:
            # Enviar a Kafka
            future = self.producer.send(
                settings.kafka_topic_raw_data,
                value=event_data
            )
            
            # Esperar confirmación
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"✅ Evento enviado: {event_id} "
                f"(topic: {record_metadata.topic}, partition: {record_metadata.partition}, "
                f"offset: {record_metadata.offset})"
            )
            
            return event_id
            
        except KafkaError as e:
            logger.error(f"❌ Error enviando evento: {e}")
            raise
    
    def send_batch(self, events: list):
        """
        Envía múltiples eventos en lote.
        
        Args:
            events: Lista de diccionarios con 'text', 'task_type' y 'metadata'
        """
        event_ids = []
        
        for event in events:
            event_id = self.send_event(
                text=event.get("text"),
                task_type=event.get("task_type", "general_analysis"),
                metadata=event.get("metadata")
            )
            event_ids.append(event_id)
        
        # Flush para asegurar que todos los mensajes se envíen
        self.producer.flush()
        
        logger.info(f"✅ Lote de {len(events)} eventos enviados")
        return event_ids
    
    def close(self):
        """Cierra el productor."""
        if self.producer:
            self.producer.close()
            logger.info("Productor cerrado")


# Ejemplos de uso
def example_sentiment_analysis():
    """Ejemplo: Análisis de sentimientos de reseñas."""
    producer = EventProducer()
    
    reviews = [
        {
            "text": "Este producto es excelente! Superó todas mis expectativas.",
            "task_type": "sentiment_analysis",
            "metadata": {"source": "amazon", "product_id": "12345"}
        },
        {
            "text": "Muy decepcionado con la calidad. No lo recomiendo.",
            "task_type": "sentiment_analysis",
            "metadata": {"source": "amazon", "product_id": "12345"}
        },
        {
            "text": "El producto es aceptable, nada especial.",
            "task_type": "sentiment_analysis",
            "metadata": {"source": "amazon", "product_id": "12345"}
        }
    ]
    
    event_ids = producer.send_batch(reviews)
    logger.info(f"Eventos de análisis de sentimientos enviados: {event_ids}")
    
    producer.close()


def example_summarization():
    """Ejemplo: Resumen de artículos."""
    producer = EventProducer()
    
    article = """
    La inteligencia artificial está transformando la manera en que trabajamos y vivimos.
    Los avances en aprendizaje profundo han permitido desarrollar sistemas que pueden
    procesar lenguaje natural, reconocer imágenes y tomar decisiones complejas.
    Sin embargo, estos avances también plantean desafíos éticos y sociales importantes
    que debemos abordar como sociedad.
    """
    
    event_id = producer.send_event(
        text=article,
        task_type="summarization",
        metadata={"source": "blog", "category": "technology"}
    )
    
    logger.info(f"Evento de resumen enviado: {event_id}")
    producer.close()


def example_batch_processing():
    """Ejemplo: Procesamiento masivo de datos."""
    producer = EventProducer()
    
    # Simular 100 eventos
    events = []
    for i in range(100):
        events.append({
            "text": f"Este es el mensaje número {i} para procesar con IA.",
            "task_type": "general_analysis",
            "metadata": {"batch_id": "batch_001", "index": i}
        })
    
    logger.info("Enviando lote de 100 eventos...")
    event_ids = producer.send_batch(events)
    logger.info(f"✅ {len(event_ids)} eventos enviados exitosamente")
    
    producer.close()


if __name__ == "__main__":
    # Configurar logging
    logger.add(
        "logs/kafka_producer.log",
        rotation="500 MB",
        retention="10 days",
        level="INFO"
    )
    
    print("\n=== AI-EventStream: Kafka Producer Examples ===\n")
    print("1. Análisis de sentimientos")
    print("2. Resumen de textos")
    print("3. Procesamiento masivo (100 eventos)")
    print("4. Salir")
    
    choice = input("\nSelecciona una opción: ")
    
    if choice == "1":
        example_sentiment_analysis()
    elif choice == "2":
        example_summarization()
    elif choice == "3":
        example_batch_processing()
    else:
        print("Saliendo...")
