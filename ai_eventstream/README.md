# AI-EventStream: Agente de Procesamiento Semántico Distribuido

Sistema de procesamiento de IA distribuido y asíncrono que utiliza Apache Kafka para ingesta masiva de eventos, Celery para procesamiento pesado de modelos de IA, y Redis como capa de memoria ultrarrápida.

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐
│  Apache Kafka   │ ← Ingesta de datos masiva
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI API   │ ← Orquestador asíncrono
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Redis       │ ← Broker + Caché Semántica
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Celery Workers  │ ← Procesamiento de IA
└─────────────────┘
```

## 🚀 Componentes Principales

### 1. **Ingesta de Datos (Apache Kafka)**
- Sistema nervioso central del flujo de datos
- Recibe eventos masivos (reseñas, logs, mensajes)
- Garantiza durabilidad e inmutabilidad

### 2. **Orquestador API (FastAPI)**
- Endpoints asíncronos para envío de tareas
- Consulta de estados y métricas
- Totalmente no-bloqueante

### 3. **Procesamiento de IA (Celery + Workers)**
- Ejecución distribuida de LLMs
- Escalado independiente según carga
- Optimizado para tareas pesadas

### 4. **Cerebro y Memoria (Redis)**
- **Broker**: Intermediario entre FastAPI y Celery
- **Caché Semántica**: Búsqueda vectorial con RedisVL
- **Async Client**: Conexión de baja latencia

## 📦 Stack Tecnológico

| Componente      | Tecnología    | Rol                                          |
|-----------------|---------------|----------------------------------------------|
| Backend         | FastAPI       | Gateway asíncrono y manejo de endpoints      |
| Worker          | Celery        | Ejecución distribuida de modelos de IA       |
| Broker/Cache    | Redis Stack   | Memoria RAM, broker y búsqueda vectorial     |
| Streaming       | Apache Kafka  | Ingesta de eventos inmutable y duradera      |
| Monitorización  | Flower        | Dashboard en tiempo real para tareas Celery  |
| Infraestructura | Docker        | Contenedores y hosting escalable            |


### ✅1: El Núcleo Asíncrono (FastAPI + Redis)
- [x] Setup de FastAPI con uvicorn
- [x] Cliente Redis asíncrono (redis.asyncio)
- [x] Estructura de Caché Semántica con RedisVL
- [x] Endpoints básicos de API

### ✅2: El Músculo del Agente (Celery + IA)
- [x] Configuración de Celery con Redis
- [x] Integración con LLM (OpenAI/HuggingFace)
- [x] Optimización de workers (prefetch, acks_late)
- [x] Reinicio automático para evitar fugas de memoria

### ✅3: El Bus de Eventos (Apache Kafka)
- [x] Kafka Consumer independiente
- [x] Patrón de disparo: Kafka → Celery
- [x] Desacoplamiento completo
- [x] Persistencia de resultados en Redis

### ✅4: Memoria de Agente y Lógica Avanzada
- [x] Lógica de caché semántica
- [x] Búsqueda vectorial (umbral > 0.8)
- [x] Rate limiting para APIs externas
- [x] Optimización de costos

### ✅5: Dockerización y Despliegue Cloud
- [x] Dockerfile multietapa
- [x] docker-compose.yml completo
- [x] Configuración de variables de entorno
- [x] Endpoint público /process

## 🛠️ Instalación

### Requisitos Previos
- Python 3.11+
- Docker y Docker Compose
- Redis Stack
- Apache Kafka

### Instalación Local

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### Usando Docker

```bash
# Levantar todos los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener servicios
docker-compose down
```

## 🎯 Uso

### 1. Enviar una tarea para procesamiento

```python
import requests

response = requests.post(
    "http://localhost:8000/process",
    json={
        "text": "Analiza el sentimiento de esta reseña: El producto es excelente!",
        "task_type": "sentiment_analysis"
    }
)

task_id = response.json()["task_id"]
print(f"Task ID: {task_id}")
```

### 2. Consultar el estado de una tarea

```python
status_response = requests.get(f"http://localhost:8000/task/{task_id}")
print(status_response.json())
```

### 3. Enviar eventos a Kafka

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

producer.send('datos_crudos', {
    'text': 'Texto para analizar',
    'metadata': {'source': 'web'}
})
```

## 📊 Monitorización

### Flower (Celery Dashboard)
Accede a `http://localhost:5555` para ver:
- Tareas activas y completadas
- Workers disponibles
- Métricas de rendimiento

### API Metrics
Accede a `http://localhost:8000/metrics` para ver:
- Tareas procesadas
- Cache hit rate
- Latencia promedio

## 🔧 Configuración Avanzada

### Optimización de Workers

```python
# celery_config.py
worker_prefetch_multiplier = 1  # Una tarea a la vez
task_acks_late = True           # Confirmar después de completar
worker_max_tasks_per_child = 100  # Reiniciar después de 100 tareas
```

### Caché Semántica

```python
# Umbral de similitud para cache hit
SEMANTIC_SIMILARITY_THRESHOLD = 0.8

# TTL de caché (en segundos)
CACHE_TTL = 3600  # 1 hora
```

## 🚀 Despliegue en Producción

### Railway/Render

1. Conectar el repositorio
2. Configurar variables de entorno:
   - `REDIS_URL`
   - `KAFKA_BOOTSTRAP_SERVERS`
   - `OPENAI_API_KEY`
3. Desplegar API y Workers por separado

### Variables de Entorno Requeridas

```env
# Redis
REDIS_URL=redis://localhost:6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# OpenAI
OPENAI_API_KEY=sk-...

# Configuración
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 📈 Características Principales

- ✅ **Procesamiento Asíncrono**: FastAPI + Redis async
- ✅ **Escalabilidad Horizontal**: Workers Celery independientes
- ✅ **Caché Inteligente**: Búsqueda vectorial semántica
- ✅ **Ingesta Masiva**: Apache Kafka para eventos
- ✅ **Optimización de Costos**: Reutilización de respuestas LLM
- ✅ **Monitorización**: Flower + métricas personalizadas
- ✅ **Dockerizado**: Despliegue simple con docker-compose

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📝 Licencia

MIT License - ver el archivo LICENSE para más detalles

## 🙏 Agradecimientos

- FastAPI por el framework asíncrono
- Celery por el procesamiento distribuido
- Redis por la velocidad y versatilidad
- Apache Kafka por la ingesta confiable
