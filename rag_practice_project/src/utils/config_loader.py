"""
Helper para cargar configuración evitando conflictos de nombres de módulos
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Cargar el módulo de configuración ejecutando el archivo directamente
project_root = Path(__file__).parent.parent.parent
config_path = project_root / "config" / "config.py"

# Ejecutar el archivo de configuración y extraer las variables
# Proporcionar contexto necesario para que el config.py funcione
config_globals = {
    '__file__': str(config_path),
    '__name__': 'config',
    'Path': Path,
    'os': os,
    'load_dotenv': load_dotenv
}

with open(config_path, 'r', encoding='utf-8') as f:
    exec(f.read(), config_globals)

# Exportar todas las configuraciones
DEFAULT_LLM_PROVIDER = config_globals['DEFAULT_LLM_PROVIDER']
DEFAULT_MODEL = config_globals['DEFAULT_MODEL']
EVALUATION_LLM_PROVIDER = config_globals['EVALUATION_LLM_PROVIDER']
EVALUATION_MODEL = config_globals['EVALUATION_MODEL']
EXPANSION_LLM_PROVIDER = config_globals['EXPANSION_LLM_PROVIDER']
EXPANSION_MODEL = config_globals['EXPANSION_MODEL']
EMBEDDING_MODEL = config_globals['EMBEDDING_MODEL']
EMBEDDING_DIMENSION = config_globals['EMBEDDING_DIMENSION']
CHROMA_PERSIST_DIRECTORY = config_globals['CHROMA_PERSIST_DIRECTORY']
COLLECTION_NAME = config_globals['COLLECTION_NAME']
EVAL_SAMPLE_SIZE = config_globals['EVAL_SAMPLE_SIZE']
EVAL_METRICS = config_globals['EVAL_METRICS']
PROJECT_ROOT = config_globals['PROJECT_ROOT']
DATA_DIR = config_globals['DATA_DIR']
RAW_DATA_DIR = config_globals['RAW_DATA_DIR']
PROCESSED_DATA_DIR = config_globals['PROCESSED_DATA_DIR']
CHROMA_DIR = config_globals['CHROMA_DIR']
RESULTS_DIR = config_globals['RESULTS_DIR']
LOGS_DIR = config_globals['LOGS_DIR']
