# Makefile para AI-EventStream
# Simplifica comandos comunes de desarrollo y despliegue

.PHONY: help install dev build up down logs test clean verify

# Variables
DOCKER_COMPOSE = docker-compose
PYTHON = python
PIP = pip

help: ## Muestra esta ayuda
	@echo "AI-EventStream - Comandos Disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependencias de Python
	$(PIP) install -r requirements.txt

dev: ## Inicia el entorno de desarrollo
	$(PYTHON) -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

build: ## Construye las imágenes Docker
	$(DOCKER_COMPOSE) build

up: ## Levanta todos los servicios
	$(DOCKER_COMPOSE) up -d

down: ## Detiene todos los servicios
	$(DOCKER_COMPOSE) down

restart: down up ## Reinicia todos los servicios

logs: ## Muestra logs de todos los servicios
	$(DOCKER_COMPOSE) logs -f

logs-api: ## Muestra logs de la API
	$(DOCKER_COMPOSE) logs -f api

logs-worker: ## Muestra logs de los workers
	$(DOCKER_COMPOSE) logs -f worker

logs-kafka: ## Muestra logs del consumidor de Kafka
	$(DOCKER_COMPOSE) logs -f kafka_consumer

test: ## Ejecuta los tests
	$(PYTHON) -m pytest test_system.py -v --cov=. --cov-report=html --html=reporte_errores.html

verify: ## Verifica el estado del sistema
	$(PYTHON) verify_system.py

clean: ## Limpia archivos temporales y caché
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

clean-docker: ## Limpia volúmenes y contenedores Docker
	$(DOCKER_COMPOSE) down -v
	docker system prune -f

shell-api: ## Abre shell en el contenedor de la API
	$(DOCKER_COMPOSE) exec api /bin/bash

shell-worker: ## Abre shell en un worker
	$(DOCKER_COMPOSE) exec worker /bin/bash

shell-redis: ## Abre CLI de Redis
	$(DOCKER_COMPOSE) exec redis redis-cli

ps: ## Muestra el estado de los servicios
	$(DOCKER_COMPOSE) ps

scale-workers: ## Escala los workers (uso: make scale-workers N=5)
	$(DOCKER_COMPOSE) up -d --scale worker=$(N)

flower: ## Abre Flower en el navegador
	@echo "Abriendo Flower en http://localhost:5555"
	@open http://localhost:5555 || xdg-open http://localhost:5555 || start http://localhost:5555

docs: ## Abre la documentación de la API
	@echo "Abriendo API Docs en http://localhost:8000/docs"
	@open http://localhost:8000/docs || xdg-open http://localhost:8000/docs || start http://localhost:8000/docs

format: ## Formatea el código con Black
	black *.py

lint: ## Ejecuta linter con Ruff
	ruff check *.py

type-check: ## Verifica tipos con mypy
	mypy *.py --ignore-missing-imports

all-checks: format lint type-check test ## Ejecuta todos los checks de calidad

init: ## Inicializa el proyecto (primera vez)
	@echo "Inicializando AI-EventStream..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Archivo .env creado. Por favor configura tus credenciales."; fi
	@mkdir -p logs
	@echo "Instalando dependencias..."
	$(MAKE) install
	@echo "Listo! Ejecuta 'make up' para iniciar los servicios."

backup-redis: ## Hace backup de Redis
	$(DOCKER_COMPOSE) exec redis redis-cli SAVE
	docker cp ai_eventstream_redis:/data/dump.rdb ./backup_redis_$(shell date +%Y%m%d_%H%M%S).rdb

restore-redis: ## Restaura backup de Redis (uso: make restore-redis FILE=backup.rdb)
	docker cp $(FILE) ai_eventstream_redis:/data/dump.rdb
	$(DOCKER_COMPOSE) restart redis
