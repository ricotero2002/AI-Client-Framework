"""
Cliente de ejemplo para interactuar con la API de AI-EventStream.
Demuestra cómo enviar tareas y consultar resultados.
"""

import requests
import time
import json
from typing import Dict, Any, Optional
from loguru import logger


class AIEventStreamClient:
    """Cliente para interactuar con la API de AI-EventStream."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def health_check(self) -> Dict[str, Any]:
        """Verifica el estado de salud del sistema."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def process_text(
        self,
        text: str,
        task_type: str = "general_analysis",
        use_cache: bool = True,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Envía texto para procesamiento.
        
        Returns:
            task_id para consultar el resultado
        """
        payload = {
            "text": text,
            "task_type": task_type,
            "use_cache": use_cache,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if model:
            payload["model"] = model
        
        response = self.session.post(
            f"{self.base_url}/process",
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        return result["task_id"]
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Consulta el estado de una tarea."""
        response = self.session.get(f"{self.base_url}/task/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def wait_for_result(
        self,
        task_id: str,
        timeout: int = 120,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """
        Espera a que una tarea se complete y retorna el resultado.
        
        Args:
            task_id: ID de la tarea
            timeout: Tiempo máximo de espera en segundos
            poll_interval: Intervalo entre consultas en segundos
            
        Returns:
            Resultado de la tarea
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)
            
            if status["status"] == "SUCCESS":
                return status["result"]
            elif status["status"] == "FAILURE":
                raise Exception(f"Task failed: {status.get('error')}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del sistema."""
        response = self.session.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.json()
    
    def get_workers(self) -> Dict[str, Any]:
        """Obtiene información sobre workers activos."""
        response = self.session.get(f"{self.base_url}/workers")
        response.raise_for_status()
        return response.json()


# Ejemplos de uso
def example_sentiment_analysis():
    """Ejemplo: Análisis de sentimientos."""
    client = AIEventStreamClient()
    
    # Verificar salud del sistema
    health = client.health_check()
    logger.info(f"Sistema: {health}")
    
    # Enviar texto para análisis
    text = "Este producto es absolutamente increíble! La mejor compra que he hecho."
    
    logger.info(f"Enviando texto para análisis de sentimientos...")
    task_id = client.process_text(
        text=text,
        task_type="sentiment_analysis",
        use_cache=True
    )
    
    logger.info(f"Task ID: {task_id}")
    logger.info("Esperando resultado...")
    
    # Esperar resultado
    result = client.wait_for_result(task_id)
    
    logger.info("\n=== RESULTADO ===")
    logger.info(f"Respuesta: {result['response']}")
    logger.info(f"Modelo: {result['model']}")
    logger.info(f"Tiempo de procesamiento: {result['processing_time']:.2f}s")
    logger.info(f"Desde caché: {result['from_cache']}")
    logger.info(f"Tokens usados: {result['metadata']['tokens_used']}")


def example_summarization():
    """Ejemplo: Resumen de texto."""
    client = AIEventStreamClient()
    
    article = """
    La inteligencia artificial generativa ha experimentado un crecimiento exponencial
    en los últimos años. Modelos como GPT-4, Claude y Gemini han demostrado capacidades
    impresionantes en tareas de procesamiento de lenguaje natural, generación de código
    y razonamiento complejo. Estas tecnologías están transformando industrias enteras,
    desde el desarrollo de software hasta la creación de contenido y el servicio al cliente.
    Sin embargo, también plantean desafíos importantes en términos de ética, privacidad
    y el futuro del trabajo. Es crucial que como sociedad desarrollemos marcos regulatorios
    y éticos apropiados para guiar el desarrollo y uso de estas poderosas herramientas.
    """
    
    logger.info("Enviando artículo para resumen...")
    task_id = client.process_text(
        text=article,
        task_type="summarization",
        temperature=0.3,  # Más determinístico para resúmenes
        max_tokens=200
    )
    
    result = client.wait_for_result(task_id)
    
    logger.info("\n=== RESUMEN ===")
    logger.info(result['response'])


def example_cache_demonstration():
    """Ejemplo: Demostración de caché semántica."""
    client = AIEventStreamClient()
    
    # Primera consulta
    text1 = "¿Cuál es el mejor lenguaje de programación para IA?"
    
    logger.info("Primera consulta (sin caché)...")
    task_id1 = client.process_text(text=text1, task_type="question_answering")
    result1 = client.wait_for_result(task_id1)
    
    logger.info(f"Tiempo: {result1['processing_time']:.2f}s")
    logger.info(f"Desde caché: {result1['from_cache']}")
    
    # Segunda consulta similar (debería usar caché)
    text2 = "¿Qué lenguaje de programación es mejor para inteligencia artificial?"
    
    logger.info("\nSegunda consulta similar (debería usar caché)...")
    task_id2 = client.process_text(text=text2, task_type="question_answering")
    result2 = client.wait_for_result(task_id2)
    
    logger.info(f"Tiempo: {result2['processing_time']:.2f}s")
    logger.info(f"Desde caché: {result2['from_cache']}")
    
    if result2['from_cache']:
        logger.info("✅ ¡Caché semántica funcionando! Respuesta instantánea.")
        logger.info(f"Similitud: {result2.get('similarity', 'N/A')}")


def example_batch_processing():
    """Ejemplo: Procesamiento en lote."""
    client = AIEventStreamClient()
    
    texts = [
        "Este servicio es excelente, muy recomendado.",
        "Terrible experiencia, no volvería a usar esto.",
        "Es aceptable, nada extraordinario.",
        "¡Increíble! Superó todas mis expectativas.",
        "No cumplió con lo prometido, decepcionante."
    ]
    
    logger.info(f"Enviando {len(texts)} textos para procesamiento...")
    
    task_ids = []
    for i, text in enumerate(texts, 1):
        task_id = client.process_text(
            text=text,
            task_type="sentiment_analysis"
        )
        task_ids.append(task_id)
        logger.info(f"  {i}. Task ID: {task_id}")
    
    logger.info("\nEsperando resultados...")
    
    results = []
    for task_id in task_ids:
        result = client.wait_for_result(task_id)
        results.append(result)
    
    logger.info("\n=== RESULTADOS ===")
    for i, result in enumerate(results, 1):
        logger.info(f"\n{i}. {texts[i-1][:50]}...")
        logger.info(f"   Análisis: {result['response'][:100]}...")
        logger.info(f"   Caché: {result['from_cache']}")


if __name__ == "__main__":
    # Configurar logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
        level="INFO"
    )
    
    print("\n=== AI-EventStream: Client Examples ===\n")
    print("1. Análisis de sentimientos")
    print("2. Resumen de texto")
    print("3. Demostración de caché semántica")
    print("4. Procesamiento en lote")
    print("5. Salir")
    
    choice = input("\nSelecciona una opción: ")
    
    try:
        if choice == "1":
            example_sentiment_analysis()
        elif choice == "2":
            example_summarization()
        elif choice == "3":
            example_cache_demonstration()
        elif choice == "4":
            example_batch_processing()
        else:
            print("Saliendo...")
    except Exception as e:
        logger.error(f"Error: {e}")
