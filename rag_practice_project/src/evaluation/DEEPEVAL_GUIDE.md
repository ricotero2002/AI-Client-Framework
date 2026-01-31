# Integración de DeepEval - Guía de Uso

## ✅ Implementación Completada

Se ha refactorizado exitosamente el sistema de evaluación RAG para usar **DeepEval** en lugar de prompts manuales.

### Archivos Creados/Modificados

1. **`src/evaluation/deepeval_llm_wrapper.py`** (NUEVO)
   - Wrapper personalizado que integra DeepEval con nuestro `LLMClientWrapper`
   - Permite usar Gemini/OpenAI para las evaluaciones sin configuración adicional

2. **`src/evaluation/evaluator.py`** (REFACTORIZADO)
   - Usa las 5 métricas de DeepEval: Contextual Precision, Recall, Relevancy, Faithfulness, Answer Relevancy
   - Cada métrica retorna `{"score": float, "reason": str}` para debugging mejorado
   - Eliminados ~400 líneas de código de prompts manuales

3. **`src/evaluation/analyzer.py`** (REFACTORIZADO)
   - Aplana estructura de DeepEval en DataFrame
   - **Nueva visualización**: Radar Chart para las 5 métricas
   - **Nueva sección en reportes**: Análisis de fallos con explicaciones de DeepEval

4. **`src/evaluation/test_queries_example.py`** (NUEVO)
   - Ejemplos de cómo estructurar queries con Ground Truth

---

## 📋 Formato de Datos Requerido

### IMPORTANTE: Estructura de test_queries

El `ExperimentRunner` ahora requiere que `test_queries` sea una lista de **diccionarios** con este formato:

```python
test_queries = [
    {
        "query": "¿Cómo preparar hummus?",
        "expected_output": "Para hacer hummus necesitas garbanzos cocidos, tahini, limón..."
    },
    {
        "query": "¿Qué recetas tienen quinoa?",
        "expected_output": "Bowl de quinoa con frijoles, ensalada de quinoa..."
    }
]
```

**Campos:**
- `query` (str): La pregunta del usuario
- `expected_output` (str): La respuesta esperada (Ground Truth)

### ¿Qué es el Ground Truth (expected_output)?

Es la **respuesta ideal/esperada** que el sistema debería generar. DeepEval usa esto para:

1. **Contextual Recall**: Verificar si el contexto recuperado contiene la información necesaria
2. **Faithfulness**: Detectar si la respuesta alucina información no presente en el contexto
3. **Answer Relevancy**: Comparar la relevancia de la respuesta generada vs. la esperada

### Si NO tienes Ground Truth

Si no tienes respuestas esperadas preparadas, puedes usar un placeholder genérico:

```python
test_queries = [
    {"query": "¿Cómo hacer hummus?", "expected_output": "Respuesta detallada sobre la consulta."},
    {"query": "Recetas con quinoa", "expected_output": "Respuesta detallada sobre la consulta."}
]
```

**Nota**: Esto reduce la precisión de las métricas, pero permite ejecutar DeepEval.

---

## 🚀 Cómo Usar

### 1. Actualizar run_all_experiments.py

Cambia tus `TEST_QUERIES` actuales (que son solo strings) por el nuevo formato:

```python
# ANTES (solo strings)
TEST_QUERIES = [
    "¿Cómo preparar hummus?",
    "Dame recetas con quinoa"
]

# DESPUÉS (diccionarios con expected_output)
TEST_QUERIES = [
    {
        "query": "¿Cómo preparar hummus?",
        "expected_output": "Para hacer hummus necesitas garbanzos cocidos, tahini, jugo de limón, ajo y aceite de oliva. Procesa todos los ingredientes hasta obtener una consistencia cremosa."
    },
    {
        "query": "Dame recetas con quinoa",
        "expected_output": "Bowl de quinoa con frijoles negros, ensalada de quinoa mediterránea, y quinoa con verduras asadas son opciones populares."
    }
]
```

### 2. Ejecutar Experimentos

```bash
python run_all_experiments.py
```

El output ahora incluirá:
- Scores de las 5 métricas DeepEval
- Reasons (explicaciones) cuando hay fallos
- Radar chart mostrando balance entre métricas
- Sección de análisis de fallos en el reporte markdown

### 3. Revisar Resultados

**Visualizaciones generadas:**
- `radar_chart.png` (NUEVO) - Balance entre las 5 métricas
- `retrieval_vs_generation.png` - Comparación Retrieval vs Generation
- `diagnostic_heatmap.png` - Heatmap de todas las métricas
- `hallucination_analysis.png` - Scatter plot Recall vs Faithfulness
- `cost_vs_quality.png`
- `latency_vs_quality.png`

**Reporte markdown:**
- Incluye nueva sección "🔍 ANÁLISIS DE FALLOS"
- Muestra los 3 peores casos de cada métrica con explicaciones

---

## 🔧 Configuración

### Modelo de Evaluación

El modelo usado para evaluaciones se configura en `src/utils/config_loader.py`:

```python
EVALUATION_LLM_PROVIDER = "gemini"  # o "openai"
EVALUATION_MODEL = "gemini-1.5-flash"
```

DeepEval usará este modelo para todas las métricas.

### Thresholds de Métricas

Actualmente configurados en 0.5 (50%). Puedes ajustarlos en `evaluator.py`:

```python
self.contextual_precision = ContextualPrecisionMetric(
    threshold=0.7,  # Cambiar aquí
    model=self.deepeval_llm,
    include_reason=True
)
```

---

## 📊 Interpretación de Métricas

### Retrieval Metrics

| Métrica | Qué mide | Score bajo indica |
|---------|----------|-------------------|
| **Contextual Precision** | Chunks relevantes al inicio | Reranking deficiente |
| **Contextual Recall** | % de info del GT en contexto | Embeddings malos o top_k bajo |
| **Contextual Relevancy** | % de contenido relevante | Mucho ruido en el contexto |

### Generation Metrics

| Métrica | Qué mide | Score bajo indica |
|---------|----------|-------------------|
| **Faithfulness** | Sin alucinaciones | LLM inventa información |
| **Answer Relevancy** | Respuesta aborda la query | Prompt mal diseñado |

---

## 🐛 Troubleshooting

### Error: "expected_output is required"

**Causa**: Estás pasando `test_queries` como lista de strings.

**Solución**: Convierte a formato de diccionarios:

```python
# Si tienes esto:
queries = ["query1", "query2"]

# Conviértelo así:
test_queries = [
    {"query": q, "expected_output": "Respuesta detallada."}
    for q in queries
]
```

### Error: "DeepEvalBaseLLM not found"

**Causa**: DeepEval no está instalado.

**Solución**:

```bash
pip install deepeval
```

### Visualizaciones no se ven bien

**Causa**: Falta matplotlib o seaborn.

**Solución**:

```bash
pip install matplotlib seaborn
```

---

## 📝 Próximos Pasos Recomendados

1. **Crear Ground Truth dataset**: Dedica tiempo a escribir respuestas esperadas de calidad para tus queries de prueba
2. **Ajustar thresholds**: Experimenta con diferentes valores según tus requisitos de calidad
3. **Analizar reasons**: Lee las explicaciones de DeepEval para entender por qué fallan ciertas queries
4. **Iterar en estrategias**: Usa el radar chart para identificar qué aspecto mejorar (retrieval vs generation)

---

## 🎯 Ventajas vs. Sistema Anterior

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| **Código** | ~600 líneas de prompts manuales | Métricas probadas de DeepEval |
| **Debugging** | Solo scores numéricos | Scores + explicaciones detalladas |
| **Reproducibilidad** | Dependía de quality de prompts | Framework estandarizado |
| **Mantenibilidad** | Difícil ajustar prompts | Configuración simple con thresholds |
| **Visualización** | 6 gráficos | 7 gráficos + radar chart |

---

## 📚 Referencias

- **DeepEval Docs**: https://docs.confident-ai.com/
- **RAG Triad Framework**: Métricas industria para evaluar RAG
- **Contextual Metrics**: Usan Ground Truth para validación más rigurosa
