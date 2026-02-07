# Guía de Inicio Rápido - AI-EventStream

Esta guía te ayudará a poner en marcha AI-EventStream en menos de 10 minutos.

## 🚀 Inicio Rápido (Docker)

### Paso 1: Clonar y Configurar

```bash
# Navegar al directorio
cd ai_eventstream

# Copiar archivo de configuración
cp .env.example .env
```

### Paso 2: Configurar Credenciales

Edita el archivo `.env` y agrega tu API key de OpenAI:

```env
OPENAI_API_KEY=sk-tu-api-key-aqui
```

### Paso 3: Levantar Servicios

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```powershell
.\start.ps1
```

**O usando Docker Compose directamente:**
```bash
docker-compose up -d
```

### Paso 4: Verificar

```bash
# Verificar que todo esté funcionando
python verify_system.py

# O manualmente
curl http://localhost:8000/health
```

## 🎯 Primer Uso

### Opción 1: Usando el Cliente Python

```python
python api_client_example.py
```

Selecciona una de las opciones del menú interactivo.

### Opción 2: Usando cURL

```bash
# Enviar tarea
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Este producto es excelente!",
    "task_type": "sentiment_analysis"
  }'

# Respuesta: {"task_id": "abc-123", ...}

# Consultar resultado
curl http://localhost:8000/task/abc-123
```

### Opción 3: Usando la Documentación Interactiva

Abre en tu navegador: http://localhost:8000/docs

## 📊 Monitorización

### Flower (Celery Dashboard)
http://localhost:5555

### RedisInsight
http://localhost:8001

### API Docs
http://localhost:8000/docs

## 🔧 Comandos Útiles

```bash
# Ver logs
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f api
docker-compose logs -f worker

# Reiniciar servicios
docker-compose restart

# Detener todo
docker-compose down

# Escalar workers
docker-compose up -d --scale worker=5
```

## 📝 Ejemplos de Uso

### Análisis de Sentimientos

```python
import requests

response = requests.post(
    "http://localhost:8000/process",
    json={
        "text": "Me encanta este producto, es increíble!",
        "task_type": "sentiment_analysis"
    }
)

task_id = response.json()["task_id"]
print(f"Task ID: {task_id}")
```

### Resumen de Texto

```python
article = """
La inteligencia artificial está transformando el mundo...
[texto largo]
"""

response = requests.post(
    "http://localhost:8000/process",
    json={
        "text": article,
        "task_type": "summarization",
        "temperature": 0.3,
        "max_tokens": 200
    }
)
```

### Enviar Eventos a Kafka

```python
python kafka_producer_example.py
```

## 🐛 Troubleshooting

### La API no responde

```bash
# Verificar que el contenedor esté corriendo
docker-compose ps

# Ver logs
docker-compose logs api
```

### No hay workers activos

```bash
# Verificar workers
curl http://localhost:8000/workers

# Reiniciar workers
docker-compose restart worker
```

### Error de conexión a Redis

```bash
# Verificar Redis
docker-compose exec redis redis-cli ping
# Debe responder: PONG
```

### Error de Kafka

```bash
# Verificar Kafka
docker-compose logs kafka

# Listar tópicos
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

## 📚 Próximos Pasos

1. **Explorar la Documentación:**
   - [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitectura del sistema
   - [DEPLOYMENT.md](DEPLOYMENT.md) - Guía de despliegue en producción

2. **Personalizar:**
   - Modificar prompts en `celery_tasks.py`
   - Ajustar configuración en `config.py`
   - Agregar nuevos tipos de tareas

3. **Desplegar en Producción:**
   - Ver [DEPLOYMENT.md](DEPLOYMENT.md) para Railway, Render o AWS

## 🆘 Ayuda

Si encuentras problemas:

1. Verifica los logs: `docker-compose logs -f`
2. Ejecuta el verificador: `python verify_system.py`
3. Revisa la documentación en `/docs`

## 🎉 ¡Listo!

Tu sistema AI-EventStream está funcionando. Ahora puedes:

- ✅ Procesar texto con IA de forma asíncrona
- ✅ Aprovechar la caché semántica para reducir costos
- ✅ Escalar horizontalmente según la demanda
- ✅ Monitorizar con Flower y métricas

¡Disfruta construyendo con AI-EventStream! 🚀
