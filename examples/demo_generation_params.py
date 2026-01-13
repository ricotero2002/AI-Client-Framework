"""
Demo: Generation Parameters Configuration
Shows how to configure temperature, top_p, top_k, and other parameters
"""
import sys
import io
from prompt import Prompt
from client_factory import create_client

# Configure UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def demo_generation_parameters():
    """Demonstrate generation parameter configuration"""
    print("=" * 60)
    print("DEMO: Generation Parameters Configuration")
    print("=" * 60)
    
    # Create a simple prompt
    prompt = Prompt().set_user_input("Escribe un poema corto sobre la luna")
    
    # Create client
    client = create_client('gemini')
    client.select_model('gemini-2.0-flash-exp')
    
    # Test 1: Low temperature (more deterministic)
    print("\n" + "-" * 60)
    print("TEST 1: Low Temperature (0.2) - Más determinístico")
    print("-" * 60)
    
    client.set_temperature(0.2)
    response1, usage1 = client.get_response(prompt)
    
    print(f"\nRespuesta 1:")
    print(response1)
    print(f"\nTokens: {usage1.total_tokens}")
    
    # Test 2: High temperature (more creative)
    print("\n" + "-" * 60)
    print("TEST 2: High Temperature (1.5) - Más creativo")
    print("-" * 60)
    
    client.set_temperature(1.5)
    response2, usage2 = client.get_response(prompt)
    
    print(f"\nRespuesta 2:")
    print(response2)
    print(f"\nTokens: {usage2.total_tokens}")
    
    # Test 3: With top_p (nucleus sampling)
    print("\n" + "-" * 60)
    print("TEST 3: Top-P (0.8) + Temperature (0.7)")
    print("-" * 60)
    
    client.set_temperature(0.7).set_top_p(0.8)
    response3, usage3 = client.get_response(prompt)
    
    print(f"\nRespuesta 3:")
    print(response3)
    print(f"\nTokens: {usage3.total_tokens}")
    
    # Test 4: With top_k
    print("\n" + "-" * 60)
    print("TEST 4: Top-K (40) + Temperature (0.9)")
    print("-" * 60)
    
    client.reset_generation_config()
    client.set_temperature(0.9).set_top_k(40)
    response4, usage4 = client.get_response(prompt)
    
    print(f"\nRespuesta 4:")
    print(response4)
    print(f"\nTokens: {usage4.total_tokens}")
    
    # Test 5: With max_tokens
    print("\n" + "-" * 60)
    print("TEST 5: Max Tokens (50) - Respuesta corta")
    print("-" * 60)
    
    client.reset_generation_config()
    client.set_temperature(0.7).set_max_tokens(50)
    response5, usage5 = client.get_response(prompt)
    
    print(f"\nRespuesta 5:")
    print(response5)
    print(f"\nTokens: {usage5.total_tokens}")
    
    # Test 6: View current config
    print("\n" + "-" * 60)
    print("TEST 6: Ver configuración actual")
    print("-" * 60)
    
    client.set_temperature(0.8).set_top_p(0.9).set_top_k(50).set_max_tokens(100)
    config = client.get_generation_config()
    
    print("\nConfiguración activa:")
    for param, value in config.items():
        print(f"  {param}: {value}")
    
    # Test 7: Reset config
    print("\n" + "-" * 60)
    print("TEST 7: Reset configuración")
    print("-" * 60)
    
    print("\nAntes del reset:")
    print(f"  Config: {client.get_generation_config()}")
    
    client.reset_generation_config()
    
    print("\nDespués del reset:")
    print(f"  Config: {client.get_generation_config()}")
    
    # Test 8: Method chaining
    print("\n" + "-" * 60)
    print("TEST 8: Method Chaining")
    print("-" * 60)
    
    response8, usage8 = (client
        .set_temperature(0.7)
        .set_top_p(0.9)
        .set_max_tokens(80)
        .get_response(prompt))
    
    print(f"\nRespuesta con chaining:")
    print(response8)
    print(f"\nTokens: {usage8.total_tokens}")
    
    print("\n" + "=" * 60)
    print("Demo completado!")
    print("=" * 60)


if __name__ == "__main__":
    demo_generation_parameters()
