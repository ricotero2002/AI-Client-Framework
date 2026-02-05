#!/bin/bash
# Script de inicio rápido para AI-EventStream
# Levanta todos los servicios con Docker Compose

set -e

echo "🚀 AI-EventStream - Quick Start"
echo "================================"
echo ""

# Verificar que Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor instala Docker primero."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose no está instalado. Por favor instala Docker Compose primero."
    exit 1
fi

# Verificar que existe el archivo .env
if [ ! -f .env ]; then
    echo "⚠️  Archivo .env no encontrado. Copiando desde .env.example..."
    cp .env.example .env
    echo "⚠️  Por favor edita el archivo .env con tus credenciales antes de continuar."
    echo "   Especialmente necesitas configurar:"
    echo "   - OPENAI_API_KEY"
    echo "   - GOOGLE_API_KEY (opcional)"
    exit 1
fi

# Crear directorio de logs si no existe
mkdir -p logs

echo "📦 Construyendo imágenes Docker..."
docker-compose build

echo ""
echo "🚀 Iniciando servicios..."
docker-compose up -d

echo ""
echo "⏳ Esperando a que los servicios estén listos..."
sleep 10

echo ""
echo "✅ Servicios iniciados!"
echo ""
echo "📊 Estado de los servicios:"
docker-compose ps

echo ""
echo "🌐 URLs disponibles:"
echo "   - API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Flower (Celery): http://localhost:5555"
echo "   - RedisInsight: http://localhost:8001"
echo ""
echo "📝 Ver logs:"
echo "   docker-compose logs -f [servicio]"
echo ""
echo "   Servicios disponibles:"
echo "   - api"
echo "   - worker"
echo "   - kafka_consumer"
echo "   - flower"
echo "   - redis"
echo "   - kafka"
echo ""
echo "🛑 Detener servicios:"
echo "   docker-compose down"
echo ""
echo "✨ ¡Listo para usar!"
