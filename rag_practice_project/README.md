# RAG Practice Project - Vegetarian Recipes 🥗

Este proyecto implementa y compara 6 estrategias diferentes de RAG (Retrieval-Augmented Generation) utilizando un dataset de recetas vegetarianas. El objetivo es analizar el trade-off entre **calidad de respuesta** y **latencia/costo**.

## 📊 Resumen Ejecutivo de Resultados

La historia principal de nuestros experimentos revela una clara disyuntiva entre INTELIGENCIA y VELOCIDAD:

-   🏆 **Ganador en Calidad:** **Graph RAG** (Score: 0.654). La estrategia más robusta, capaz de conectar puntos que otras perdieron.
-   ⚡ **Ganador en Velocidad:** **Naive RAG** (1.4s). 13 veces más rápido que Graph RAG, pero con calidad inferior.

### Análisis Comparativo

| Estrategia | Rol | Fortalezas | Debilidades | Uso Ideal |
| :--- | :--- | :--- | :--- | :--- |
| **Graph RAG** | 🧠 El Cerebro | Mejor calidad general (0.654), excelente fidelidad (0.958). | Latencia extrema (18.6s ±12s), costo computacional. | Reportes complejos, investigación offline. |
| **Agentic RAG** | 🕵️ El Agente | Fidelidad perfecta (1.0). Razonamiento en pasos. | Baja relevancia contextual (0.190), trae "ruido". | Tareas multi-paso complejas. |
| **Advanced RAG** | 📉 La Decepción | Técnicas avanzadas de retrieval. | Precisión baja (0.333), costo alto ($0.017), bajo ROI. | Neceista optimización de re-ranking. |
| **Naive RAG** | 🏎️ El Velocista | Muy rápido (1.4s) y barato. | Calidad inaceptable (0.421), recall crítico (0.08). | Prototipos, consultas triviales. |

> **Nota sobre Costos:** En el caso de Graph RAG, los costos no son exactos comparados con Agentic RAG debido al uso de herramientas externas de LLM para algunos pasos, pero se estima que su costo operativo real se sitúa entre Advanced y Agentic RAG.

---

## 🔍 Diagnóstico Profundo

### 1. El "Talón de Aquiles": Retrieval (Búsqueda) ❌
Todas las estrategias sufrieron aquí.
*   **Problema:** `contextual_recall_score` muy bajo (0.08 - 0.33).
*   **Significado:** El sistema no encuentra los documentos correctos en la base vectorial. Incluso las mejores estrategias pierden el 67% de la información relevante.
*   **Causa Raíz:** Dataset limitado y consultas intencionalmente complejas. El modelo de embeddings actual podría no estar capturando bien la semántica de recetas específicas.

### 2. La "Superestrella": Generation (Redacción) ✅
Los LLMs (Generator) están funcionando perfectamente.
*   **Agentic & Advanced:** 1.000 en Fidelidad (No alucinan).
*   **Conclusión:** El cuello de botella es la RECUPERACIN, no la generación.

---

## 🛠️ Estrategias Implementadas

1.  **No RAG**: Baseline. El modelo responde solo con su conocimiento pre-entrenado.
2.  **Naive RAG**: Recuperación simple + Generación.
3.  **Advanced RAG**: query expansion, retrieval avanzado y re-ranking.
4.  **Modular RAG**: Arquitectura flexible para intercambiar componentes.
5.  **Agentic RAG**: Agente autónomo que decide qué herramientas usar y cómo buscar.
6.  **Graph RAG**: Utiliza un Grafo de Conocimiento (Neo4j) para entender relaciones entre entidades.

## 🚀 Instalación y Uso

### Prerrequisitos
*   Python 3.10+
*   Cuenta de OpenAI / Google Gemini (API Keys)
*   Neo4j (para Graph RAG)

### Configuración
1.  Clonar el repositorio.
2.  Instalar dependencias:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configurar variables de entorno en `.env`:
    ```env
    OPENAI_API_KEY=sk-...
    GOOGLE_API_KEY=...
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USERNAME=neo4j
    NEO4J_PASSWORD=password
    ```

### Ejecución de Experimentos

Para correr la suite completa de pruebas y generar el reporte:

```bash
python run_all_experiments.py
```

### Scripts de Utilidad

*   **Cargar Datos:** `python src/data/load_dataset.py`
*   **Crear Vector DB:** `python src/vector_db/setup_chroma.py`
*   **Crear Grafo:** `python setup_graph.py`

## 🔮 Roadmap y Mejoras Futuras

Basado en los resultados, los siguientes pasos son críticos:

1.  **🚑 Prioridad 1: Arreglar el Retrieval** (URGENTE)
    *   Cambiar el modelo de embeddings por uno más robusto para dominio culinario.
    *   Aumentar el dataset para tener más cobertura de recetas.

2.  **🧹 Prioridad 2: Limpieza de Contexto**
    *   Mejorar el Re-ranker para Advanced y Agentic RAG (reducir ruido).
    *   El `contextual_relevancy` de 0.190 en Agentic RAG debe subir.

3.  **⚡ Optimización de Graph RAG**
    *   Pre-calcular el grafo y consultas frecuentes.
    *   Paralelizar llamadas del agente para bajar de los 18s de latencia.

4.  **💰 optimización de Costos**
    *   Revisar prompts de Advanced RAG para reducir consumo de tokens (actualmente el más caro ineficientemente).

---
*Proyecto realizado como práctica de arquitecturas RAG avanzadas.*
