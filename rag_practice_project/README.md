# RAG Practice Project - Vegetarian Recipes

Este proyecto implementa y evalúa diferentes estrategias de RAG (Retrieval-Augmented Generation) usando un dataset de recetas vegetarianas.

## 🎯 Objetivos

- Practicar embeddings y vector databases
- Implementar 6 estrategias diferentes de RAG
- Evaluar latencia, costo y calidad de respuestas
- Comparar resultados y analizar trade-offs

## 📊 Estrategias RAG Implementadas

1. **No RAG**: Baseline sin recuperación de contexto
2. **Naive RAG**: Recuperación → Lectura → Generación (básico)
3. **Advanced RAG**: Con pre-procesamiento y re-ranking
4. **Modular RAG**: Arquitectura modular e intercambiable
5. **Agentic RAG**: RAG con agentes autónomos
6. **Graph RAG**: RAG basado en grafos de conocimiento

## 🛠️ Stack Tecnológico

- **Embeddings**: Modelo gratuito (sentence-transformers)
- **Vector Database**: ChromaDB
- **Dataset**: Vegan Recipes Dataset (Kaggle)
- **LLM**: Configurable (OpenAI/Gemini)

## 📁 Estructura del Proyecto

```
rag_practice_project/
├── data/                      # Datos y dataset
├── src/                       # Código fuente
│   ├── embeddings/           # Utilidades de embeddings
│   ├── vector_db/            # Gestión de ChromaDB
│   ├── rag_strategies/       # Implementaciones RAG
│   ├── evaluation/           # Sistema de evaluación
│   └── utils/                # Utilidades generales
├── experiments/              # Scripts de experimentos
├── results/                  # Resultados y análisis
├── config/                   # Configuraciones
└── notebooks/                # Jupyter notebooks exploratorios
```

## 🚀 Instalación

```bash
pip install -r requirements.txt
```

## 📝 Uso

1. **Cargar datos**:
```bash
python src/data/load_dataset.py
```

2. **Crear embeddings y vector DB**:
```bash
python src/vector_db/setup_chroma.py
```

3. **Ejecutar experimentos**:
```bash
python experiments/run_all_experiments.py
```

4. **Generar análisis**:
```bash
python src/evaluation/generate_report.py
```

## 📈 Métricas de Evaluación

- **Latencia**: Tiempo de respuesta
- **Costo**: Tokens utilizados y costo estimado
- **Calidad**:
  - Relevancia al prompt
  - Claridad de la respuesta
  - Concisión
  - Cumplimiento de requisitos
  - Precisión factual

## 📊 Resultados

Los resultados se guardan en `results/` con:
- Métricas comparativas
- Visualizaciones
- Análisis detallado por estrategia


## Modelos a definir
- Generar el prompt (Default) -> gemini-2.5-flash-lite
- Modelo de evaluacion -> gemini-2.5-flash
- Expandir prompt en advanced rag -> gemini-2.0-flash-exp
