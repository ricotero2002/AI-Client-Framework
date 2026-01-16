"""
Prompt Comparison Tool
Compare usage statistics and costs across all prompts in the database
"""
from database import get_db_manager, Prompt as DBPrompt
from typing import List, Dict, Any
import json


def get_all_prompts() -> List[DBPrompt]:
    """Get all prompts from database"""
    db = get_db_manager()
    session = db.get_session()
    
    try:
        prompts = session.query(DBPrompt).all()
        return prompts
    finally:
        session.close()


def get_prompt_stats(prompt_id: int) -> Dict[str, Any]:
    """Get comprehensive stats for a prompt"""
    db = get_db_manager()
    
    # Get basic stats
    stats = db.get_usage_stats(prompt_id)
    
    # Get model breakdown
    from prompt import Prompt
    temp_prompt = Prompt()
    temp_prompt._prompt_id = prompt_id
    model_stats = temp_prompt.get_usage_by_model()
    
    return {
        'overall': stats,
        'by_model': model_stats
    }


def format_prompt_preview(prompt: DBPrompt, max_length: int = 60) -> str:
    """Format prompt system message as preview"""
    if not prompt.system_message:
        return "[No system message]"
    
    preview = prompt.system_message.replace('\n', ' ').strip()
    if len(preview) > max_length:
        return preview[:max_length] + "..."
    return preview


def print_prompt_comparison():
    """Print comparison table of all prompts"""
    print("\n" + "="*100)
    print("PROMPT COMPARISON - All Prompts in Database")
    print("="*100)
    
    prompts = get_all_prompts()
    
    if not prompts:
        print("\n[!] No prompts found in database")
        return
    
    print(f"\nTotal prompts: {len(prompts)}\n")
    
    # Collect data
    prompt_data = []
    for prompt in prompts:
        stats = get_prompt_stats(prompt.id)
        overall = stats['overall']
        by_model = stats['by_model']
        
        prompt_data.append({
            'id': prompt.id,
            'preview': format_prompt_preview(prompt),
            'calls': overall['total_calls'],
            'total_cost': overall['total_cost'],
            'avg_cost': overall['total_cost'] / overall['total_calls'] if overall['total_calls'] > 0 else 0,
            'total_tokens': overall['total_input_tokens'] + overall['total_output_tokens'],
            'avg_input': overall['total_input_tokens'] / overall['total_calls'] if overall['total_calls'] > 0 else 0,
            'avg_output': overall['total_output_tokens'] / overall['total_calls'] if overall['total_calls'] > 0 else 0,
            'models': list(by_model.keys()),
            'by_model': by_model
        })
    
    # Sort by total cost (descending)
    prompt_data.sort(key=lambda x: x['total_cost'], reverse=True)
    
    # Print summary table
    print("-"*100)
    print(f"{'ID':<5} {'Calls':<7} {'Total Cost':<12} {'Avg Cost':<12} {'Avg In':<10} {'Avg Out':<10} {'Models':<15}")
    print("-"*100)
    
    for data in prompt_data:
        models_str = ', '.join(data['models'][:2])  # Show first 2 models
        if len(data['models']) > 2:
            models_str += f" +{len(data['models'])-2}"
        
        print(f"{data['id']:<5} {data['calls']:<7} ${data['total_cost']:<11.6f} ${data['avg_cost']:<11.6f} "
              f"{data['avg_input']:<10.1f} {data['avg_output']:<10.1f} {models_str:<15}")
    
    print("-"*100)
    
    # Print totals
    total_calls = sum(d['calls'] for d in prompt_data)
    total_cost = sum(d['total_cost'] for d in prompt_data)
    
    print(f"\nTOTALS: {total_calls} calls, ${total_cost:.6f} total cost")
    print("="*100)


def print_detailed_prompt_stats(prompt_id: int):
    """Print detailed statistics for a specific prompt"""
    db = get_db_manager()
    session = db.get_session()
    
    try:
        prompt = session.query(DBPrompt).filter(DBPrompt.id == prompt_id).first()
        
        if not prompt:
            print(f"\n[!] Prompt {prompt_id} not found")
            return
        
        print("\n" + "="*80)
        print(f"DETAILED STATS - Prompt ID: {prompt_id}")
        print("="*80)
        
        # System message
        print(f"\nSystem Message:")
        print("-"*80)
        print(prompt.system_message or "[None]")
        print("-"*80)
        
        # Few-shot examples
        if prompt.few_shot_examples:
            examples = json.loads(prompt.few_shot_examples)
            print(f"\nFew-Shot Examples: {len(examples)}")
            for i, ex in enumerate(examples, 1):
                print(f"  {i}. User: {ex.get('user', '')[:50]}...")
                print(f"     Assistant: {ex.get('assistant', '')[:50]}...")
        
        # Get stats
        stats = get_prompt_stats(prompt_id)
        overall = stats['overall']
        by_model = stats['by_model']
        
        # Overall stats
        print(f"\n{'='*80}")
        print("OVERALL STATISTICS")
        print("="*80)
        print(f"Total calls: {overall['total_calls']}")
        print(f"Total input tokens: {overall['total_input_tokens']:,}")
        print(f"Total output tokens: {overall['total_output_tokens']:,}")
        print(f"Total tokens: {overall['total_input_tokens'] + overall['total_output_tokens']:,}")
        print(f"Total cost: ${overall['total_cost']:.6f}")
        
        if overall['total_calls'] > 0:
            print(f"\nAverages per call:")
            print(f"  Input tokens: {overall['total_input_tokens'] / overall['total_calls']:.1f}")
            print(f"  Output tokens: {overall['total_output_tokens'] / overall['total_calls']:.1f}")
            print(f"  Cost: ${overall['total_cost'] / overall['total_calls']:.6f}")
        
        if overall['avg_quality_score']:
            print(f"  Quality score: {overall['avg_quality_score']:.2f}")
        
        # Per-model stats
        if by_model:
            print(f"\n{'='*80}")
            print("STATISTICS BY MODEL")
            print("="*80)
            
            for model, model_stats in sorted(by_model.items()):
                print(f"\n{model}:")
                print(f"  Calls: {model_stats['calls']}")
                print(f"  Total cost: ${model_stats['total_cost']:.6f}")
                print(f"  Avg input tokens: {model_stats['avg_input_tokens']:.1f}")
                print(f"  Avg output tokens: {model_stats['avg_output_tokens']:.1f}")
                print(f"  Avg cost per call: ${model_stats['avg_cost']:.6f}")
                if model_stats['avg_quality_score']:
                    print(f"  Avg quality score: {model_stats['avg_quality_score']:.2f}")
        
        print("\n" + "="*80)
        
    finally:
        session.close()


def compare_prompts_by_model(model_name: str):
    """Compare all prompts for a specific model"""
    print("\n" + "="*100)
    print(f"PROMPT COMPARISON - Model: {model_name}")
    print("="*100)
    
    prompts = get_all_prompts()
    
    # Collect data for this model
    model_data = []
    for prompt in prompts:
        stats = get_prompt_stats(prompt.id)
        by_model = stats['by_model']
        
        if model_name in by_model:
            model_stats = by_model[model_name]
            model_data.append({
                'id': prompt.id,
                'preview': format_prompt_preview(prompt),
                'calls': model_stats['calls'],
                'total_cost': model_stats['total_cost'],
                'avg_cost': model_stats['avg_cost'],
                'avg_input': model_stats['avg_input_tokens'],
                'avg_output': model_stats['avg_output_tokens'],
                'avg_quality': model_stats['avg_quality_score']
            })
    
    if not model_data:
        print(f"\n[!] No prompts found using model: {model_name}")
        return
    
    # Sort by average cost
    model_data.sort(key=lambda x: x['avg_cost'], reverse=True)
    
    print(f"\nPrompts using {model_name}: {len(model_data)}\n")
    print("-"*100)
    print(f"{'ID':<5} {'Calls':<7} {'Avg Cost':<12} {'Avg In':<10} {'Avg Out':<10} {'Quality':<10} {'Preview':<40}")
    print("-"*100)
    
    for data in model_data:
        quality_str = f"{data['avg_quality']:.2f}" if data['avg_quality'] else "N/A"
        print(f"{data['id']:<5} {data['calls']:<7} ${data['avg_cost']:<11.6f} "
              f"{data['avg_input']:<10.1f} {data['avg_output']:<10.1f} {quality_str:<10} {data['preview']:<40}")
    
    print("-"*100)
    
    # Totals
    total_calls = sum(d['calls'] for d in model_data)
    total_cost = sum(d['total_cost'] for d in model_data)
    avg_cost = total_cost / total_calls if total_calls > 0 else 0
    
    print(f"\nTOTALS: {total_calls} calls, ${total_cost:.6f} total, ${avg_cost:.6f} avg per call")
    print("="*100)


def main():
    """Main menu"""
    while True:
        print("\n" + "="*60)
        print("PROMPT COMPARISON TOOL")
        print("="*60)
        print("\nOptions:")
        print("  1. Compare all prompts")
        print("  2. View detailed stats for a prompt")
        print("  3. Compare prompts by model")
        print("  4. Exit")
        
        choice = input("\nYour choice (1-4): ").strip()
        
        if choice == "1":
            print_prompt_comparison()
        
        elif choice == "2":
            prompt_id = input("Enter prompt ID: ").strip()
            try:
                print_detailed_prompt_stats(int(prompt_id))
            except ValueError:
                print("[!] Invalid prompt ID")
        
        elif choice == "3":
            model = input("Enter model name (e.g., gpt-4o-mini, gemini-2.0-flash-exp): ").strip()
            if model:
                compare_prompts_by_model(model)
        
        elif choice == "4":
            print("\n[*] Goodbye!")
            break
        
        else:
            print("[!] Invalid choice")


if __name__ == "__main__":
    main()
