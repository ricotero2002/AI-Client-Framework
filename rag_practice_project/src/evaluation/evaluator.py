"""
Sistema de evaluación RAG usando DeepEval Framework
Implementación limpia y robusta usando client_factory directamente
"""
import sys
import json
import time
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

# DeepEval imports
from deepeval.metrics import (
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    AnswerRelevancyMetric
)
from deepeval.test_case import LLMTestCase
from deepeval.models.base_model import DeepEvalBaseLLM

# Agregar parent dir para importar client_factory
parent_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(parent_dir))

from client_factory import create_client
from prompt import Prompt
from base_client import BaseAIClient

# Configuración local
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from rag_practice_project.src.utils.config_loader import EVALUATION_LLM_PROVIDER, EVALUATION_MODEL


class DeepEvalCustomLLM(DeepEvalBaseLLM):
    """
    Wrapper que conecta client_factory con DeepEval
    
    DeepEval requiere un objeto que implemente:
    - load_model() -> retorna el modelo
    - generate(prompt: str) -> str: generación síncrona
    - a_generate(prompt: str) -> str: generación async
    - get_model_name() -> str: nombre del modelo
    """
    
    def __init__(self, provider: str = EVALUATION_LLM_PROVIDER, model_name: str = EVALUATION_MODEL):
        """
        Inicializa el LLM wrapper para DeepEval
        
        Args:
            provider: 'openai' o 'gemini'
            model_name: Nombre específico del modelo
        """
        self.provider = provider
        self.model_name = model_name
        
        # Crear cliente usando client_factory
        self.client: BaseAIClient = create_client(provider, langsmith=False)
        self.client.select_model(model_name)
        
    def load_model(self):
        """DeepEval requiere este método. Retornamos el cliente ya inicializado"""
        return self.client
    
    def get_model_name(self) -> str:
        """Retorna el nombre del modelo"""
        return self.model_name
    
    def generate(self, prompt: str) -> str:
        """
        Generación síncrona requerida por DeepEval
        
        PASO A PASO:
        1. Crear Prompt object con system message
        2. Configurar temperatura baja para consistencia
        3. Llamar a client.get_response()
        4. Extraer y limpiar el texto
        5. Retornar string (DeepEval espera texto plano, no dict)
        """
        try:
            # PASO 1: Configurar parámetros
            # Usar temperatura muy baja para respuestas deterministas en evaluación
            # IMPORTANTE: NO usar 0.0 exacto, tiene bugs en Gemini
            self.client.set_temperature(0.05)
            self.client.set_max_tokens(5000)  # Suficiente para JSON de métricas
            
            # PASO 2: Crear objeto Prompt correctamente
            prompt_obj = Prompt(use_delimiters=False)
            
            # CRUCIAL: Gemini necesita system message para funcionar correctamente
            # Sin esto, algunos modelos retornan None
            system_msg = (
                "You are an expert AI evaluator. "
                "Respond ONLY with valid JSON. "
                "Do not add any explanation or markdown formatting."
            )
            prompt_obj.set_system(system_msg)
            prompt_obj.set_user_input(prompt)
            
            # PASO 3: Obtener respuesta
            response_text, usage = self.client.get_response(prompt_obj)
            
            # PASO 4: Validar respuesta
            if response_text is None or not isinstance(response_text, str):
                print(f"⚠️ [EVALUATOR] Modelo {self.model_name} retornó None/inválido")
                # Resetear y retornar JSON vacío
                self.client.reset_generation_config()
                return "{}"
            
            # PASO 5: Limpiar y resetear
            response_text = response_text.strip()
            self.client.reset_generation_config()
            
            return response_text
            
        except Exception as e:
            print(f"❌ [EVALUATOR] Error en generate(): {e}")
            import traceback
            traceback.print_exc()
            
            # Resetear configuración incluso si hay error
            try:
                self.client.reset_generation_config()
            except:
                pass
            
            return "{}"
    
    async def a_generate(self, prompt: str) -> str:
        """
        Generación async requerida por DeepEval
        
        Como nuestro client_factory no es async nativo,
        llamamos al método síncrono
        """
        return self.generate(prompt)


class RAGEvaluator:
    """
    Evaluador de estrategias RAG usando la Tríada RAG de DeepEval
    
    Métricas:
    - Retrieval: Contextual Precision, Recall, Relevancy
    - Generation: Faithfulness, Answer Relevancy
    """
    
    def __init__(self):
        """Inicializa el evaluador con métricas DeepEval"""
        
        # Crear LLM wrapper
        self.eval_llm = DeepEvalCustomLLM()
        
        # Cliente separado para cálculo de costos
        # (el wrapper de DeepEval no expone estimate_cost)
        self.cost_client: BaseAIClient = create_client(
            EVALUATION_LLM_PROVIDER,
            langsmith=False
        )
        self.cost_client.select_model(EVALUATION_MODEL)
        
        # Inicializar las 5 métricas RAG Triad
        # Threshold 0.5 = punto medio entre pasar/fallar
        self.metrics = {
            "contextual_precision": ContextualPrecisionMetric(
                threshold=0.5, 
                model=self.eval_llm, 
                include_reason=True
            ),
            "contextual_recall": ContextualRecallMetric(
                threshold=0.5,
                model=self.eval_llm,
                include_reason=True
            ),
            "contextual_relevancy": ContextualRelevancyMetric(
                threshold=0.5,
                model=self.eval_llm,
                include_reason=True
            ),
            "faithfulness": FaithfulnessMetric(
                threshold=0.5,
                model=self.eval_llm,
                include_reason=True
            ),
            "answer_relevancy": AnswerRelevancyMetric(
                threshold=0.5,
                model=self.eval_llm,
                include_reason=True
            )
        }
    
    def evaluate_response(
        self, 
        query: str, 
        response: str, 
        retrieval_context: List[str],
        expected_output: str
    ) -> Dict[str, Any]:
        """
        Evalúa una respuesta RAG usando DeepEval
        
        Args:
            query: Pregunta del usuario
            response: Respuesta generada por el sistema RAG
            retrieval_context: Lista de documentos/chunks recuperados
            expected_output: Respuesta esperada (Ground Truth)
            
        Returns:
            Dict con scores, reasons y overall_score
        """
        # Crear test case de DeepEval
        test_case = LLMTestCase(
            input=query,
            actual_output=response,
            retrieval_context=retrieval_context if retrieval_context else [],
            expected_output=expected_output
        )
        
        results = {}
        scores = []
        
        print(f"  [Evaluando]", end=" ", flush=True)
        
        # Ejecutar cada métrica
        for name, metric in self.metrics.items():
            try:
                metric.measure(test_case)
                
                results[name] = {
                    "score": metric.score,
                    "reason": metric.reason if metric.reason else "No reason provided"
                }
                scores.append(metric.score)
                print("✓", end=" ", flush=True)
                
            except Exception as e:
                print(f"✗({name[:3]})", end=" ", flush=True)
                results[name] = {
                    "score": 0.0,
                    "reason": f"Error: {str(e)}"
                }
                scores.append(0.0)
        
        print()  # Nueva línea
        
        # Calcular score promedio
        results["overall_score"] = sum(scores) / len(scores) if scores else 0.0
        results["evaluator_model"] = self.eval_llm.model_name
        results["evaluator_provider"] = self.eval_llm.provider
        
        return results


class ExperimentRunner:
    """Ejecuta experimentos con múltiples estrategias RAG"""
    
    def __init__(self, strategies: List, test_queries: List[Dict[str, str]]):
        """
        Args:
            strategies: Lista de objetos estrategia RAG
            test_queries: Lista de dicts con 'query' y 'expected_output'
        """
        self.strategies = strategies
        self.test_queries = test_queries
        self.evaluator = RAGEvaluator()
        self.results = []
    
    def run_experiments(self) -> List[Dict[str, Any]]:
        """Ejecuta todos los experimentos y retorna resultados"""
        
        print(f"Ejecutando experimentos: {len(self.strategies)} estrategias × {len(self.test_queries)} consultas\n")
        
        for strategy in self.strategies:
            print(f"\n{'='*60}")
            print(f"Estrategia: {strategy.name}")
            print(f"{'='*60}")
            
            for query_data in self.test_queries:
                query = query_data["query"]
                expected = query_data.get("expected_output", "No ground truth provided")
                
                print(f"\n📝 {query[:70]}...")
                
                # Generar respuesta RAG
                try:
                    response_data = strategy.generate_response(query)
                except Exception as e:
                    print(f"❌ Error generando respuesta: {e}")
                    continue
                
                # Evaluar calidad
                try:
                    # Obtener contexto de recuperación
                    retrieval_context = response_data.get("context", []) or response_data.get("contexts", [])
                    
                    # IMPORTANTE: DeepEval requiere lista de STRINGS, no objetos Document
                    if retrieval_context and not isinstance(retrieval_context, str):
                        retrieval_context_strings = []
                        for item in (retrieval_context if isinstance(retrieval_context, list) else [retrieval_context]):
                            if isinstance(item, str):
                                retrieval_context_strings.append(item)
                            elif hasattr(item, 'page_content'):  # Document object
                                retrieval_context_strings.append(item.page_content)
                            elif hasattr(item, 'text'):
                                retrieval_context_strings.append(item.text)
                            else:
                                retrieval_context_strings.append(str(item))
                        retrieval_context = retrieval_context_strings
                    elif isinstance(retrieval_context, str):
                        retrieval_context = [retrieval_context]
                    else:
                        retrieval_context = []
                    
                    quality_metrics = self.evaluator.evaluate_response(
                        query=query,
                        response=response_data["response"],
                        retrieval_context=retrieval_context,
                        expected_output=expected
                    )
                except Exception as e:
                    print(f"❌ Error en evaluación: {e}")
                    quality_metrics = {"overall_score": 0.0}
                
                # Calcular costo
                try:
                    cost_estimate = self.evaluator.cost_client.estimate_cost(
                        prompt_tokens=response_data.get("input_tokens", 0),
                        completion_tokens=response_data.get("output_tokens", 0)
                    )
                    cost = cost_estimate.total_cost
                except:
                    cost = 0.0
                
                # Guardar resultado
                result = {
                    "timestamp": datetime.now().isoformat(),
                    "strategy": strategy.name,
                    "query": query,
                    "expected_output": expected,
                    "response": response_data["response"],
                    "latency_ms": response_data.get("latency_ms", 0),
                    "input_tokens": response_data.get("input_tokens", 0),
                    "output_tokens": response_data.get("output_tokens", 0),
                    "total_tokens": response_data.get("total_tokens", 0),
                    "cost_usd": cost,
                    "quality_metrics": quality_metrics,
                    "response_model": response_data.get("model", "unknown"),
                    "response_provider": response_data.get("provider", "unknown"),
                    "evaluator_model": quality_metrics.get("evaluator_model"),
                    "extra_info": response_data.get("extra_info", {})
                }
                
                self.results.append(result)
                print(f"  Score: {quality_metrics.get('overall_score', 0):.3f}")
        
        return self.results
    
    def save_results(self, output_path: Path):
        """Guarda resultados en JSON"""
        try:
            with open(str(output_path), 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Resultados guardados: {output_path}")
        except Exception as e:
            print(f"❌ Error guardando resultados: {e}")