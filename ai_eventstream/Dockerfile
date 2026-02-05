# Dockerfile multietapa para AI-EventStream
# Optimizado para producción con capas separadas

# ============================================
# Stage 1: Base
# ============================================
FROM python:3.11-slim as base

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ============================================
# Stage 2: API
# ============================================
FROM base as api

# Copiar código de la aplicación
COPY config.py .
COPY redis_client.py .
COPY celery_app.py .
COPY celery_tasks.py .
COPY main.py .

# Crear directorio de logs
RUN mkdir -p logs

# Exponer puerto
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Stage 3: Worker
# ============================================
FROM base as worker

# Copiar código de la aplicación
COPY config.py .
COPY redis_client.py .
COPY celery_app.py .
COPY celery_tasks.py .

# Crear directorio de logs
RUN mkdir -p logs

# Comando por defecto
CMD ["celery", "-A", "celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=4", \
     "--max-tasks-per-child=100", \
     "--prefetch-multiplier=1"]

# ============================================
# Stage 4: Kafka Consumer
# ============================================
FROM base as consumer

# Copiar código de la aplicación
COPY config.py .
COPY redis_client.py .
COPY celery_app.py .
COPY celery_tasks.py .
COPY kafka_consumer.py .

# Crear directorio de logs
RUN mkdir -p logs

# Comando por defecto
CMD ["python", "kafka_consumer.py"]

# ============================================
# Stage 5: Flower (Monitoring)
# ============================================
FROM base as flower

# Copiar solo lo necesario para Flower
COPY config.py .
COPY celery_app.py .

# Exponer puerto
EXPOSE 5555

# Comando por defecto
CMD ["celery", "-A", "celery_app", "flower", "--port=5555"]
