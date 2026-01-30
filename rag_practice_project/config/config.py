"""
Configuración central del proyecto RAG
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Directorios del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CHROMA_DIR = DATA_DIR / "chroma_db"
RESULTS_DIR = PROJECT_ROOT / "results"
LOGS_DIR = PROJECT_ROOT / "logs"

# Crear directorios si no existen
for dir_path in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, CHROMA_DIR, RESULTS_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuración de modelo por defecto (para generar respuestas)
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "gemini")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash-lite")
#DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.0-flash-exp")

# Configuración de modelo para evaluación
EVALUATION_LLM_PROVIDER = os.getenv("EVALUATION_LLM_PROVIDER", "gemini")
EVALUATION_MODEL = os.getenv("EVALUATION_MODEL", "gemini-2.0-flash")

# Configuración de modelo para expansión de queries (Advanced RAG)
EXPANSION_LLM_PROVIDER = os.getenv("EXPANSION_LLM_PROVIDER", "gemini")
EXPANSION_MODEL = os.getenv("EXPANSION_MODEL", "gemini-2.5-flash")
print("[CONFIG] EXPANSION_MODEL", EXPANSION_MODEL)

# Configuración de embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))

# Configuración de ChromaDB
CHROMA_PERSIST_DIRECTORY = str(CHROMA_DIR)
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "vegan_recipes")

# Configuración de evaluación
EVAL_SAMPLE_SIZE = int(os.getenv("EVAL_SAMPLE_SIZE", "50"))
EVAL_METRICS = os.getenv("EVAL_METRICS", "latency,cost,relevance,clarity,conciseness").split(",")

# Configuración de logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# Neo4j Aura Configuration (Cloud Instance)
# ============================================================================
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://your-instance.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")  # Set in .env
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# ============================================================================
# Ollama Configuration (Local Free LLM) - OBSOLETO para Graph RAG
# ============================================================================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")  # Free model for entity extraction

# ============================================================================
# Graph RAG Configuration
# ============================================================================
# Graph Database Directory (for metadata/cache)
GRAPH_DIR = DATA_DIR / "graph_db"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

# Modelo para extracción de entidades en Graph RAG
# Ahora usa Gemini 2.5 Pro via client_factory (gratis)
GRAPH_EXTRACTION_LLM_PROVIDER = os.getenv("GRAPH_EXTRACTION_LLM_PROVIDER", "gemini")
GRAPH_EXTRACTION_MODEL = os.getenv("GRAPH_EXTRACTION_MODEL", "gemini-2.5-pro")

# Retrieval parameters
GRAPH_RETRIEVAL_TOP_K = int(os.getenv("GRAPH_RETRIEVAL_TOP_K", "5"))
GRAPH_SIMILARITY_TOP_K = int(os.getenv("GRAPH_SIMILARITY_TOP_K", "10"))

# Document chunking for graph
GRAPH_CHUNK_SIZE = int(os.getenv("GRAPH_CHUNK_SIZE", "1024"))
GRAPH_CHUNK_OVERLAP = int(os.getenv("GRAPH_CHUNK_OVERLAP", "200"))

# Graph extraction parameters
GRAPH_MAX_TRIPLETS_PER_CHUNK = int(os.getenv("GRAPH_MAX_TRIPLETS_PER_CHUNK", "10"))

LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")