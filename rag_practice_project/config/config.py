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
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
#DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.0-flash-exp")

# Configuración de modelo para evaluación
EVALUATION_LLM_PROVIDER = os.getenv("EVALUATION_LLM_PROVIDER", "gemini")
EVALUATION_MODEL = os.getenv("EVALUATION_MODEL", "gemini-2.0-flash-exp")

# Configuración de modelo para expansión de queries (Advanced RAG)
EXPANSION_LLM_PROVIDER = os.getenv("EXPANSION_LLM_PROVIDER", "gemini")
EXPANSION_MODEL = os.getenv("EXPANSION_MODEL", "gemini-2.5-flash")

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
