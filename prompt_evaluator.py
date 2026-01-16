"""
Prompt Evaluation System - Core evaluation and improvement logic
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pydantic import BaseModel, Field
import json


@dataclass
class EvaluationResult:
    """Result of a single test case evaluation"""
    test_case_id: int
    input: str
    expected_output: str
    response: str
    llm_score: float
    llm_reasoning: str
    human_score: Optional[float] = None
    human_feedback: Optional[str] = None
    
    @property
    def final_score(self) -> float:
        """Get final score (human if available, otherwise LLM)"""
        return self.human_score if self.human_score is not None else self.llm_score
    
    def passed(self, threshold: float = 0.7) -> bool:
        """Check if evaluation passed"""
        return self.final_score >= threshold


class EvaluationScore(BaseModel):
    """Structured output for evaluation scoring"""
    score: float = Field(description="Score from 0.0 to 1.0 evaluating response quality")
    reasoning: str = Field(description="Detailed explanation of the score")


class PromptEvaluator:
    """Evaluates prompt responses against golden examples using LLM"""
    
    def __init__(self, evaluator_client, evaluator_model: str = 'gpt-4o'):
        """
        Initialize evaluator
        
        Args:
            evaluator_client: AI client to use for evaluation
            evaluator_model: Model to use for evaluation scoring
        """
        self.client = evaluator_client
        self.model = evaluator_model
        self.client.select_model(evaluator_model)
    
    def evaluate_response(
        self,
        input_text: str,
        expected_output: str,
        actual_response: str,
        criteria: Optional[str] = None
    ) -> Tuple[float, str]:
        """
        Evaluate a single response against expected output
        
        Args:
            input_text: The test input
            expected_output: Golden example response
            actual_response: Response to evaluate
            criteria: Optional custom evaluation criteria
            
        Returns:
            Tuple of (score, reasoning)
        """
        from prompt import Prompt
        
        # Default evaluation criteria
        if criteria is None:
            criteria = """
1. Similarity to expected output (style, tone, structure)
2. Correctness and relevance to the input
3. Quality and creativity
"""
        
        # Create evaluation prompt
        eval_prompt = Prompt()
        eval_prompt.set_system(
            "You are an expert evaluator assessing AI responses. "
            "Provide objective, detailed evaluations."
        )
        
        eval_input = f"""Evaluate the quality of this AI response.

TEST INPUT:
{input_text}

EXPECTED OUTPUT (Golden Example):
{expected_output}

ACTUAL RESPONSE:
{actual_response}

EVALUATION CRITERIA:
{criteria}

Be strict but fair. Consider how well the actual response matches the golden example in style, content, and quality."""
        
        eval_prompt.set_user_input(eval_input)
        
        # Set structured output schema
        eval_prompt.set_output_schema(EvaluationScore)
        
        # Get evaluation
        response, _ = self.client.get_response(eval_prompt)
        
        # Parse structured response
        try:
            eval_result = EvaluationScore.model_validate_json(response)
            score = max(0.0, min(1.0, eval_result.score))  # Clamp to [0, 1]
            reasoning = eval_result.reasoning
        except Exception as e:
            print(f"[!] Failed to parse structured output: {e}")
            # Fallback to text parsing
            score, reasoning = self._parse_evaluation(response)
        
        return score, reasoning
    
    def _parse_evaluation(self, response: str) -> Tuple[float, str]:
        """Parse LLM evaluation response"""
        lines = response.strip().split('\n')
        score = 0.5  # Default
        reasoning = ""
        
        for line in lines:
            if line.startswith('Score:'):
                try:
                    score_str = line.replace('Score:', '').strip()
                    score = float(score_str)
                    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                except ValueError:
                    pass
            elif line.startswith('Reasoning:'):
                reasoning = line.replace('Reasoning:', '').strip()
        
        # If reasoning is empty, use full response
        if not reasoning:
            reasoning = response
        
        return score, reasoning
    
    def batch_evaluate(
        self,
        prompt,
        test_cases: List[Dict[str, Any]],
        test_client,
        criteria: Optional[str] = None
    ) -> List[EvaluationResult]:
        """
        Evaluate prompt against multiple test cases
        
        Args:
            prompt: Prompt instance to evaluate
            test_cases: List of test case dicts
            test_client: Client to use for generating responses
            criteria: Optional evaluation criteria
            
        Returns:
            List of EvaluationResult objects
        """
        results = []
        
        print(f"\n[*] Running evaluation on {len(test_cases)} test cases...")
        print("="*60)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}/{len(test_cases)}: {test_case['input'][:50]}...")
            
            # Generate response
            prompt.set_user_input(test_case['input'])
            response, _ = test_client.get_response(prompt)
            
            print(f"  Response: {response[:80]}...")
            
            # Evaluate response
            score, reasoning = self.evaluate_response(
                test_case['input'],
                test_case['expected_output'],
                response,
                criteria
            )
            
            print(f"  Score: {score:.2f}")
            print(f"  Reasoning: {reasoning[:100]}...")
            
            result = EvaluationResult(
                test_case_id=test_case['id'],
                input=test_case['input'],
                expected_output=test_case['expected_output'],
                response=response,
                llm_score=score,
                llm_reasoning=reasoning
            )
            
            results.append(result)
        
        print("\n" + "="*60)
        print(f"[+] Evaluation complete!")
        
        return results
    
    def generate_report(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Generate evaluation report"""
        total = len(results)
        if total == 0:
            return {'total': 0}
        
        scores = [r.final_score for r in results]
        avg_score = sum(scores) / total
        passed = sum(1 for r in results if r.passed())
        failed = total - passed
        
        # Group by score ranges
        excellent = sum(1 for s in scores if s >= 0.9)
        good = sum(1 for s in scores if 0.7 <= s < 0.9)
        poor = sum(1 for s in scores if s < 0.7)
        
        return {
            'total': total,
            'avg_score': avg_score,
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / total,
            'score_distribution': {
                'excellent (>=0.9)': excellent,
                'good (0.7-0.9)': good,
                'poor (<0.7)': poor
            },
            'min_score': min(scores),
            'max_score': max(scores)
        }


class PromptImprover:
    """Automatically improves prompts based on evaluation feedback"""
    
    def __init__(self, improver_client, improver_model: str = 'gpt-4o'):
        """
        Initialize improver
        
        Args:
            improver_client: AI client to use for generating improvements
            improver_model: Model to use for improvement generation
        """
        self.client = improver_client
        self.model = improver_model
        self.client.select_model(improver_model)
    
    def analyze_failures(
        self,
        results: List[EvaluationResult],
        threshold: float = 0.7
    ) -> List[EvaluationResult]:
        """Identify and return failed evaluations"""
        failures = [r for r in results if r.final_score < threshold]
        return failures
    
    def generate_improvements(
        self,
        prompt,
        failures: List[EvaluationResult]
    ) -> Dict[str, Any]:
        """
        Generate improvement suggestions based on failures
        
        Args:
            prompt: Original prompt instance
            failures: List of failed evaluations
            
        Returns:
            Dict with improved system_message and few_shot_examples
        """
        from prompt import Prompt
        
        # Build failure analysis
        failure_summary = self._build_failure_summary(failures)
        
        # Create improvement prompt
        improve_prompt = Prompt()
        improve_prompt.set_system(
            "You are an expert prompt engineer. Your task is to improve prompts "
            "based on evaluation failures to achieve better results."
        )
        
        improve_input = f"""CURRENT PROMPT:
System Message: {prompt._system_message}

Few-Shot Examples: {len(prompt._few_shot_examples)} examples

EVALUATION FAILURES:
{failure_summary}

TASK:
Analyze the failures and suggest improvements to the prompt. Provide:
1. An improved system message that addresses the failure patterns
2. Suggestions for additional few-shot examples (if needed)
3. Brief explanation of changes

Format your response as:
IMPROVED_SYSTEM_MESSAGE:
[Your improved system message]

ADDITIONAL_FEW_SHOTS:
[List any suggested few-shot examples, or "None" if not needed]

EXPLANATION:
[Brief explanation of improvements]"""
        
        improve_prompt.set_user_input(improve_input)
        
        # Get improvements
        response, _ = self.client.get_response(improve_prompt)
        
        # Parse improvements
        improvements = self._parse_improvements(response)
        
        return improvements
    
    def _build_failure_summary(self, failures: List[EvaluationResult]) -> str:
        """Build summary of failures"""
        summary_parts = []
        
        for i, failure in enumerate(failures, 1):
            summary_parts.append(f"""
Failure {i}:
Input: {failure.input}
Expected: {failure.expected_output[:100]}...
Actual: {failure.response[:100]}...
Score: {failure.final_score:.2f}
Reasoning: {failure.llm_reasoning[:150]}...
""")
        
        return "\n".join(summary_parts)
    
    def _parse_improvements(self, response: str) -> Dict[str, Any]:
        """Parse improvement suggestions from LLM response"""
        improvements = {
            'system_message': '',
            'few_shot_examples': [],
            'explanation': ''
        }
        
        current_section = None
        content_lines = []
        
        for line in response.split('\n'):
            if 'IMPROVED_SYSTEM_MESSAGE:' in line:
                current_section = 'system_message'
                content_lines = []
            elif 'ADDITIONAL_FEW_SHOTS:' in line:
                if current_section == 'system_message':
                    improvements['system_message'] = '\n'.join(content_lines).strip()
                current_section = 'few_shots'
                content_lines = []
            elif 'EXPLANATION:' in line:
                if current_section == 'few_shots':
                    # Parse few-shot examples if any
                    few_shot_text = '\n'.join(content_lines).strip()
                    if few_shot_text and few_shot_text.lower() != 'none':
                        improvements['few_shot_examples'] = few_shot_text
                current_section = 'explanation'
                content_lines = []
            elif current_section:
                content_lines.append(line)
        
        # Save last section
        if current_section == 'explanation':
            improvements['explanation'] = '\n'.join(content_lines).strip()
        
        return improvements
    
    def create_improved_version(
        self,
        original_prompt,
        improvements: Dict[str, Any],
        version: int
    ):
        """
        Create new improved prompt version
        
        Args:
            original_prompt: Original Prompt instance
            improvements: Improvement suggestions dict
            version: Version number
            
        Returns:
            New Prompt instance with improvements
        """
        from prompt import Prompt
        
        # Create new prompt
        improved = Prompt()
        
        # Apply improved system message
        if improvements['system_message']:
            improved.set_system(improvements['system_message'])
        else:
            improved.set_system(original_prompt._system_message)
        
        # Copy original few-shot examples
        for example in original_prompt._few_shot_examples:
            improved.add_few_shot_example(example.user, example.assistant)
        
        # Add new few-shot examples if suggested
        # (This would require parsing the suggestions more carefully)
        
        return improved
