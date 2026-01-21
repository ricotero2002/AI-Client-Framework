"""
OpenAI Client with LangSmith Integration
Extends OpenAIClient with LangSmith tracing
"""
from typing import Tuple, Optional
from openai_client import OpenAIClient
from base_client import TokenUsage
from langsmith import traceable, get_current_run_tree

class OpenAIClientSmith(OpenAIClient):
    """OpenAI client with LangSmith tracing enabled"""
    
    def __init__(self, api_key: Optional[str] = None, langsmith: bool = False):
        """Initialize OpenAI client with LangSmith wrapping"""
        # Call parent init
        super().__init__(api_key, langsmith)
        
        # Wrap with LangSmith if API key is present
        import os
        if os.environ.get("LANGCHAIN_API_KEY"):
            try:
                from langsmith.wrappers import wrap_openai
                self._client = wrap_openai(client=self._client)
            except ImportError:
                print("LangSmith not installed. Skipping tracing.")
        else:
            print("Warning: OpenAIClientSmith requires LANGCHAIN_API_KEY environment variable")
    
    @traceable(run_type="llm", name="OpenAI Generation")
    def get_response(
        self, 
        prompt, 
        **kwargs
    ) -> Tuple[str, TokenUsage]:
        """Get response from OpenAI API with LangSmith tracing"""
        # Call parent method
        response_text, token_usage = super().get_response(prompt, **kwargs)
        
        # Add metadata to LangSmith
        rt = get_current_run_tree()
        if rt:
            rt.add_metadata({
                "ls_provider": "openai",
                "ls_model_name": self.current_model,
                "total_tokens": token_usage.total_tokens,
                "input_tokens": token_usage.prompt_tokens,
                "output_tokens": token_usage.completion_tokens,
            })
        
        return response_text, token_usage
