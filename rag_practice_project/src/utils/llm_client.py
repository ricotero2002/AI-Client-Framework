"""
Wrapper para usar el client_factory existente del proyecto principal
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel

# Agregar el directorio padre al path para importar client_factory
parent_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(parent_dir))

from client_factory import create_client
from base_client import BaseAIClient, TokenUsage

# Importar configuración del proyecto RAG - usar import relativo al proyecto
import sys
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from rag_practice_project.src.utils.config_loader import DEFAULT_LLM_PROVIDER, DEFAULT_MODEL

class LLMClientWrapper:
    """
    Wrapper que adapta el client_factory existente para el proyecto RAG
    """
    
    def __init__(self, provider: str = DEFAULT_LLM_PROVIDER, model: str = DEFAULT_MODEL, langsmith: bool = False):
        """
        Inicializa el wrapper del cliente LLM
        
        Args:
            provider: Proveedor (openai o gemini)
            model: Nombre del modelo
            langsmith: Si habilitar LangSmith tracing
        """
        self.provider = provider
        self.model = model
        self.langsmith = langsmith
        
        # Crear cliente usando el factory existente
        self.client: BaseAIClient = create_client(provider, langsmith=langsmith)
        self.client.select_model(model)
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, few_shot_examples: Optional[list[dict[str, str]]] = None,
                max_tokens: int = 500, temperature: float = 0.7, structured_output: Optional[Type[BaseModel]] = None) -> Dict[str, Any]:
        """
        Genera una respuesta del LLM
        
        Args:
            prompt: Prompt del usuario
            system_prompt: Prompt del sistema (opcional)
            few_shot_examples: Ejemplos few-shot (opcional)
            max_tokens: Máximo de tokens a generar
            temperature: Temperatura de generación (0.0 a 1.0)
            structured_output: Schema Pydantic para output estructurado
            
        Returns:
            Dict con respuesta y metadatos
        """
        # Import Prompt class
        from prompt import Prompt
        
        # IMPORTANTE: Gemini tiene bug con temperature=0.0 exacto
        # Si recibimos 0.0, lo cambiamos a 0.01 para evitar respuestas None
        if temperature == 0.0:
            temperature = 0.01
        
        # Configurar parámetros de generación
        self.client.set_temperature(temperature)
        self.client.set_max_tokens(max_tokens)
        
        # Crear objeto Prompt en lugar de lista de mensajes
        prompt_obj = Prompt(use_delimiters=False)
        
        if system_prompt:
            prompt_obj.set_system(system_prompt)
        
        prompt_obj.set_user_input(prompt)

        if few_shot_examples:
            for example in few_shot_examples:
                prompt_obj.add_few_shot_example(example["query"], example["response"])
        
        if structured_output:
            prompt_obj.set_output_schema(structured_output)
        
        # Obtener respuesta pasando el objeto Prompt
        try:
            response_text, usage = self.client.get_response(prompt_obj)
            
            # Validar que la respuesta no sea None
            if response_text is None:
                print(f"⚠️ [LLM_CLIENT] get_response retornó None (Provider: {self.provider}, Model: {self.model}, Temp: {temperature})")
                response_text = ""  # Fallback a string vacío
                
        except Exception as e:
            print(f"❌ [LLM_CLIENT] Error en get_response: {e}")
            # Crear usage vacío y respuesta vacía
            response_text = ""
            usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        
        # Resetear configuración
        self.client.reset_generation_config()
        
        return {
            "response": response_text,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            },
            "model": self.model,
            "provider": self.provider
        }
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calcula el costo de una llamada al LLM
        
        Args:
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            
        Returns:
            float: Costo en USD
        """
        cost_estimate = self.client.estimate_cost(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens
        )
        return cost_estimate.total_cost

# Instancia global
_llm_client = None

def get_llm_client(provider: str = DEFAULT_LLM_PROVIDER, 
                   model: str = DEFAULT_MODEL,
                   langsmith: bool = False) -> LLMClientWrapper:
    """
    Obtiene la instancia global del cliente LLM
    
    Args:
        provider: Proveedor del LLM
        model: Modelo a usar
        langsmith: Si habilitar LangSmith tracing
        
    Returns:
        LLMClientWrapper: Instancia del cliente
    """
    global _llm_client
    if _llm_client is None or _llm_client.provider != provider or _llm_client.model != model:
        _llm_client = LLMClientWrapper(provider, model, langsmith)
    return _llm_client