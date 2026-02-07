# Script de inicio rápido para AI-EventStream (Windows)
# Levanta todos los servicios con Docker Compose

Write-Host " AI-EventStream - Quick Start" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que Docker está instalado
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host " Docker no está instalado. Por favor instala Docker Desktop primero." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host " Docker Compose no está instalado. Por favor instala Docker Compose primero." -ForegroundColor Red
    exit 1
}

# Verificar que existe el archivo .env
if (-not (Test-Path .env)) {
    Write-Host "  Archivo .env no encontrado. Copiando desde .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "  Por favor edita el archivo .env con tus credenciales antes de continuar." -ForegroundColor Yellow
    Write-Host "   Especialmente necesitas configurar:" -ForegroundColor Yellow
    Write-Host "   - OPENAI_API_KEY" -ForegroundColor Yellow
    Write-Host "   - GOOGLE_API_KEY (opcional)" -ForegroundColor Yellow
    exit 1
}

# Crear directorio de logs si no existe
if (-not (Test-Path logs)) {
    New-Item -ItemType Directory -Path logs | Out-Null
}

Write-Host " Construyendo imágenes Docker..." -ForegroundColor Yellow
docker-compose build

Write-Host ""
Write-Host " Iniciando servicios..." -ForegroundColor Green
docker-compose up -d

Write-Host ""
Write-Host " Esperando a que los servicios estén listos..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host " Servicios iniciados!" -ForegroundColor Green
Write-Host ""
Write-Host " Estado de los servicios:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host " URLs disponibles:" -ForegroundColor Cyan
Write-Host "   - API: http://localhost:8000" -ForegroundColor White
Write-Host "   - API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "   - Flower (Celery): http://localhost:5555" -ForegroundColor White
Write-Host "   - RedisInsight: http://localhost:8001" -ForegroundColor White
Write-Host ""
Write-Host " Ver logs:" -ForegroundColor Cyan
Write-Host "   docker-compose logs -f [servicio]" -ForegroundColor White
Write-Host ""
Write-Host "   Servicios disponibles:" -ForegroundColor Yellow
Write-Host "   - api" -ForegroundColor White
Write-Host "   - worker" -ForegroundColor White
Write-Host "   - kafka_consumer" -ForegroundColor White
Write-Host "   - flower" -ForegroundColor White
Write-Host "   - redis" -ForegroundColor White
Write-Host "   - kafka" -ForegroundColor White
Write-Host ""
Write-Host " Detener servicios:" -ForegroundColor Cyan
Write-Host "   docker-compose down" -ForegroundColor White
Write-Host ""
Write-Host " ¡Listo para usar!" -ForegroundColor Green
