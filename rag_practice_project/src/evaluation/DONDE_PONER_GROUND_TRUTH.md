# Dónde Poner las Respuestas Esperadas (Ground Truth)

## Respuesta Rápida

Las respuestas esperadas van en el archivo **`run_all_experiments.py`**, en la variable `TEST_QUERIES`.

## Formato Actual (Incorrecto para DeepEval)

```python
TEST_QUERIES = [
    "¿Cómo preparar hummus?",  # ❌ Solo strings
    "Dame recetas con quinoa"
]
```

## Formato Correcto para DeepEval

```python
TEST_QUERIES = [
    {
        "query": "¿Cómo preparar hummus?",
        "expected_output": "Para hacer hummus necesitas garbanzos cocidos, tahini, jugo de limón, ajo y aceite de oliva. Procesa todo en una licuadora hasta conseguir textura cremosa."
    },
    {
        "query": "Dame recetas con quinoa",
        "expected_output": "Bowl de quinoa con frijoles negros, ensalada mediterránea de quinoa, y quinoa con verduras asadas son opciones populares y nutritivas."
    }
]
```

## ¿Qué es el "expected_output"?

Es la **respuesta ideal** que tu sistema RAG debería generar. DeepEval compara:

1. ✅ **La respuesta generada** por tu estrategia RAG
2. ✅ **La respuesta esperada** (expected_output)  
3. ✅ **El contexto recuperado** (retrieval_context)

Y determina si:
- El contexto tiene la información necesaria (Contextual Recall)
- La respuesta es fiel al contexto sin alucinar (Faithfulness)
- La respuesta es relevante a la pregunta (Answer Relevancy)

## Ejemplo Completo

```python
# En run_all_experiments.py, reemplaza TEST_QUERIES por:

TEST_QUERIES = [
    {
        "query": "Menciona exactamente 3 recetas que contengan garbanzos.",
        "expected_output": "Tres recetas con garbanzos son: 1) Hummus (puré de garbanzos con tahini y limón), 2) Curry de garbanzos con leche de coco, 3) Ensalada de garbanzos con verduras frescas y vinagreta."
    },
    {
        "query": "¿Qué recetas tienen más de 15g de proteína por porción?",
        "expected_output": "Las recetas altas en proteína incluyen: Tofu scramble (18g), Lentejas estofadas (17g), Quinoa con frijoles negros (16g), y Bowl de tempeh marinado (20g)."
    },
    {
        "query": "Dame solo una receta de sopa que tenga menos de 200 calorías.",
        "expected_output": "Sopa de miso con tofu (150 calorías por porción). Incluye tofu suave, alga wakame, cebollín y pasta de miso en caldo dashi."
    },
    {
        "query": "Necesito recetas con quinoa que tengan al menos 12g de proteína.",
        "expected_output": "Bowl de quinoa con frijoles negros (16g de proteína) y Quinoa con tofu marinado (18g de proteína) cumplen con ese requisito."
    },
    {
        "query": "Tengo berenjena y garbanzos, ¿qué receta puedo hacer?",
        "expected_output": "Puedes preparar Curry de berenjena y garbanzos: saltea berenjena en cubos, añade garbanzos cocidos, leche de coco, pasta de curry, y sirve con arroz basmati."
    },
    {
        "query": "Dame dos opciones de platos que sean picantes.",
        "expected_output": "Tofu al estilo Mapo (picante con salsa de frijol fermentado) y Pad Thai vegetariano con chiles rojos son excelentes opciones picantes."
    }
]
```

## Si NO Tienes Respuestas Esperadas

Puedes usar un placeholder genérico (aunque reduce la precisión):

```python
TEST_QUERIES = [
    {"query": "¿Cómo preparar hummus?", "expected_output": "Instrucciones detalladas para preparar hummus."},
    {"query": "Recetas con quinoa", "expected_output": "Lista de recetas que usan quinoa como ingrediente principal."}
]
```

## Helper para Migración Rápida

Si tienes muchas queries actuales:

```python
# Script temporal en run_all_experiments.py

OLD_QUERIES = [
    "¿Cómo preparar hummus?",
    "Dame recetas con quinoa"
]

# Convertir automáticamente
TEST_QUERIES = [
    {
        "query": q,
        "expected_output": f"Respuesta detallada sobre: {q}"
    }
    for q in OLD_QUERIES
]
```

## Ver Más

- **Ejemplos completos**: `src/evaluation/test_queries_example.py`
- **Guía detallada**: `src/evaluation/DEEPEVAL_GUIDE.md`
- **Walkthrough**: Artifact `walkthrough.md`
