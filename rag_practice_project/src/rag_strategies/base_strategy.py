"""
Base class para todas las estrategias RAG
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

class BaseRAGStrategy(ABC):
    """
    Clase base abstracta para estrategias RAG
    """
    
    def __init__(self, name: str):
        """
        Inicializa la estrategia RAG
        
        Args:
            name: Nombre de la estrategia
        """
        self.name = name
        self.metrics = {
            "latency": [],
            "input_tokens": [],
            "output_tokens": [],
            "total_tokens": []
        }
    
    @abstractmethod
    def generate_response(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Genera una respuesta para la consulta
        
        Args:
            query: Consulta del usuario
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict con la respuesta y metadatos
        """
        pass
    
    def _measure_latency(self, func, *args, **kwargs):
        """
        Mide la latencia de una función
        
        Args:
            func: Función a medir
            *args: Argumentos posicionales
            **kwargs: Argumentos con nombre
            
        Returns:
            Tuple (resultado, latencia_ms)
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        return result, latency_ms
    
    def _track_metrics(self, latency: float, input_tokens: int, output_tokens: int):
        """
        Registra métricas de la ejecución
        
        Args:
            latency: Latencia en ms
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
        """
        self.metrics["latency"].append(latency)
        self.metrics["input_tokens"].append(input_tokens)
        self.metrics["output_tokens"].append(output_tokens)
        self.metrics["total_tokens"].append(input_tokens + output_tokens)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen de las métricas
        
        Returns:
            Dict con estadísticas de métricas
        """
        import numpy as np
        
        summary = {}
        for metric_name, values in self.metrics.items():
            if values:
                summary[metric_name] = {
                    "mean": np.mean(values),
                    "median": np.median(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "total": np.sum(values)
                }
        
        return summary
    
    def reset_metrics(self):
        """
        Reinicia las métricas
        """
        for key in self.metrics:
            self.metrics[key] = []
