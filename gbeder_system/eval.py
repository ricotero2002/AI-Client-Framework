"""
DeepEval Integration for GBeder System
LLM-based evaluation using Faithfulness and Answer Relevancy metrics.
"""
from typing import Dict, Any, List, Tuple
import logging

try:
    from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False
    logging.warning("DeepEval not installed. Evaluation metrics will use fallback scoring.")

from gbeder_system.config import EVAL_THRESHOLDS
from gbeder_system.state import GBederState

logger = logging.getLogger(__name__)


class DeepEvalNode:
    """
    DeepEval evaluation node for assessing draft quality.
    Uses Faithfulness and Answer Relevancy metrics.
    """
    
    def __init__(self, use_deepeval: bool = True):
        """
        Initialize DeepEval node.
        
        Args:
            use_deepeval: Whether to use DeepEval library (requires installation)
        """
        self.use_deepeval = use_deepeval and DEEPEVAL_AVAILABLE
        
        if self.use_deepeval:
            # Initialize metrics
            self.faithfulness_metric = FaithfulnessMetric(
                threshold=EVAL_THRESHOLDS["faithfulness"],
                model="gpt-4o-mini",  # DeepEval's evaluation model
                include_reason=True
            )
            
            self.relevancy_metric = AnswerRelevancyMetric(
                threshold=EVAL_THRESHOLDS["answer_relevancy"],
                model="gpt-4o-mini",
                include_reason=True
            )
            
            logger.info("DeepEval metrics initialized")
        else:
            logger.warning("Using fallback evaluation (DeepEval not available)")
    
    def evaluate_draft(
        self,
        query: str,
        draft: str,
        context: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, float], str]:
        """
        Evaluate a draft using DeepEval metrics.
        
        Args:
            query: Original research query
            draft: Generated draft to evaluate
            context: Retrieved context/sources
            
        Returns:
            Tuple of (scores_dict, feedback_string)
        """
        if self.use_deepeval:
            return self._evaluate_with_deepeval(query, draft, context)
        else:
            return self._evaluate_fallback(query, draft, context)
    
    def _evaluate_with_deepeval(
        self,
        query: str,
        draft: str,
        context: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, float], str]:
        """Evaluate using DeepEval library."""
        # Prepare context for evaluation
        retrieval_context = [
            src.get("content", "") for src in context if src.get("content")
        ]
        
        # Create test case
        test_case = LLMTestCase(
            input=query,
            actual_output=draft,
            retrieval_context=retrieval_context
        )
        
        scores = {}
        feedback_parts = []
        
        # Evaluate faithfulness
        try:
            self.faithfulness_metric.measure(test_case)
            scores["faithfulness"] = self.faithfulness_metric.score
            
            if self.faithfulness_metric.score < EVAL_THRESHOLDS["faithfulness"]:
                feedback_parts.append(
                    f"**Faithfulness Issue (Score: {self.faithfulness_metric.score:.2f}):** "
                    f"{self.faithfulness_metric.reason}"
                )
            
            logger.info(f"Faithfulness score: {self.faithfulness_metric.score}")
        except Exception as e:
            logger.error(f"Faithfulness evaluation error: {str(e)}")
            scores["faithfulness"] = 0.5
            feedback_parts.append(f"Faithfulness evaluation failed: {str(e)}")
        
        # Evaluate answer relevancy
        try:
            self.relevancy_metric.measure(test_case)
            scores["answer_relevancy"] = self.relevancy_metric.score
            
            if self.relevancy_metric.score < EVAL_THRESHOLDS["answer_relevancy"]:
                feedback_parts.append(
                    f"**Relevancy Issue (Score: {self.relevancy_metric.score:.2f}):** "
                    f"{self.relevancy_metric.reason}"
                )
            
            logger.info(f"Answer relevancy score: {self.relevancy_metric.score}")
        except Exception as e:
            logger.error(f"Relevancy evaluation error: {str(e)}")
            scores["answer_relevancy"] = 0.5
            feedback_parts.append(f"Relevancy evaluation failed: {str(e)}")
        
        # Generate feedback
        if feedback_parts:
            feedback = "\n\n".join(feedback_parts)
            feedback += "\n\n**Recommendations:**\n"
            feedback += "- Ensure all claims are supported by the provided sources\n"
            feedback += "- Stay focused on the original query\n"
            feedback +="- Add citations for key facts and statistics\n"
        else:
            feedback = "Draft meets quality thresholds. Good work!"
        
        return scores, feedback
    
    def _evaluate_fallback(
        self,
        query: str,
        draft: str,
        context: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, float], str]:
        """Fallback evaluation using simple heuristics."""
        scores = {}
        feedback_parts = []
        
        # Simple faithfulness check: draft length vs context
        draft_length = len(draft.split())
        context_length = sum(len(src.get("content", "").split()) for src in context)
        
        if context_length > 0:
            length_ratio = draft_length / (context_length + 1)
            # Good faithfulness if draft is substantial but not too long
            faithfulness = min(1.0, max(0.3, 1.0 - abs(length_ratio - 0.3)))
        else:
            faithfulness = 0.3
        
        scores["faithfulness"] = faithfulness
        
        if faithfulness < EVAL_THRESHOLDS["faithfulness"]:
            feedback_parts.append(
                f"**Faithfulness Issue (Score: {faithfulness:.2f}):** "
                "Draft may not adequately reflect the source material."
            )
        
        # Simple relevancy check: query terms in draft
        query_terms = set(query.lower().split())
        draft_terms = set(draft.lower().split())
        overlap = len(query_terms & draft_terms)
        relevancy = min(1.0, overlap / (len(query_terms) + 1))
        
        scores["answer_relevancy"] = relevancy
        
        if relevancy < EVAL_THRESHOLDS["answer_relevancy"]:
            feedback_parts.append(
                f"**Relevancy Issue (Score: {relevancy:.2f}):** "
                "Draft may not fully address the query."
            )
        
        # Generate feedback
        if feedback_parts:
            feedback = "\n\n".join(feedback_parts)
            feedback += "\n\n**Note:** Using fallback evaluation. Install DeepEval for better metrics."
        else:
            feedback = "Draft appears to meet basic quality criteria."
        
        return scores, feedback
    
    def execute(self, state: GBederState) -> Dict[str, Any]:
        """
        Execute evaluation as a graph node.
        
        Args:
            state: Current GBeder state
            
        Returns:
            Updated state with scores and feedback
        """
        query = state["query"]
        draft = state.get("draft", "")
        context = state.get("retrieved_context", [])
        
        if not draft:
            # No draft to evaluate
            return {
                **state,
                "scores": {"faithfulness": 0.0, "answer_relevancy": 0.0},
                "feedback": "No draft available to evaluate.",
                "is_complete": False
            }
        
        # Evaluate
        scores, feedback = self.evaluate_draft(query, draft, context)
        
        # Determine if complete
        avg_score = sum(scores.values()) / len(scores)
        is_complete = avg_score >= EVAL_THRESHOLDS["overall_quality"]
        
        logger.info(f"Evaluation complete. Average score: {avg_score:.2f}, Complete: {is_complete}")
        
        # Update state
        return {
            **state,
            "scores": scores,
            "feedback": feedback,
            "is_complete": is_complete,
            "current_agent": "evaluator"
        }


def create_evaluator(use_deepeval: bool = True) -> DeepEvalNode:
    """
    Create a DeepEval evaluator instance.
    
    Args:
        use_deepeval: Whether to use DeepEval library
        
    Returns:
        DeepEvalNode instance
    """
    return DeepEvalNode(use_deepeval=use_deepeval)


def evaluate_draft(
    query: str,
    draft: str,
    context: List[Dict[str, Any]],
    use_deepeval: bool = True
) -> Tuple[Dict[str, float], str, bool]:
    """
    Standalone function to evaluate a draft.
    
    Args:
        query: Research query
        draft: Generated draft
        context: Retrieved context
        use_deepeval: Whether to use DeepEval
        
    Returns:
        Tuple of (scores, feedback, is_approved)
    """
    evaluator = create_evaluator(use_deepeval)
    scores, feedback = evaluator.evaluate_draft(query, draft, context)
    
    avg_score = sum(scores.values()) / len(scores)
    is_approved = avg_score >= EVAL_THRESHOLDS["overall_quality"]
    
    return scores, feedback, is_approved
