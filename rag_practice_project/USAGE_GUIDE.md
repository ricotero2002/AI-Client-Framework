# Guía de Uso - Proyecto RAG

## 🚀 Inicio Rápido

### 1. Instalación de Dependencias

```bash
# Instalar todas las dependencias necesarias
pip install -r requirements.txt

Desde rag_practice_proyect
```

### 2. Configuración

Crea un archivo `.env` en la raíz del proyecto:

```bash
# Copiar el template
cp .env.example .env
```

Edita `.env` y agrega tus API keys:

```env
OPENAI_API_KEY=tu_api_key_aqui
GEMINI_API_KEY=tu_api_key_aqui
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-3.5-turbo
```

### 3. Setup Inicial

```bash
# Cargar datos y crear vector database
python setup.py
```

Este script:
- Descarga el dataset de Kaggle
- Procesa las recetas
- Genera embeddings
- Crea la base de datos vectorial con ChromaDB

### 4. Ejecutar Experimentos

```bash
# Ejecutar todos los experimentos
python experiments/run_all_experiments.py
```

Esto evaluará las 6 estrategias RAG con 10 consultas de prueba.

## 📊 Estrategias RAG Implementadas

### 1. **No RAG** (Baseline)
- Sin recuperación de contexto
- Solo LLM puro
- Útil como baseline de comparación

### 2. **Naive RAG**
- Recuperación → Lectura → Generación
- Enfoque más básico de RAG
- Recupera top-k documentos por similitud

### 3. **Advanced RAG**
- Pre-recuperación: Optimización de consultas
- Post-recuperación: Re-ranking y filtrado
- Mejora significativa sobre Naive RAG

### 4. **Modular RAG**
- Arquitectura modular con componentes intercambiables
- Retriever, QueryProcessor, ContextBuilder
- Fácil de personalizar y extender

### 5. **Agentic RAG**
- Agentes autónomos que toman decisiones
- Decide si necesita recuperar información
- Refina búsquedas automáticamente

### 6. **Graph RAG**
- Basado en grafos de conocimiento
- Navegación contextual entre recetas
- Encuentra relaciones entre ingredientes

## 📈 Métricas Evaluadas

### Rendimiento
- **Latencia**: Tiempo de respuesta en ms
- **Costo**: Tokens y costo en USD

### Calidad
- **Relevancia**: Qué tan relevante es la respuesta
- **Claridad**: Qué tan clara es la respuesta
- **Concisión**: Qué tan concisa es la respuesta
- **Cumplimiento**: Si cumple con lo solicitado
- **Precisión Factual**: Si es correcta según el contexto

## 🔧 Personalización

### Cambiar el Modelo LLM

Edita `.env`:
```env
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_MODEL=gemini-pro
```

### Agregar Nuevas Consultas de Prueba

Edita `experiments/run_all_experiments.py`:
```python
TEST_QUERIES = [
    "Tu consulta personalizada aquí",
    # ... más consultas
]
```

### Crear una Nueva Estrategia RAG

1. Crea un archivo en `src/rag_strategies/`
2. Hereda de `BaseRAGStrategy`
3. Implementa `generate_response()`

Ejemplo:
```python
from src.rag_strategies.base_strategy import BaseRAGStrategy

class MiNuevaEstrategia(BaseRAGStrategy):
    def __init__(self):
        super().__init__("Mi Nueva Estrategia")
    
    def generate_response(self, query: str, **kwargs):
        # Tu implementación aquí
        pass
```

## 📁 Estructura de Resultados

Después de ejecutar experimentos, encontrarás en `results/`:

- `experiment_results_YYYYMMDD_HHMMSS.json`: Resultados detallados
- `latency_comparison.png`: Comparación de latencias
- `quality_comparison.png`: Comparación de calidad
- `cost_vs_quality.png`: Análisis costo vs calidad
- `latency_vs_quality.png`: Análisis latencia vs calidad
- `quality_heatmap.png`: Heatmap de métricas

## 🎯 Ejemplos de Uso

### Usar una Estrategia Específica

```python
from src.rag_strategies.advanced_rag import AdvancedRAGStrategy

# Crear estrategia
strategy = AdvancedRAGStrategy(top_k=10, final_k=5)

# Generar respuesta
result = strategy.generate_response("¿Recetas veganas con quinoa?")

print(result["response"])
print(f"Latencia: {result['latency_ms']:.1f} ms")
print(f"Costo: ${result['cost_usd']:.4f}")
```

### Evaluar una Respuesta

```python
from src.evaluation.evaluator import RAGEvaluator

evaluator = RAGEvaluator()

metrics = evaluator.evaluate_response(
    query="¿Recetas veganas con quinoa?",
    response="Aquí hay algunas recetas...",
    context=["Receta 1...", "Receta 2..."]
)

print(f"Score general: {metrics['overall_score']:.2f}")
print(f"Relevancia: {metrics['relevance']:.2f}")
```

### Analizar Resultados

```python
from src.evaluation.analyzer import ResultsAnalyzer
import json

# Cargar resultados
with open("results/experiment_results.json") as f:
    results = json.load(f)

# Analizar
analyzer = ResultsAnalyzer(results)
analyzer.print_summary()
analyzer.generate_visualizations(Path("results"))
```

## 🐛 Troubleshooting

### Error: "No module named 'config'"
```bash
# Asegúrate de ejecutar desde la raíz del proyecto
cd rag_practice_project
python setup.py
```

### Error: "API key not found"
```bash
# Verifica que .env existe y tiene las keys correctas
cat .env
```

### Error al cargar dataset de Kaggle
```bash
# Configura Kaggle API
# Descarga kaggle.json desde https://www.kaggle.com/settings
# Colócalo en ~/.kaggle/kaggle.json (Linux/Mac) o %USERPROFILE%\.kaggle\kaggle.json (Windows)
```

## 📚 Recursos Adicionales

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [OpenAI API](https://platform.openai.com/docs)
- [Google Gemini API](https://ai.google.dev/)

## 📄 Licencia

Este proyecto es para fines educativos y de práctica.
