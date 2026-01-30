# Graph RAG - Quick Start

## ¿Qué es esto?

Implementación de **Knowledge Graph RAG** que combina:
- Neo4j (grafo de entidades y relaciones)
- ChromaDB (búsqueda vectorial)
- LlamaIndex PropertyGraphIndex (orquestación)
- Ollama/llama2 (LLM local gratuito)

## 🚀 Setup Rápido

### 1. Instalar dependencias

```bash
pip install -r requirements_graph.txt
```

### 2. Configurar credenciales

Crea/edita `.env`:

```bash
# Neo4j Aura
NEO4J_URI=neo4j+s://tu-instancia.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=tu_password
NEO4J_DATABASE=neo4j

# Ollama
OLLAMA_MODEL=llama2
```

### 3. Verificar conexiones

```bash
# Test Neo4j
python src/graph_db/neo4j_manager.py

# Test Ollama
ollama list
```

### 4. Construir grafo (prueba)

```bash
# Empieza con muestra pequeña (~5-10 min)
python setup_graph.py --sample 20
```

### 5. Comparar con Vector RAG

```bash
python compare_systems.py --sample 50
```

## 📖 Documentación Completa

Ver **[GRAPH_RAG_GUIDE.md](./GRAPH_RAG_GUIDE.md)** para:
- Conceptos y arquitectura
- Guía paso a paso
- Ejemplos de uso
- Queries Cypher
- Troubleshooting

## 📁 Archivos Principales

```
src/graph_db/
├── neo4j_manager.py      # Conexión Neo4j
├── graph_builder.py      # Construcción del grafo
└── graph_retriever.py    # Retrieval híbrido

setup_graph.py            # Script de setup
compare_systems.py        # Comparación de sistemas
GRAPH_RAG_GUIDE.md       # Guía completa
```

## 🆚 Vector RAG vs Graph RAG

| | Vector RAG | Graph RAG |
|---|---|---|
| **Velocidad ingesta** | ⚡ Rápida | 🐌 Lenta (LLM) |
| **Velocidad query** | ⚡ ~50-100ms | 🐌 ~200-500ms |
| **Capacidades** | Similitud | Similitud + Relaciones |
| **Costo** | $0 | $0 (Ollama local) |

**Usa Graph RAG para:**
- Queries multi-hop ("¿qué comparten X y Y?")
- Descubrir relaciones entre entidades
- Exploración de conocimiento

**Usa Vector RAG para:**
- Búsqueda simple por similitud
- Velocidad es crítica
- Dataset cambia frecuentemente

## 💡 Próximos Pasos

1. ✅ Instala dependencias
2. ✅ Configura `.env`
3. ✅ Ejecuta `setup_graph.py --sample 20`
4. ✅ Explora en Neo4j Browser
5. ✅ Ejecuta `compare_systems.py`
6. 🚀 Lee [GRAPH_RAG_GUIDE.md](./GRAPH_RAG_GUIDE.md) para más detalles

## 🐛 Problemas Comunes

**"No se puede conectar a Neo4j"**
- Verifica URI y password en `.env`
- Asegúrate que tu instancia Aura esté activa

**"Ollama no responde"**
```bash
ollama list  # Verifica que esté corriendo
```

**Setup muy lento**
- Es normal! Extracción de entidades toma tiempo
- Usa `--sample 10` para pruebas más rápidas

---

**Documentación completa**: [GRAPH_RAG_GUIDE.md](./GRAPH_RAG_GUIDE.md)
