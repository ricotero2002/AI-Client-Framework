# Guía de Despliegue - AI-EventStream

Esta guía detalla cómo desplegar AI-EventStream en diferentes plataformas cloud.

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Despliegue Local con Docker](#despliegue-local)
3. [Despliegue en Railway](#despliegue-railway)
4. [Despliegue en Render](#despliegue-render)
5. [Despliegue en AWS](#despliegue-aws)
6. [Configuración de Servicios Externos](#servicios-externos)
7. [Monitorización y Logs](#monitorización)

---

## 🔧 Requisitos Previos

### Servicios Necesarios

- **Redis**: Base de datos en memoria y broker de Celery
- **Kafka**: Sistema de mensajería para eventos
- **OpenAI API Key**: Para procesamiento de IA

### Opciones de Servicios Administrados

| Servicio | Opciones Gratuitas | Opciones Pagadas |
|----------|-------------------|------------------|
| Redis | Upstash (10K requests/day) | Redis Cloud, AWS ElastiCache |
| Kafka | Upstash Kafka (10K msgs/day) | Confluent Cloud, AWS MSK |
| Hosting | Railway (5$/mes gratis), Render | AWS, GCP, Azure |

---

## 🐳 Despliegue Local con Docker

### Paso 1: Configurar Variables de Entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### Paso 2: Levantar Servicios

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```powershell
.\start.ps1
```

### Paso 3: Verificar Estado

```bash
# Ver logs
docker-compose logs -f

# Verificar salud
curl http://localhost:8000/health

# Ver workers
curl http://localhost:8000/workers
```

---

## 🚂 Despliegue en Railway

Railway es ideal para desarrollo y proyectos pequeños con su tier gratuito.

### Paso 1: Preparar el Proyecto

1. Crear cuenta en [Railway.app](https://railway.app)
2. Instalar Railway CLI:
   ```bash
   npm i -g @railway/cli
   railway login
   ```

### Paso 2: Crear Servicios

```bash
# Inicializar proyecto
railway init

# Agregar Redis
railway add redis

# Agregar variables de entorno
railway variables set OPENAI_API_KEY=sk-...
railway variables set ENVIRONMENT=production
```

### Paso 3: Configurar Servicios

Crear `railway.json`:

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Paso 4: Desplegar

```bash
# Desplegar API
railway up --service api

# Desplegar Workers (crear nuevo servicio)
railway service create worker
railway up --service worker
```

### Configuración de Kafka en Railway

Para Kafka, usar **Upstash Kafka**:

1. Crear cuenta en [Upstash](https://upstash.com)
2. Crear cluster de Kafka
3. Copiar credenciales a Railway:
   ```bash
   railway variables set KAFKA_BOOTSTRAP_SERVERS=your-cluster.upstash.io:9092
   ```

---

## 🎨 Despliegue en Render

Render ofrece hosting gratuito con algunas limitaciones.

### Paso 1: Crear Servicios en Render

1. Ir a [Render Dashboard](https://dashboard.render.com)
2. Crear nuevo **Web Service** para la API
3. Crear nuevo **Background Worker** para Celery

### Paso 2: Configurar API Service

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Environment Variables:**
```
REDIS_URL=<redis-url-from-render>
KAFKA_BOOTSTRAP_SERVERS=<upstash-kafka>
OPENAI_API_KEY=<your-key>
ENVIRONMENT=production
```

### Paso 3: Configurar Worker Service

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
celery -A celery_app worker --loglevel=info --concurrency=2
```

### Paso 4: Agregar Redis

1. En Render Dashboard, crear nuevo **Redis** instance
2. Copiar la URL interna
3. Agregarla a las variables de entorno de API y Worker

---

## ☁️ Despliegue en AWS

Para producción a escala, AWS ofrece la mejor infraestructura.

### Arquitectura Recomendada

```
┌─────────────────┐
│   CloudFront    │ ← CDN
└────────┬────────┘
         │
┌────────▼────────┐
│   ALB/API GW    │ ← Load Balancer
└────────┬────────┘
         │
┌────────▼────────┐
│   ECS/Fargate   │ ← API Containers
└────────┬────────┘
         │
┌────────▼────────┐
│  ElastiCache    │ ← Redis
└────────┬────────┘
         │
┌────────▼────────┐
│   Amazon MSK    │ ← Kafka
└─────────────────┘
```

### Paso 1: Configurar ECR (Container Registry)

```bash
# Autenticar Docker con ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Crear repositorio
aws ecr create-repository --repository-name ai-eventstream-api
aws ecr create-repository --repository-name ai-eventstream-worker

# Construir y pushear imágenes
docker build --target api -t ai-eventstream-api .
docker tag ai-eventstream-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-eventstream-api:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-eventstream-api:latest
```

### Paso 2: Crear ElastiCache (Redis)

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id ai-eventstream-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1
```

### Paso 3: Crear MSK (Kafka)

```bash
aws kafka create-cluster \
  --cluster-name ai-eventstream-kafka \
  --broker-node-group-info file://broker-config.json \
  --kafka-version 3.5.1 \
  --number-of-broker-nodes 2
```

### Paso 4: Desplegar en ECS

Crear `task-definition.json`:

```json
{
  "family": "ai-eventstream-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-eventstream-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "REDIS_URL",
          "value": "redis://elasticache-endpoint:6379"
        },
        {
          "name": "KAFKA_BOOTSTRAP_SERVERS",
          "value": "msk-endpoint:9092"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account-id:secret:openai-key"
        }
      ]
    }
  ]
}
```

Registrar y ejecutar:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs create-service --cluster ai-eventstream --service-name api --task-definition ai-eventstream-api --desired-count 2
```

---

## 🔌 Configuración de Servicios Externos

### Upstash Redis

1. Crear cuenta en [Upstash](https://upstash.com)
2. Crear base de datos Redis
3. Habilitar **RedisJSON** y **RediSearch** (para caché semántica)
4. Copiar URL de conexión

### Upstash Kafka

1. En Upstash, crear cluster de Kafka
2. Crear tópico `datos_crudos`
3. Copiar bootstrap servers y credenciales

### OpenAI API

1. Crear cuenta en [OpenAI](https://platform.openai.com)
2. Generar API key
3. Configurar límites de uso y billing

---

## 📊 Monitorización y Logs

### Flower (Celery Dashboard)

Acceder a `http://your-domain:5555` para ver:
- Workers activos
- Tareas en cola
- Historial de ejecución
- Métricas de rendimiento

### CloudWatch (AWS)

Configurar logs y métricas:

```python
# En main.py y celery_tasks.py
import watchtower
import logging

logger = logging.getLogger()
logger.addHandler(watchtower.CloudWatchLogHandler())
```

### Prometheus + Grafana

Para métricas avanzadas, agregar exporters:

```yaml
# docker-compose.yml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
```

---

## 🔒 Seguridad

### Variables de Entorno Sensibles

Nunca commitear `.env`. Usar:
- **AWS Secrets Manager**
- **Railway/Render Environment Variables**
- **HashiCorp Vault**

### Rate Limiting

Configurar en `config.py`:

```python
rate_limit_calls: int = 60  # Llamadas por minuto
rate_limit_period: int = 60  # Período en segundos
```

### HTTPS

Usar certificados SSL:
- **Railway/Render**: Automático
- **AWS**: ACM (AWS Certificate Manager)

---

## 📈 Escalado

### Horizontal Scaling

**Workers de Celery:**
```bash
# Docker Compose
docker-compose up --scale worker=5

# ECS
aws ecs update-service --service worker --desired-count 5
```

**API Instances:**
```bash
# Railway
railway scale --replicas 3

# ECS
aws ecs update-service --service api --desired-count 3
```

### Vertical Scaling

Ajustar recursos en `docker-compose.yml`:

```yaml
worker:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
```

---

## 🆘 Troubleshooting

### Workers no procesan tareas

```bash
# Verificar conexión a Redis
redis-cli -u $REDIS_URL ping

# Ver logs de workers
docker-compose logs -f worker
```

### Kafka no recibe mensajes

```bash
# Listar tópicos
kafka-topics --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --list

# Consumir mensajes manualmente
kafka-console-consumer --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --topic datos_crudos --from-beginning
```

### API lenta

1. Verificar cache hit rate en `/metrics`
2. Aumentar workers de Celery
3. Optimizar umbral de similitud semántica

---

## 📚 Recursos Adicionales

- [Documentación de Celery](https://docs.celeryq.dev/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Redis Best Practices](https://redis.io/docs/management/optimization/)
- [Kafka Documentation](https://kafka.apache.org/documentation/)
