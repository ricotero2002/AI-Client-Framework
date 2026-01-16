"""
Comedian Prompt Example - Evaluation System Demo
Demonstrates the complete evaluation workflow for a comedian prompt
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client_factory import create_client
from prompt import Prompt
from prompt_evaluator import PromptEvaluator, PromptImprover
from eval_database import get_eval_db


def create_comedian_prompt():
    """Create the comedian prompt"""
    print("\n" + "="*60)
    print("Creating Comedian Prompt")
    print("="*60)
    
    comedian = Prompt()
    comedian.set_system(
        "Sos un comediante experto de Argentina llamado Lucas Lauriente. "
        "Generás chistes inteligentes, con humor absurdo y observacional sobre "
        "la vida cotidiana argentina. Tus chistes son cortos, ingeniosos y tienen "
        "un giro inesperado. Pueden ser observaciones sobre la vida cotidiana, "
        "o experiencias personales. Siempre intenta tener un humor acido."
    )
    
    # Add a few-shot example
    comedian.add_few_shot_example(
        "Hacé un chiste sobre la gente mayor",
        "¿Saben cuál es la diferencia técnica entre una 'señora' y una 'vieja de mierda'? Una señora es una mujer de edad adulta. Una vieja de mierda... es una mujer de edad adulta, ¡de mierda! Vas al banco, hay 50 personas, y siempre está esa vieja que se queja de la embarazada: 'Ay, estas se embarazan para no hacer la fila'. ¡Señora, por favor! ¿Usted se piensa que alguien decide cuidar a una criatura 18 años y no dormir nunca más solo para ganarle 15 minutos al Banco Galicia? ¡¿En qué mundo vive?!"
    )
    
    comedian.save()
    print(f"[+] Comedian prompt created (ID: {comedian.get_id()})")
    
    return comedian


def add_golden_examples(comedian: Prompt):
    """Add golden test cases for evaluation"""
    print("\n" + "="*60)
    print("Adding Golden Examples (Test Cases)")
    print("="*60)
    
    db = get_eval_db()
    
    test_cases = [
    {
        'input': 'Chiste sobre los Reyes Magos',
        'expected': 'Nuestros viejos nos mintieron en la cara. Nos hicieron creer que tres tipos en camello '
                    'entraban a un departamento de dos ambientes en Almagro. ¡Tres camellos! Te despertabas y decías '
                    '"Ma, hay olor a bosta en el living". Era un chantaje emocional: "Si no alimentás a mi camello, me llevo la Play".',
        'category': 'infancia',
        'notes': 'Observación nostálgica sobre mentiras parentales'
    },
    {
        'input': 'Hacé un chiste sobre los nombres modernos de los bebés',
        'expected': 'Fui tío hace poco y mi hermana le puso a la nena "Isis". ¡ISIS! Le digo: "¿Sos boluda? '
                    '¿Querés que la CIA nos intervenga el teléfono?". Ponele María, ponele Sofía... '
                    '¡No le pongas nombre de conflicto geopolítico a la criatura, que apenas sabe respirar!',
        'category': 'familia',
        'notes': 'Crítica exagerada a tendencias modernas'
    },
    {
        'input': 'Chiste sobre terminar el colegio',
        'expected': 'Yo técnicamente terminé el colegio, pero en mi corazón sigo debiendo Físico-Química. '
                    'Fui a buscar el analítico y la directora me lo dio con asco: "Tomá, legalmente terminaste... '
                    'pero vos y yo sabemos que no sabés un carajo". Y tiene razón, si me preguntás la tabla periódica, '
                    'te tiro nombres de Pokemones.',
        'category': 'educación',
        'notes': 'Autocrítica e identificación con el fracaso académico'
    },
    {
        'input': 'Hacé un chiste sobre viajar en avión',
        'expected': 'El miedo al avión no es racional. Se mueve la nave y pensás: "Listo, lástima que no borré el historial". '
                    'Mirás a la azafata y está sonriendo como si nada... ¡Eso me da más miedo! ¡Gritá, loca! '
                    '¡Entrá en pánico conmigo así siento que estamos conectados!',
        'category': 'viajes',
        'notes': 'Ansiedad y pensamientos intrusivos'
    },
    {
        'input': 'Chiste sobre ir a Disney',
        'expected': 'Ir a Disney de grande es raro. De chico es magia, de grande ves los hilos. Ves a Mickey y decís "Uh, el ratón", '
                    'pero te das cuenta que tiene olor a transpiración porque hace 40 grados en Orlando. '
                    'Te acercás y escuchás que le dice a Goofy: "Che, me quiero matar, me duelen los juanetes".',
        'category': 'entretenimiento',
        'notes': 'Desilusión de la adultez vs infancia'
    }
]
    
    for tc in test_cases:
        test_case = db.add_test_case(
            prompt_id=comedian.get_id(),
            input=tc['input'],
            expected_output=tc['expected'],
            category=tc['category'],
            notes=tc['notes']
        )
        print(f"[+] Added test case {test_case.id}: {tc['category']}")
    
    print(f"\n[+] Added {len(test_cases)} golden examples")
    return test_cases


def run_evaluation(comedian: Prompt):
    """Run evaluation on the comedian prompt"""
    print("\n" + "="*60)
    print("Running Evaluation")
    print("="*60)
    
    # Get test cases
    db = get_eval_db()
    test_cases_db = db.get_test_cases(comedian.get_id())
    test_cases = [tc.to_dict() for tc in test_cases_db]
    
    # Create clients
    test_client = create_client('gemini')
    test_client.select_model('gemini-2.0-flash-exp')
    
    eval_client = create_client('gemini')
    
    # Create evaluator
    evaluator = PromptEvaluator(eval_client, evaluator_model='gemini-2.5-flash')
    
    # Run evaluation
    results = evaluator.batch_evaluate(
        comedian,
        test_cases,
        test_client
    )
    
    # Save results to database
    for result in results:
        db.save_evaluation(
            prompt_id=comedian.get_id(),
            test_case_id=result.test_case_id,
            response=result.response,
            model=test_client.current_model,
            llm_score=result.llm_score,
            llm_reasoning=result.llm_reasoning
        )
    
    # Generate report
    report = evaluator.generate_report(results)
    
    print("\n" + "="*60)
    print("EVALUATION REPORT")
    print("="*60)
    print(f"Total test cases: {report['total']}")
    print(f"Average score: {report['avg_score']:.2f}")
    print(f"Passed: {report['passed']} ({report['pass_rate']*100:.1f}%)")
    print(f"Failed: {report['failed']}")
    print(f"\nScore distribution:")
    for category, count in report['score_distribution'].items():
        print(f"  {category}: {count}")
    print(f"\nScore range: {report['min_score']:.2f} - {report['max_score']:.2f}")
    
    return results, report


def collect_human_feedback(results):
    """Collect human feedback for evaluations"""
    print("\n" + "="*60)
    print("Human Feedback Collection")
    print("="*60)
    
    db = get_eval_db()
    
    # Save results to file for review
    results_file = "evaluation_results.txt"
    with open(results_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("EVALUATION RESULTS - Full Details\n")
        f.write("="*80 + "\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"\n{'='*80}\n")
            f.write(f"Test Case {i}/{len(results)}\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"INPUT:\n{result.input}\n\n")
            f.write(f"EXPECTED OUTPUT:\n{result.expected_output}\n\n")
            f.write(f"ACTUAL RESPONSE:\n{result.response}\n\n")
            f.write(f"LLM SCORE: {result.llm_score:.2f}\n\n")
            f.write(f"LLM REASONING:\n{result.llm_reasoning}\n\n")
    
    print(f"\n[+] Full results saved to: {results_file}")
    print("    You can review all responses in detail there.\n")
    
    print("Would you like to provide human feedback on the evaluations?")
    response = input("(y/n, default: n): ").strip().lower()
    
    if response != 'y':
        print("[*] Skipping human feedback")
        return
    
    evaluations = db.get_evaluations(prompt_id=results[0].test_case_id)
    
    for i, result in enumerate(results, 1):
        print(f"\n{'='*80}")
        print(f"Evaluation {i}/{len(results)}")
        print(f"{'='*80}")
        print(f"\nInput: {result.input}")
        print(f"\nExpected Output:\n{result.expected_output}")
        print(f"\nActual Response:\n{result.response}")
        print(f"\nLLM Score: {result.llm_score:.2f}")
        print(f"\nLLM Reasoning:\n{result.llm_reasoning}")
        
        score_input = input(f"\nYour score (0.0-1.0, or press Enter to skip): ").strip()
        
        if score_input:
            try:
                human_score = float(score_input)
                human_score = max(0.0, min(1.0, human_score))
                
                feedback = input("Your feedback (optional): ").strip()
                
                # Find corresponding evaluation in DB
                eval_id = evaluations[i-1].id if i <= len(evaluations) else None
                if eval_id:
                    db.update_evaluation_human_feedback(eval_id, human_score, feedback or None)
                    print(f"[+] Feedback saved")
            except ValueError:
                print("[!] Invalid score, skipping")


def improve_prompt(comedian: Prompt, results):
    """Generate improved version of the prompt"""
    print("\n" + "="*60)
    print("Prompt Improvement")
    print("="*60)
    
    # Create improver
    improve_client = create_client('gemini')
    improver = PromptImprover(improve_client, improver_model='gemini-2.5-flash')
    
    # Analyze failures
    failures = improver.analyze_failures(results, threshold=0.7)
    
    if not failures:
        print("\n[+] No failures found! Prompt is performing well.")
        return None
    
    print(f"\n[!] Found {len(failures)} failures")
    
    # Generate improvements
    print("\n[*] Generating improvements...")
    improvements = improver.generate_improvements(comedian, failures)
    
    print("\n" + "="*60)
    print("SUGGESTED IMPROVEMENTS")
    print("="*60)
    print(f"\nImproved System Message:")
    print("-"*60)
    print(improvements['system_message'])
    print("-"*60)
    
    if improvements['few_shot_examples']:
        print(f"\nAdditional Few-Shot Examples:")
        print(improvements['few_shot_examples'])
    
    print(f"\nExplanation:")
    print(improvements['explanation'])
    
    # Ask if user wants to create improved version
    create = input("\nCreate improved version? (y/n, default: y): ").strip().lower()
    
    if create == 'n':
        print("[*] Skipping version creation")
        return None
    
    # Get current version number
    db = get_eval_db()
    versions = db.get_prompt_versions(comedian.get_id())
    next_version = len(versions) + 1
    
    # Create improved version
    improved = improver.create_improved_version(comedian, improvements, next_version)
    improved.save()
    
    # Save version to database
    db.save_prompt_version(
        parent_prompt_id=comedian.get_id(),
        version=next_version,
        system_message=improvements['system_message'],
        few_shot_examples=[{'user': ex.user, 'assistant': ex.assistant} for ex in improved._few_shot_examples],
        improvement_reason=improvements['explanation']
    )
    
    print(f"\n[+] Created improved version (ID: {improved.get_id()}, Version: {next_version})")
    
    return improved


def main():
    """Main workflow"""
    print("\n" + "="*70)
    print("COMEDIAN PROMPT EVALUATION - Complete Workflow")
    print("="*70)
    
    # Step 1: Create prompt
    comedian = create_comedian_prompt()
    
    # Step 2: Add golden examples
    add_golden_examples(comedian)
    
    # Step 3: Run evaluation
    results, report = run_evaluation(comedian)
    
    # Step 4: Collect human feedback (optional)
    collect_human_feedback(results)
    
    # Step 5: Improve prompt if needed
    if report['avg_score'] < 0.8:
        print(f"\n[!] Average score ({report['avg_score']:.2f}) below threshold (0.8)")
        improved = improve_prompt(comedian, results)
        
        if improved:
            print("\n[*] Re-evaluating improved version...")
            results2, report2 = run_evaluation(improved)
            
            print(f"\n" + "="*60)
            print("IMPROVEMENT COMPARISON")
            print("="*60)
            print(f"Original score: {report['avg_score']:.2f}")
            print(f"Improved score: {report2['avg_score']:.2f}")
            print(f"Improvement: {(report2['avg_score'] - report['avg_score'])*100:+.1f}%")
    else:
        print(f"\n[+] Prompt performing well (score: {report['avg_score']:.2f})")
    
    print("\n" + "="*70)
    print("[SUCCESS] Evaluation workflow complete!")
    print("="*70)


if __name__ == "__main__":
    main()
