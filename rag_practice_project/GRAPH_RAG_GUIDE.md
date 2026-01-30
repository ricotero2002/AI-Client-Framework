# Knowledge Graph RAG - Guía Completa

## 📖 ¿Qué es Graph RAG?

**Graph RAG** (Graph Retrieval-Augmented Generation) es una evolución del RAG tradicional que combina:

1. **Búsqueda vectorial** (semántica) - igual que Vector RAG
2. **Grafo de conocimiento** - entidades y sus relaciones
3. **Traversal de grafo** - navegación por conexiones

### Vector RAG vs Graph RAG

| Característica | Vector RAG | Graph RAG |
|---------------|------------|-----------|
| **Búsqueda** | Solo similitud semántica | Semántica + relaciones |
| **Contexto** | Documentos aislados | Documentos + conexiones |
| **Queries complejas** | ❌ Limitado | ✅ Multi-hop reasoning |
| **Velocidad ingesta** | ⚡ Rápida | 🐌 Más lenta (extracción) |
| **Costo ingesta** | 💰 Bajo (solo embeddings) | 💰💰 Medio (LLM + embeddings) |
| **Velocidad query** | ⚡ Muy rápida | 🐌 Un poco más lenta |
| **Descubrimiento** | ❌ No | ✅ Encuentra conexiones |

### ¿Cuándo usar cada uno?

**Usa Vector RAG cuando:**
- Solo necesitas búsqueda por similitud
- Tus documentos son independientes
- Priorizas velocidad sobre profundidad
- Tu dataset cambia frecuentemente

**Usa Graph RAG cuando:**
- Necesitas entender relaciones entre entidades
- Haces preguntas tipo "¿qué tienen en común X y Y?"
- Quieres explorar conexiones en tus datos
- Tienes un dominio rico en entidades (productos, personas, conceptos)

---

## 🚀 Setup Inicial

### 1. Requisitos Previos

#### Neo4j Aura (Gratuito)

Ya tienes una instancia de Neo4j Aura. Asegúrate de tener:

- **URI**: `neo4j+s://xxxxx.databases.neo4j.io`
- **Usuario**: `neo4j`
- **Password**: Tu contraseña de Aura

#### Ollama (LLM Local Gratuito)

Ya tienes Ollama instalado. Verifica que esté corriendo:

```bash
# Verificar que Ollama está activo
ollama list

# Si no tienes un modelo, descarga uno (recomendado: llama2 o mistral)
ollama pull llama2
```

### 2. Instalar Dependencias

```bash
# Instalar dependencias de Graph RAG
pip install -r requirements_graph.txt
```

### 3. Configurar Variables de Entorno

Copia `.env.example` a `.env` y actualiza:

```bash
# Neo4j Aura
NEO4J_URI=neo4j+s://tu-instancia.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=tu_password_aqui
NEO4J_DATABASE=neo4j

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### 4. Verificar Conexiones

```bash
# Test Neo4j
python -c "from src.graph_db.neo4j_manager import test_neo4j_connection; test_neo4j_connection()"

# Test Ollama
ollama run llama2 "Hello, test"
```

---

## 📊 Construcción del Knowledge Graph

### Setup Básico

```bash
# Construir grafo con dataset completo
python setup_graph.py

# Construir con muestra para pruebas (más rápido)
python setup_graph.py --sample 50

# No limpiar base de datos existente
python setup_graph.py --no-reset
```

### ¿Qué hace `setup_graph.py`?

1. **Conecta a Neo4j Aura** - verifica credenciales
2. **Carga dataset** - recetas veganas procesadas
3. **Prepara documentos** - convierte a formato LlamaIndex
4. **Extrae entidades** - usa Ollama para identificar:
   - Ingredientes (quinoa, avocado, etc.)
   - Categorías (breakfast, dinner, etc.)
   - Relaciones (contains, used_in, etc.)
5. **Construye grafo** - almacena en Neo4j
6. **Crea embeddings** - almacena en ChromaDB
7. **Prueba queries** - valida el sistema

### Tiempo Estimado

- **50 recetas**: ~5-10 minutos
- **500 recetas**: ~30-60 minutos
- **Todo el dataset**: Varias horas

> ⚠️ **Nota**: La extracción de entidades con LLM es el paso más lento.

---

## 🔍 Cómo Funciona PropertyGraphIndex

### Arquitectura

```
┌─────────────────────────────────────────────────┐
│              PROPERTYGRАPHINDEX                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────────┐      ┌─────────────────┐ │
│  │   Neo4j (Aura)   │      │   ChromaDB      │ │
│  │                  │      │                 │ │
│  │  • Nodos         │      │  • Embeddings   │ │
│  │  • Relaciones    │◄────►│  • IDs          │ │
│  │  • Propiedades   │      │  • Metadata     │ │
│  └──────────────────┘      └─────────────────┘ │
│         ▲                         ▲             │
│         │                         │             │
│         └─────────┬───────────────┘             │
│                   │                             │
│         ┌─────────▼──────────┐                  │
│         │  Hybrid Retriever  │                  │
│         │                    │                  │
│         │  • Vector Search   │                  │
│         │  • Synonym Expand  │                  │
│         │  • Graph Traverse  │                  │
│         └────────────────────┘                  │
└─────────────────────────────────────────────────┘
```

### Flujo de Consulta

1. **Query**: "recetas con quinoa altas en proteína"

2. **Vector Search**: Busca en ChromaDB documentos similares
   - Encuentra recetas con quinoa

3. **Synonym Expansion**: LLM expande términos
   - "quinoa" → también busca "granos", "cereales"
   - "proteína" → también "protein-rich", "high-protein"

4. **Graph Traversal**: Navega relaciones en Neo4j
   - Encuentra ingredientes relacionados
   - Descubre categorías conectadas
   - Expande contexto

5. **Response**: Combina todo y genera respuesta

---

## 🆚 Comparación de Sistemas

### Ejecutar Comparación

```bash
# Comparación con muestra pequeña (rápido)
python compare_systems.py --sample 50

# Comparación con más datos (más preciso)
python compare_systems.py --sample 200
```

### Métricas que Compara

1. **Tiempo de Ingesta**
   - Vector RAG: Solo embeddings
   - Graph RAG: Embeddings + extracción de entidades

2. **Costo de Ingesta**
   - Vector RAG: $0 (solo embeddings locales)
   - Graph RAG: $0 (Ollama es local y gratuito)
   - Nota: Ollama tiene costo computacional

3. **Tiempo de Consulta**
   - Vector RAG: ~50-100ms
   - Graph RAG: ~200-500ms (más complejo)

4. **Calidad de Respuestas**
   - Vector RAG: Buena para queries simples
   - Graph RAG: Mejor para queries complejas

### Resultados Esperados

```
📊 RESULTADOS:

1. TIEMPO DE INGESTA:
   Vector RAG: 5.2s
   Graph RAG:  245.8s
   → Ganador:  Vector RAG
   → Factor:   47.3x más rápido

2. COSTO DE INGESTA:
   Vector RAG: 0 tokens
   Graph RAG:  ~25,000 tokens (Ollama = gratis)

3. RENDIMIENTO DE CONSULTA:
   Vector RAG: 85ms
   Graph RAG:  320ms
   → Ganador:  Vector RAG
   → Factor:   3.8x más rápido

4. CAPACIDADES:
   Vector RAG: ✓ Rápido, ✗ No entiende relaciones
   Graph RAG:  ✓ Relaciones, ✓ Multi-hop, ✗ Más lento
```

---

## 💡 Uso Programático

### Ejemplo 1: Consulta Simple

```python
from src.graph_db.neo4j_manager import Neo4jManager
from src.graph_db.graph_builder import GraphBuilder
from src.graph_db.graph_retriever import GraphRetriever

# Cargar índice existente (asume que ya corriste setup_graph.py)
neo4j_manager = Neo4jManager()

# Crear retriever (necesitas el index, ver setup_graph.py)
# Este ejemplo asume que ya construiste el grafo
```

### Ejemplo 2: Comparación Personalizada

```python
from compare_systems import SystemComparison

# Crear comparador
comp = SystemComparison(sample_size=100)

# Ejecutar
comp.run()

# Resultados en: results/system_comparison.json
# Gráficos en: results/system_comparison.png
```

---

## 🔧 Exploración del Grafo

### Neo4j Browser

1. Abre tu Neo4j Aura Console
2. Haz clic en "Open with Neo4j Browser"
3. Ejecuta queries Cypher:

```cypher
// Ver todos los nodos (limitado)
MATCH (n) RETURN n LIMIT 25

// Contar nodos por tipo
MATCH (n) RETURN labels(n) as tipo, count(*) as cantidad

// Buscar recetas con un ingrediente específico
MATCH (r:Recipe)-[:CONTAINS]->(i:Ingredient {name: "quinoa"})
RETURN r, i

// Encontrar ingredientes comunes entre dos recetas
MATCH (r1:Recipe {title: "Receta1"})-[:CONTAINS]->(i:Ingredient)<-[:CONTAINS]-(r2:Recipe {title: "Receta2"})
RETURN i.name as ingrediente_comun

// Estadísticas del grafo
CALL apoc.meta.stats()
```

---

## 📈 Mejores Prácticas

### Para Ingesta

1. **Empieza pequeño**: Usa `--sample 10` para probar
2. **Incrementa gradualmente**: 50 → 100 → 500
3. **Monitorea memoria**: Ollama puede usar bastante RAM
4. **Usa modelos eficientes**: `llama2` es un buen balance

### Para Consultas

1. **Queries específicas**: "recetas con quinoa y alta proteína"
2. **Queries relacionales**: "¿qué comparten recetas X y Y?"
3. **Exploración**: "ingredientes conectados con avocado"

### Optimización

1. **Chunk size**: Ajusta `GRAPH_CHUNK_SIZE` según tus docs
2. **Top K**: Balancea `GRAPH_SIMILARITY_TOP_K` y `GRAPH_RETRIEVAL_TOP_K`
3. **Modelos**: Prueba `mistral` si `llama2` es muy lento

---

## 🐛 Troubleshooting

### Error: "No se puede conectar a Neo4j"

```bash
# Verifica URI y credenciales en .env
# Asegúrate que tu instancia Aura esté activa
```

### Error: "Ollama no responde"

```bash
# Verifica que Ollama esté corriendo
ollama list

# Reinicia Ollama si es necesario
```

### Construcción muy lenta

```bash
# Usa una muestra más pequeña
python setup_graph.py --sample 20

# O usa un modelo más rápido (pero menos preciso)
# Cambia OLLAMA_MODEL en .env a un modelo más pequeño
```

### Out of memory

```bash
# Reduce chunk size en config.py
GRAPH_CHUNK_SIZE = 512  # en vez de 1024

# O procesa en lotes más pequeños
```

---

## 📚 Recursos

- **LlamaIndex Docs**: https://docs.llamaindex.ai/
- **Neo4j Cypher**: https://neo4j.com/docs/cypher-manual/
- **Ollama Models**: https://ollama.ai/library
- **PropertyGraphIndex**: https://docs.llamaindex.ai/en/stable/examples/property_graph/

---

## 🎯 Próximos Pasos

1. ✅ Ejecuta `setup_graph.py` con una muestra pequeña
2. ✅ Explora el grafo en Neo4j Browser
3. ✅ Ejecuta `compare_systems.py` para ver diferencias
4. ✅ Prueba queries complejas
5. 🚀 Integra Graph RAG en tu aplicación principal

---

**¿Preguntas?** Revisa el código en `src/graph_db/` o abre un issue.
