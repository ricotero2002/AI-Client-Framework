"""
Sistema de evaluación para estrategias RAG
"""
from typing import Dict, Any, List
from pathlib import Path
import sys
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.llm_client import get_llm_client
from src.utils.config_loader import EVALUATION_LLM_PROVIDER, EVALUATION_MODEL

class RAGEvaluator:
    """
    Evaluador de estrategias RAG
    """
    
    def __init__(self):
        # Usar modelo específico para evaluación
        self.llm_client = get_llm_client(
            provider=EVALUATION_LLM_PROVIDER,
            model=EVALUATION_MODEL
        )
    
    def evaluate_response(self, query: str, response: str, context: List[str] = None) -> Dict[str, Any]:
        """
        Evalúa una respuesta generada
        
        Args:
            query: Consulta original
            response: Respuesta generada
            context: Contexto usado (opcional)
            
        Returns:
            Dict con métricas de calidad y modelo evaluador
        """
        metrics = {}
        
        # 1. Relevancia
        metrics["relevance"] = self._evaluate_relevance(query, response)
        
        # 2. Claridad
        metrics["clarity"] = self._evaluate_clarity(response)
        
        # 3. Concisión
        metrics["conciseness"] = self._evaluate_conciseness(response)
        
        # 4. Cumplimiento de requisitos
        metrics["requirement_fulfillment"] = self._evaluate_fulfillment(query, response)
        
        # 5. Precisión factual (si hay contexto)
        if context:
            metrics["factual_accuracy"] = self._evaluate_factual_accuracy(response, context)
        
        # Score general (promedio)
        metrics["overall_score"] = sum(metrics.values()) / len(metrics)
        
        # Agregar información del modelo evaluador
        metrics["evaluator_model"] = self.llm_client.model
        metrics["evaluator_provider"] = self.llm_client.provider
        
        return metrics
    
    def _evaluate_relevance(self, query: str, response: str) -> float:
        """
        Evalúa qué tan relevante es la respuesta a la consulta
        
        Returns:
            float: Score de 0 a 1
        """
        eval_prompt = f"""Evalúa la relevancia de esta respuesta a la consulta. Fíjate si cumple con los requisitos pedidos.

Consulta: {query}

Respuesta: {response}

¿Qué tan relevante es la respuesta? Califica de 0 a 10.
Responde solo con un número."""
        
        score = self._get_numeric_score(eval_prompt)
        return score / 10.0
    
    def _evaluate_clarity(self, response: str) -> float:
        """
        Evalúa la claridad de la respuesta
        
        Returns:
            float: Score de 0 a 1
        """
        eval_prompt = f"""Evalúa la claridad de esta respuesta. Es clara y fácil de entender?

Respuesta: {response}

¿Qué tan clara y fácil de entender es? Califica de 0 a 10.
Responde solo con un número."""
        
        score = self._get_numeric_score(eval_prompt)
        return score / 10.0
    
    def _evaluate_conciseness(self, response: str) -> float:
        """
        Evalúa la concisión de la respuesta
        
        Returns:
            float: Score de 0 a 1
        """
        # Métrica simple basada en longitud
        word_count = len(response.split())
        
        # Penalizar respuestas muy cortas o muy largas
        if word_count < 20:
            return 0.5
        elif word_count < 50:
            return 1.0
        elif word_count < 100:
            return 0.9
        elif word_count < 200:
            return 0.7
        else:
            return 0.5
    
    def _evaluate_fulfillment(self, query: str, response: str) -> float:
        """
        Evalúa si la respuesta cumple con lo solicitado
        
        Returns:
            float: Score de 0 a 1
        """
        eval_prompt = f"""Evalúa si esta respuesta cumple con lo solicitado en la consulta.

Consulta: {query}

Respuesta: {response}

¿La respuesta cumple con lo solicitado? Califica de 0 a 10.
Responde solo con un número."""
        
        score = self._get_numeric_score(eval_prompt)
        return score / 10.0
    
    def _evaluate_factual_accuracy(self, response: str, context: List[str]) -> float:
        """
        Evalúa la precisión factual basándose en el contexto
        
        Returns:
            float: Score de 0 a 1
        """
        # Pásale TODO el contexto que recibió el modelo, no solo los primeros 3
        context_str = "\n".join(context) 
        # Mejora el prompt para que el evaluador sea más "inteligente"
        eval_prompt = f"""Eres un auditor de calidad. Compara la respuesta con el contexto.
        Contexto: {context_str}
        Respuesta: {response}
        ¿La respuesta se apoya en el contexto? 
        0: Es un invento total.
        10: Todo está respaldado por el contexto.
        Responde solo con el número."""
        
        score = self._get_numeric_score(eval_prompt)
        return score / 10.0
    
    def _get_numeric_score(self, prompt: str) -> float:
        """
        Obtiene un score numérico del LLM
        
        Args:
            prompt: Prompt de evaluación
            
        Returns:
            float: Score de 0 a 10
        """
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt="Eres un evaluador objetivo. Responde solo con números.",
                max_tokens=5,
                temperature=0.1
            )
            
            score_text = response.get("response", "5").strip()
            score = float(score_text)
            return max(0, min(10, score))  # Clamp entre 0 y 10
        except:
            return 5.0  # Score neutral por defecto
    


class ExperimentRunner:
    """
    Ejecuta experimentos con múltiples estrategias RAG
    """
    
    def __init__(self, strategies: List, test_queries: List[str]):
        """
        Inicializa el runner de experimentos
        
        Args:
            strategies: Lista de estrategias RAG a evaluar
            test_queries: Lista de consultas de prueba
        """
        self.strategies = strategies
        self.test_queries = test_queries
        self.evaluator = RAGEvaluator()
        self.results = []
    
    def run_experiments(self) -> List[Dict[str, Any]]:
        """
        Ejecuta todos los experimentos
        
        Returns:
            Lista de resultados
        """
        print(f"Ejecutando experimentos con {len(self.strategies)} estrategias y {len(self.test_queries)} consultas...")
        
        for strategy in self.strategies:
            print(f"\nEvaluando estrategia: {strategy.name}")
            
            for query in self.test_queries:
                print(f"  Consulta: {query[:50]}...")
                
                # Generar respuesta
                response_data = strategy.generate_response(query)
                
                # Evaluar calidad
                quality_metrics = self.evaluator.evaluate_response(
                    query=query,
                    response=response_data["response"],
                    context=response_data.get("context")
                )
                
                # Calcular costo de generación de respuesta
                cost = self.evaluator.llm_client.calculate_cost(
                    input_tokens=response_data["input_tokens"],
                    output_tokens=response_data["output_tokens"],
                )
                
                # Extraer información de modelos extra usados por la estrategia
                extra_info = response_data.get("extra_info", {})
                
                # Advanced RAG - modelo para optimización de query
                if "query_optimization_model" in response_data:
                    extra_info["query_optimization_model"] = response_data["query_optimization_model"]
                
                # Agentic RAG - modelo para decisiones del agente
                if "agent_decision_model" in response_data:
                    extra_info["agent_decision_model"] = response_data["agent_decision_model"]
                    if "agent_actions" in response_data:
                        extra_info["agent_actions_count"] = len(response_data["agent_actions"])
                        extra_info["agent_actions_detail"] = response_data["agent_actions"]
                
                # Modular RAG - modelo del query processor y módulos usados
                if "query_processor_model" in response_data and response_data["query_processor_model"]:
                    extra_info["query_processor_model"] = response_data["query_processor_model"]
                if "modules" in response_data:
                    extra_info["modules_used"] = response_data["modules"]
                
                # Graph RAG - información del grafo
                if "graph_enabled" in response_data:
                    extra_info["graph_enabled"] = response_data["graph_enabled"]
                
                # Guardar resultado con información completa de modelos
                result = {
                    "timestamp": datetime.now().isoformat(),
                    "strategy": strategy.name,
                    "query": query,
                    "response": response_data["response"],
                    "latency_ms": response_data["latency_ms"],
                    "input_tokens": response_data["input_tokens"],
                    "output_tokens": response_data["output_tokens"],
                    "total_tokens": response_data["total_tokens"],
                    "cost_usd": cost,
                    "quality_metrics": quality_metrics,
                    "response_model": response_data["model"],
                    "response_provider": response_data.get("provider", self.evaluator.llm_client.provider),
                    "evaluator_model": quality_metrics.get("evaluator_model"),
                    "evaluator_provider": quality_metrics.get("evaluator_provider"),
                    "extra_info": extra_info if extra_info else None
                }
                
                self.results.append(result)
        
        print(f"\n✓ Experimentos completados: {len(self.results)} resultados")
        return self.results
    
    def save_results(self, output_path: Path):
        """
        Guarda los resultados en un archivo JSON
        
        Args:
            output_path: Ruta del archivo de salida
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"Resultados guardados en: {output_path}")
