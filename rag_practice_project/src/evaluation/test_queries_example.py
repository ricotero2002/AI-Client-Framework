"""
Ejemplo de dataset de prueba con Ground Truth para evaluación con DeepEval.

Este archivo muestra cómo estructurar las consultas de prueba con sus
respuestas esperadas (expected_output) para que DeepEval pueda evaluar
correctamente las métricas como Contextual Recall y Faithfulness.
"""

# FORMATO REQUERIDO: Lista de diccionarios con 'query' y 'expected_output'
TEST_QUERIES_WITH_GROUND_TRUTH = [
    {
        "query": "¿Cómo preparar hummus casero?",
        "expected_output": (
            "Para preparar hummus casero necesitas garbanzos cocidos (o de lata), "
            "tahini (pasta de sésamo), jugo de limón, ajo, aceite de oliva, sal y "
            "comino. Procesa todos los ingredientes en una licuadora hasta obtener "
            "una consistencia cremosa. Puedes ajustar la textura añadiendo agua. "
            "Sirve con un chorrito de aceite de oliva por encima."
        )
    },
    {
        "query": "Menciona exactamente 3 recetas que contengan garbanzos.",
        "expected_output": (
            "Tres recetas con garbanzos son: 1) Hummus (puré de garbanzos con tahini), "
            "2) Curry de garbanzos (garbanzos en salsa de curry con leche de coco), "
            "3) Ensalada de garbanzos (garbanzos con verduras frescas y vinagreta)."
        )
    },
    {
        "query": "¿Qué recetas tienen más de 15g de proteína por porción?",
        "expected_output": (
            "Las recetas altas en proteína incluyen: Tofu scramble (18g de proteína), "
            "Lentejas estofadas (17g), Quinoa con frijoles negros (16g), y "
            "Bowl de tempeh marinado (20g). Estas opciones son ideales para "
            "una dieta vegetariana alta en proteínas."
        )
    },
    {
        "query": "Dame una receta rápida para un desayuno con avena.",
        "expected_output": (
            "Overnight oats: mezcla 1/2 taza de avena con 1 taza de leche vegetal, "
            "deja reposar en el refrigerador toda la noche. Por la mañana, añade "
            "frutas frescas, nueces y un toque de miel o maple syrup. Listo en 5 minutos."
        )
    },
    {
        "query": "Necesito recetas con quinoa que tengan al menos 12g de proteína.",
        "expected_output": (
            "Bowl de quinoa con frijoles negros (16g proteína): cocina quinoa, "
            "mezcla con frijoles negros, aguacate, tomate, maíz y lima. "
            "Quinoa con tofu (18g proteína): saltea tofu marinado con quinoa "
            "y verduras. Ambas recetas superan los 12g de proteína por porción."
        )
    },
]

# NOTA: Si no tienes Ground Truth disponible, puedes usar un placeholder genérico:
# "expected_output": "Respuesta detallada sobre la consulta del usuario."
# 
# Sin embargo, esto reducirá la precisión de métricas como Contextual Recall.

# OPCIONAL: Si ya tienes queries simples, puedes agregar expected_output de forma programática:
SIMPLE_QUERIES = [
    "¿Cómo preparar un brownie de chocolate vegano?",
    "Dame dos opciones de platos que sean picantes.",
]

def convert_simple_to_ground_truth(simple_queries, default_output="Información detallada y precisa sobre la consulta."):
    """
    Convierte queries simples al formato requerido con placeholder de Ground Truth.
    
    Args:
        simple_queries: Lista de strings
        default_output: Respuesta esperada por defecto
        
    Returns:
        Lista de diccionarios con formato correcto
    """
    return [
        {"query": q, "expected_output": default_output}
        for q in simple_queries
    ]

# Ejemplo de uso:
if __name__ == "__main__":
    # Opción 1: Usar queries con Ground Truth manual
    print(f"Queries con Ground Truth: {len(TEST_QUERIES_WITH_GROUND_TRUTH)}")
    for i, item in enumerate(TEST_QUERIES_WITH_GROUND_TRUTH, 1):
        print(f"\n{i}. {item['query']}")
        print(f"   Expected: {item['expected_output'][:60]}...")
    
    # Opción 2: Convertir queries simples
    print(f"\n\nQueries convertidas: {len(SIMPLE_QUERIES)}")
    converted = convert_simple_to_ground_truth(SIMPLE_QUERIES)
    for i, item in enumerate(converted, 1):
        print(f"\n{i}. {item['query']}")
        print(f"   Expected: {item['expected_output']}")
