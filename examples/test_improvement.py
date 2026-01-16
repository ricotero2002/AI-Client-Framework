"""
Test Prompt Improvement - Using Human Feedback
Generates an improved version of the comedian prompt based on evaluation feedback
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client_factory import create_client
from prompt import Prompt
from prompt_evaluator import PromptImprover, EvaluationResult
from eval_database import get_eval_db


def get_original_prompt():
    """Get the original comedian prompt from database"""
    db = get_eval_db()
    
    # Get prompt ID 1 (the comedian prompt we just created)
    from database import get_db_manager
    db_manager = get_db_manager()
    
    prompt_record = db_manager.get_prompt(1)
    
    if not prompt_record:
        print("[!] Prompt not found. Run comedian_eval_example.py first.")
        return None
    
    # Reconstruct prompt
    prompt = Prompt()
    prompt._prompt_id = prompt_record.id
    prompt.set_system(prompt_record.system_message)
    
    # Load few-shot examples
    import json
    if prompt_record.few_shot_examples:
        examples = json.loads(prompt_record.few_shot_examples)
        for ex in examples:
            prompt.add_few_shot_example(ex['user'], ex['assistant'])
    
    return prompt


def get_evaluation_results_with_feedback():
    """Get evaluation results that have human feedback"""
    db = get_eval_db()
    
    # Get all evaluations for prompt 1
    evaluations = db.get_evaluations(prompt_id=1)
    
    # Filter those with human feedback
    with_feedback = [e for e in evaluations if e.human_score is not None]
    
    if not with_feedback:
        print("[!] No human feedback found. Run comedian_eval_example.py and provide feedback first.")
        return []
    
    # Convert to EvaluationResult objects
    results = []
    for eval in with_feedback:
        # Get test case
        test_cases = db.get_test_cases(prompt_id=1)
        test_case = next((tc for tc in test_cases if tc.id == eval.test_case_id), None)
        
        if test_case:
            result = EvaluationResult(
                test_case_id=eval.test_case_id,
                input=test_case.input,
                expected_output=test_case.expected_output,
                response=eval.response,
                llm_score=eval.llm_score,
                llm_reasoning=eval.llm_reasoning,
                human_score=eval.human_score,
                human_feedback=eval.human_feedback
            )
            results.append(result)
    
    return results


def generate_improvement():
    """Generate improved prompt based on feedback"""
    print("\n" + "="*80)
    print("PROMPT IMPROVEMENT - Based on Human Feedback")
    print("="*80)
    
    # Get original prompt
    print("\n[*] Loading original prompt...")
    original = get_original_prompt()
    if not original:
        return
    
    print(f"[+] Loaded prompt (ID: {original._prompt_id})")
    print(f"\nOriginal System Message:")
    print("-"*80)
    print(original._system_message)
    print("-"*80)
    
    # Get evaluations with human feedback
    print("\n[*] Loading evaluation results with human feedback...")
    results = get_evaluation_results_with_feedback()
    
    if not results:
        return
    
    print(f"[+] Found {len(results)} evaluations with human feedback")
    
    # Show feedback summary
    print("\n" + "="*80)
    print("HUMAN FEEDBACK SUMMARY")
    print("="*80)
    
    for i, result in enumerate(results, 1):
        print(f"\nTest {i}: {result.input}")
        print(f"  LLM Score: {result.llm_score:.2f}")
        print(f"  Human Score: {result.human_score:.2f}")
        if result.human_feedback:
            print(f"  Feedback: {result.human_feedback}")
    
    # Identify failures (human score < 0.7)
    failures = [r for r in results if r.human_score < 0.7]
    
    print(f"\n[*] Failures (human score < 0.7): {len(failures)}")
    
    if not failures:
        print("\n[+] No failures found based on human feedback!")
        print("    The prompt is performing well according to human evaluation.")
        return
    
    # Create improver
    print("\n[*] Generating improvements...")
    client = create_client('gemini')
    improver = PromptImprover(client, improver_model='gemini-2.0-flash-exp')
    
    # Build custom failure summary with human feedback
    failure_summary = _build_failure_summary_with_human_feedback(failures)
    
    # Generate improvements
    improvements = _generate_improvements_with_context(improver, original, failure_summary)
    
    # Display improvements
    print("\n" + "="*80)
    print("SUGGESTED IMPROVEMENTS")
    print("="*80)
    
    print("\n[IMPROVED SYSTEM MESSAGE]")
    print("-"*80)
    print(improvements['system_message'])
    print("-"*80)
    
    if improvements.get('few_shot_examples'):
        print("\n[ADDITIONAL FEW-SHOT EXAMPLES]")
        print("-"*80)
        print(improvements['few_shot_examples'])
        print("-"*80)
    
    print("\n[EXPLANATION]")
    print("-"*80)
    print(improvements['explanation'])
    print("-"*80)
    
    # Save to file
    output_file = "improved_prompt.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("IMPROVED COMEDIAN PROMPT\n")
        f.write("="*80 + "\n\n")
        f.write("SYSTEM MESSAGE:\n")
        f.write("-"*80 + "\n")
        f.write(improvements['system_message'] + "\n")
        f.write("-"*80 + "\n\n")
        
        if improvements.get('few_shot_examples'):
            f.write("ADDITIONAL FEW-SHOT EXAMPLES:\n")
            f.write("-"*80 + "\n")
            f.write(improvements['few_shot_examples'] + "\n")
            f.write("-"*80 + "\n\n")
        
        f.write("EXPLANATION:\n")
        f.write("-"*80 + "\n")
        f.write(improvements['explanation'] + "\n")
        f.write("-"*80 + "\n\n")
        
        f.write("HUMAN FEEDBACK INCORPORATED:\n")
        f.write("-"*80 + "\n")
        for i, failure in enumerate(failures, 1):
            f.write(f"\n{i}. {failure.input}\n")
            f.write(f"   Human Score: {failure.human_score:.2f}\n")
            if failure.human_feedback:
                f.write(f"   Feedback: {failure.human_feedback}\n")
    
    print(f"\n[+] Improved prompt saved to: {output_file}")
    
    # Ask if user wants to create new version
    create = input("\nCreate new prompt version in database? (y/n, default: n): ").strip().lower()
    
    if create == 'y':
        improved = Prompt()
        improved.set_system(improvements['system_message'])
        
        # Copy original few-shots
        for ex in original._few_shot_examples:
            improved.add_few_shot_example(ex.user, ex.assistant)
        
        improved.save()
        
        # Save version
        db = get_eval_db()
        versions = db.get_prompt_versions(original._prompt_id)
        next_version = len(versions) + 1
        
        db.save_prompt_version(
            parent_prompt_id=original._prompt_id,
            version=next_version,
            system_message=improvements['system_message'],
            few_shot_examples=[{'user': ex.user, 'assistant': ex.assistant} for ex in improved._few_shot_examples],
            improvement_reason=improvements['explanation']
        )
        
        print(f"\n[+] Created new prompt version (ID: {improved.get_id()}, Version: {next_version})")
    
    print("\n" + "="*80)


def _build_failure_summary_with_human_feedback(failures):
    """Build failure summary including human feedback"""
    summary_parts = []
    
    for i, failure in enumerate(failures, 1):
        summary_parts.append(f"""
Failure {i}:
Input: {failure.input}
Expected: {failure.expected_output[:150]}...
Actual: {failure.response[:150]}...
LLM Score: {failure.llm_score:.2f}
Human Score: {failure.human_score:.2f}
Human Feedback: {failure.human_feedback or 'None'}
LLM Reasoning: {failure.llm_reasoning[:200]}...
""")
    
    return "\n".join(summary_parts)


def _generate_improvements_with_context(improver, prompt, failure_summary):
    """Generate improvements with human feedback context"""
    from prompt import Prompt
    
    improve_prompt = Prompt()
    improve_prompt.set_system(
        "You are an expert prompt engineer specializing in comedy and creative writing. "
        "Your task is to improve prompts based on HUMAN evaluation feedback to achieve better results. "
        "Human feedback is more valuable than LLM scores - prioritize addressing human concerns."
    )
    
    improve_input = f"""CURRENT PROMPT:
System Message: {prompt._system_message}

Few-Shot Examples: {len(prompt._few_shot_examples)} examples

EVALUATION FAILURES (Based on HUMAN Feedback):
{failure_summary}

TASK:
Analyze the failures, paying special attention to the HUMAN FEEDBACK provided. The human evaluator knows what good comedy is.
Provide:
1. An improved system message that addresses the specific issues raised in human feedback
2. Suggestions for additional few-shot examples if needed
3. Brief explanation of changes focusing on how they address human concerns

Format your response as:
IMPROVED_SYSTEM_MESSAGE:
[Your improved system message]

ADDITIONAL_FEW_SHOTS:
[List any suggested few-shot examples, or "None" if not needed]

EXPLANATION:
[Brief explanation of improvements and how they address human feedback]"""
    
    improve_prompt.set_user_input(improve_input)
    
    # Get improvements
    response, _ = improver.client.get_response(improve_prompt)
    
    # Parse improvements
    improvements = improver._parse_improvements(response)
    
    return improvements


if __name__ == "__main__":
    generate_improvement()
