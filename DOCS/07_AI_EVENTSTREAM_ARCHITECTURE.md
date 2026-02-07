# AI-EventStream: Distributed AI Processing System

## 📋 Resumen Ejecutivo

**AI-EventStream** es una plataforma de procesamiento de eventos en tiempo real impulsada por Inteligencia Artificial distribuida. Su arquitectura desacoplada permite la ingesta masiva de datos a través de **Apache Kafka**, el procesamiento asíncrono y escalable mediante **Celery**, y el uso de **Redis** como backend de resultados, cola de mensajes y caché semántica vectorial.

El sistema está diseñado para manejar flujos de trabajo de IA pesados (como generación de texto con LLMs o análisis de embeddings) sin bloquear la API principal, garantizando alta disponibilidad, tolerancia a fallos y observabilidad completa.

---

## 🎯 Objetivos del Proyecto

1.  **Procesamiento Asíncrono**: Desacoplar la recepción de datos del procesamiento pesado de IA.
2.  **Escalabilidad Horizontal**: Permitir aumentar el número de workers y particiones de Kafka según la carga.
3.  **Eficiencia de Costos y Latencia**: Implementar una **Caché Semántica** (Redis Vector Search) para evitar llamadas redundantes a los LLMs.
4.  **Alta Disponibilidad**: Arquitectura tolerante a fallos con reintentos automáticos y colas persistentes.
5.  **Observabilidad**: Monitoreo en tiempo real de métricas, estados de tareas (Flower) y flujos de eventos (Kafka UI).

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Flujo de Datos

```mermaid
graph TD
    Client[Cliente/API] -->|POST /process| API[FastAPI]
    API -->|1. Check Cache| RedisCache[(Redis Semantic Cache)]
    RedisCache -- Cache Hit --> API
    RedisCache -- Cache Miss --> API
    
    API -->|2. Produce Event| Kafka{Apache Kafka}
    Kafka -->|Topic: datos_crudos| Consumer[Kafka Consumer]
    
    Consumer -->|3. Trigger Task| CeleryWorker[Celery Worker]
    CeleryWorker -->|4. Consult LLM| LLM[Gemini/OpenAI]
    
    CeleryWorker -->|5. Store Result| RedisBackend[(Redis Backend)]
    CeleryWorker -->|6. Update Cache| RedisCache
    
    Client -->|GET /task/{id}| API
    API -->|Query Status| RedisBackend
```

### Componentes Principales

| Componente | Tecnología | Rol en el Sistema |
| :--- | :--- | :--- |
| **API Gateway** | FastAPI | Punto de entrada REST para clientes. Maneja autenticación, validación y consulta de caché inicial. |
| **Event Bus** | Apache Kafka | Cola de mensajes distribuida y persistente. Garantiza que ningún evento se pierda y permite el procesamiento paralelo mediante particiones. |
| **Task Queue** | Celery | Gestor de tareas distribuidas. Orquesta la ejecución de trabajos en los workers. |
| **Workers** | Python/Celery | Unidades de procesamiento que ejecutan la lógica de IA (llamadas a LLMs, embeddings). Escalables horizontalmente. |
| **Message Broker** | Redis (DB 1) | Intermediario para las tareas de Celery (comunicación API-Worker y Consumer-Worker). |
| **Result Backend** | Redis (DB 2) | Almacenamiento temporal de los estados y resultados de las tareas de Celery. |
| **Semantic Cache** | Redis (DB 0) | Almacén de vectores (Redis Stack) para búsqueda de similitud semántica. Reduce costos y latencia. |
| **Monitorización** | Flower / Kafka UI | Interfaces visuales para inspeccionar colas, workers y tópicos de Kafka. |

---

## 🧠 Lógica de Procesamiento y Decisiones de Diseño

### 1. Estrategia de Caché Semántica
El sistema no usa una caché simple de clave-valor. Implementa **RAG (Retrieval-Augmented Generation)** simplificado para cachear respuestas:
1.  Se genera un **embedding** del prompt de entrada usando `gemini-embedding-001`.
2.  Se busca en Redis (usando `RedisVL`) vectores similares con un umbral de similitud (ej: >0.85).
3.  Si hay coincidencia ("Cache Hit"), se devuelve la respuesta almacenada inmediatamente (latencia <50ms).
4.  Si no ("Cache Miss"), se procesa con el LLM y se guarda el nuevo par (Prompt Vector, Respuesta) para el futuro.

### 2. Kafka: Particiones y Consumo
*   **Tópicos**:
    *   `datos_crudos`: Donde llegan los eventos originales.
    *   `datos_procesados` (Planeado): Para publicar resultados finales para otros consumidores.
*   **Particiones**: Permiten paralelismo. Si el tópico tiene 3 particiones, podemos tener hasta 3 consumidores leyendo simultáneamente, cada uno encargado de un subconjunto de datos.
*   **Consumer Groups**: El consumidor pertenece al grupo `ai_eventstream_consumers`. Kafka gestiona los **offsets** (punteros de lectura) para este grupo, asegurando que si el consumidor se reinicia, retome desde el último mensaje no procesado.

### 3. Celery: Aislamiento de Recursos
Se utiliza Redis con bases de datos lógicas separadas para evitar colisiones y facilitar el mantenimiento (ej: hacer FLUSHDB de la caché sin borrar la cola de tareas):
*   **DB 0**: Caché Semántica y métricas de aplicación.
*   **DB 1**: Broker de Celery (Cola de tareas).
*   **DB 2**: Backend de Celery (Resultados).

---

## 🛠️ Guía de Implementación y Despliegue

### Requisitos Previos
*   Docker y Docker Compose
*   API Key de Google Gemini (o OpenAI)

### Configuración (.env)
El sistema se configura mediante variables de entorno. Las más críticas son:

```ini
# IA Configuration
GOOGLE_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash-lite
VECTOR_DIMENSION=3072  # Crítico: debe coincidir con el modelo de embedding

# Redis & Kafka
REDIS_HOST=redis
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
```

### Comandos de Gestión

**Iniciar Sistema**
```bash
docker compose up -d --build
```

**Ver Logs del Worker**
```bash
docker logs -f ai_eventstream-worker-1
```

**Escalar Workers**
```bash
# Levanta 3 instancias de workers para mayor paralelismo
docker compose up -d --scale worker=3
```

**Monitorización**
*   **API Docs**: `http://localhost:8000/docs`
*   **Métricas**: `http://localhost:8000/metrics`
*   **Flower (Celery)**: `http://localhost:5555`
*   **Kafka UI**: `http://localhost:8081`

---

## 🔍 Estructura del Código

| Archivo | Descripción |
| :--- | :--- |
| `main.py` | API FastAPI. Endpoints para `/process` (ingesta), `/task/{id}` (consulta) y `/metrics`. |
| `celery_tasks.py` | Definición de tareas (`process_with_llm`, `generate_embedding`). Lógica core de IA. |
| `kafka_consumer.py` | Servicio que escucha continuamente el tópico de Kafka y dispara tareas de Celery. |
| `redis_client.py` | Cliente asíncrono para Redis. Maneja la lógica de búsqueda vectorial (Semantic Cache). |
| `config.py` | Configuración centralizada basada en Pydantic. |
| `docker-compose.yml` | Orquestación de servicios (Redis Stack, Zookeeper, Kafka, API, Workers, Flower). |

---

## 🚀 Flujos de Trabajo (Workflows)

### Flujo API Directo (Síncrono/Asíncrono Híbrido)
1.  Usuario envía `POST /process` con `use_cache=True`.
2.  API verifica caché semántica.
    *   **Hit**: Retorna respuesta JSON inmediatamente.
    *   **Miss**: Envía mensaje a Kafka.
3.  Retorna `task_id`.
4.  Usuario hace polling a `GET /task/{task_id}` hasta obtener `status: SUCCESS`.

### Flujo Kafka Puro (Batch Processing)
1.  Script productor (`kafka_producer_example.py`) inyecta 1000 eventos a Kafka.
2.  Consumer lee en lotes (`max_poll_records=10`).
3.  Se disparan 1000 tareas de Celery de forma distribuida entre los workers disponibles.
4.  Resultados se almacenan en Redis Backend para auditoría o consumo posterior.
