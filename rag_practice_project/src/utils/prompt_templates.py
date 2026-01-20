"""
Prompt Templates for RAG Strategies
Centralized prompt management using the Prompt class from the parent project
"""
import sys
from pathlib import Path

# Add parent directory to path to import Prompt
parent_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(parent_dir))

from prompt import Prompt


def create_no_rag_prompt(query: str) -> Prompt:
    """
    Create a prompt for the No RAG strategy (baseline)
    
    Args:
        query: User's question
        
    Returns:
        Prompt object configured for No RAG strategy
    """
    system_message = """Eres un asistente experto en recetas vegetarianas y veganas.
Responde de manera clara, concisa y útil a las preguntas sobre recetas.
Proporciona información práctica y específica cuando sea posible."""
    
    return (Prompt(use_delimiters=False)
            .set_system(system_message)
            .set_user_input(query))


def create_naive_rag_prompt(query: str, context: str) -> Prompt:
    """
    Create a prompt for Naive RAG strategy with context injection
    
    Args:
        query: User's question
        context: Retrieved context from vector database
        
    Returns:
        Prompt object configured for Naive RAG strategy
    """
    system_message = """Eres un asistente experto en recetas vegetarianas y veganas.
Usa el contexto proporcionado para responder a las preguntas del usuario.
Si el contexto no contiene información relevante, indícalo claramente.
Responde de manera clara, concisa y útil."""
    
    user_message = f"""Contexto de recetas:
{context}

---

Pregunta del usuario: {query}

Por favor, responde basándote en el contexto proporcionado."""
    
    return (Prompt(use_delimiters=False)
            .set_system(system_message)
            .set_user_input(user_message))


def create_advanced_rag_prompt(query: str, context: str, expanded_queries: list = None) -> Prompt:
    """
    Create a prompt for Advanced RAG strategy with query expansion
    
    Args:
        query: Original user's question
        context: Retrieved context from vector database
        expanded_queries: List of expanded/reformulated queries (optional)
        
    Returns:
        Prompt object configured for Advanced RAG strategy
    """
    system_message = """Eres un asistente experto en recetas vegetarianas y veganas.
Analiza cuidadosamente el contexto proporcionado y responde de manera precisa.
Si se proporcionan consultas expandidas, úsalas para entender mejor la intención del usuario.
Proporciona respuestas detalladas y bien fundamentadas."""
    
    user_message_parts = []
    
    if expanded_queries:
        user_message_parts.append("Consultas relacionadas:")
        for i, eq in enumerate(expanded_queries, 1):
            user_message_parts.append(f"{i}. {eq}")
        user_message_parts.append("")
    
    user_message_parts.append(f"Contexto de recetas:\n{context}")
    user_message_parts.append("\n---\n")
    user_message_parts.append(f"Pregunta original: {query}")
    user_message_parts.append("\nPor favor, proporciona una respuesta completa basándote en el contexto.")
    
    user_message = "\n".join(user_message_parts)
    
    return (Prompt(use_delimiters=False)
            .set_system(system_message)
            .set_user_input(user_message))


def create_query_expansion_prompt(query: str) -> Prompt:
    """
    Create a prompt for query expansion (used in Advanced RAG)
    
    Args:
        query: Original user query
        
    Returns:
        Prompt object for generating expanded queries
    """
    system_message = """Eres un experto en reformular consultas para mejorar la búsqueda de información.
Genera variaciones de la consulta original que capturen diferentes aspectos de la intención del usuario."""
    
    user_message = f"""Consulta original: {query}

Genera 3 variaciones de esta consulta que:
1. Usen sinónimos o términos relacionados
2. Reformulen la pregunta desde diferentes ángulos
3. Mantengan la intención original

Responde solo con las 3 consultas, una por línea, sin numeración ni explicaciones adicionales."""
    
    return (Prompt(use_delimiters=False)
            .set_system(system_message)
            .set_user_input(user_message))


def create_modular_rag_prompt(query: str, context: str, metadata: dict = None) -> Prompt:
    """
    Create a prompt for Modular RAG strategy with metadata
    
    Args:
        query: User's question
        context: Retrieved context
        metadata: Additional metadata about the context (scores, sources, etc.)
        
    Returns:
        Prompt object configured for Modular RAG strategy
    """
    system_message = """Eres un asistente experto en recetas vegetarianas y veganas.
Usa el contexto y los metadatos proporcionados para dar respuestas precisas y bien fundamentadas.
Considera la relevancia de cada fragmento de contexto al formular tu respuesta."""
    
    user_message_parts = [f"Contexto de recetas:\n{context}"]
    
    if metadata:
        user_message_parts.append("\nMetadatos del contexto:")
        for key, value in metadata.items():
            user_message_parts.append(f"- {key}: {value}")
    
    user_message_parts.append(f"\n---\n\nPregunta: {query}")
    user_message_parts.append("\nPor favor, responde basándote en el contexto y metadatos proporcionados.")
    
    user_message = "\n".join(user_message_parts)
    
    return (Prompt(use_delimiters=False)
            .set_system(system_message)
            .set_user_input(user_message))
