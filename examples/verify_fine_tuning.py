
from prompt import Prompt

def mock_token_counter(text: str) -> int:
    # 1 char = 1 token for simple testing
    return len(text)

def test_fine_tuning_evaluation():
    print("Testing evaluate_fine_tuning...")
    
    # Case 1: Less than 2000 tokens
    prompt1 = Prompt()
    prompt1.set_system("Small system message") # ~20 chars
    prompt1.add_few_shot_example("User 1", "Assistant 1") # ~15 chars
    
    eval1 = prompt1.evaluate_fine_tuning(mock_token_counter, threshold=2000)
    print(f"\nCase 1 (Should be False): {eval1.recommend_fine_tuning}")
    print(f"Tokens: {eval1.total_static_tokens}")
    print(f"Reason: {eval1.reason}")
    assert eval1.recommend_fine_tuning == False
    
    # Case 2: Greater than 2000 tokens
    prompt2 = Prompt()
    large_text = "x" * 2001
    prompt2.set_system(large_text)
    
    eval2 = prompt2.evaluate_fine_tuning(mock_token_counter, threshold=2000)
    print(f"\nCase 2 (Should be True): {eval2.recommend_fine_tuning}")
    print(f"Tokens: {eval2.total_static_tokens}")
    print(f"Reason: {eval2.reason}")
    assert eval2.recommend_fine_tuning == True
    
    print("\nAll tests passed!")

if __name__ == "__main__":
    test_fine_tuning_evaluation()
