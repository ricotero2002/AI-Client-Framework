import re
from typing import Optional
from nemoguardrails.actions import action

# Acción 1: Detectar Bee Movie
@action(is_system_action=True)
async def check_bee_movie_topic(context: Optional[dict] = None):
    """Chequea si el mensaje del usuario menciona 'Bee Movie'."""
    # CORRECCION: Usamos "user_message" o un string vacío si es None
    context = context or {}
    user_message = context.get("user_message") or context.get("last_user_message") or ""
    
    # Aseguramos que sea string y minúsculas
    user_message = str(user_message).lower()
    
    if "bee movie" in user_message or "la película de la abeja" in user_message:
        return True 
    return False 

# Acción 2: Enmascarar Código Interno
@action(is_system_action=True)
async def mask_internal_code(context: Optional[dict] = None):
    """
    Enmascara códigos con formato numero-letra-numero-letra-numero-letra-numero-letra.
    Ejemplo: 1a2b3c4d (8 caracteres)
    """
    # CORRECCION: Priorizamos 'user_message' que es el input actual en el rail
    context = context or {}
    user_message = context.get("user_message") or context.get("last_user_message") or ""
    
    # Defensa extra: Si por alguna razón sigue siendo None, la convertimos a string vacía
    if user_message is None:
        user_message = ""
    
    # Regex para: Digito, Letra, Digito, Letra... (4 pares = 8 caracteres)
    pattern = r'\b(?:\d[a-zA-Z]){4}\b'
    
    # Si encontramos el patrón, lo reemplazamos
    masked_message = re.sub(pattern, "[CODIGO_INTERNO_OCULTO]", user_message)
    
    return masked_message