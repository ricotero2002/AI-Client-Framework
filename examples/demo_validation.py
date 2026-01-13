"""
Demo: Prompt Validation
Shows validation of prompts with undefined variables and error handling
"""
import sys
import io
from prompt import Prompt
from client_factory import create_client

# Configure UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def demo_validation_success():
    """Demonstrate successful validation"""
    print("=" * 60)
    print("DEMO 1: Validación Exitosa")
    print("=" * 60)
    
    # Valid prompt without variables
    print("\nTest 1: Prompt sin variables")
    prompt1 = Prompt().set_user_input("¿Qué es Python?")
    is_valid, error = prompt1.validate()
    
    print(f"  Válido: {is_valid}")
    print(f"  Error: {error}")
    
    # Valid prompt with all variables defined
    print("\nTest 2: Prompt con todas las variables definidas")
    prompt2 = (Prompt()
        .set_user_input("Analiza este texto: [[text]] en [[language]]")
        .set_variables(text="Hello world", language="español"))
    
    is_valid, error = prompt2.validate()
    print(f"  Válido: {is_valid}")
    print(f"  Error: {error}")
    print(f"  Variables definidas: {list(prompt2._template_variables.keys())}")
    print(f"  Variables sin definir: {prompt2.get_undefined_variables()}")


def demo_validation_errors():
    """Demonstrate validation errors"""
    print("\n" + "=" * 60)
    print("DEMO 2: Errores de Validación")
    print("=" * 60)
    
    # Error 1: Empty prompt
    print("\nTest 1: Prompt vacío")
    prompt1 = Prompt()
    is_valid, error = prompt1.validate()
    
    print(f"  Válido: {is_valid}")
    print(f"  ❌ Error: {error}")
    
    # Error 2: Undefined variables
    print("\nTest 2: Variables sin definir")
    prompt2 = (Prompt()
        .set_user_input("Analiza [[text]] en [[language]] con enfoque en [[focus]]")
        .set_variable("text", "Hello"))  # Solo define 'text', faltan 'language' y 'focus'
    
    is_valid, error = prompt2.validate()
    undefined = prompt2.get_undefined_variables()
    
    print(f"  Válido: {is_valid}")
    print(f"  ❌ Error: {error}")
    print(f"  Variables sin definir: {undefined}")
    
    # Error 3: Partial definition
    print("\nTest 3: Definición parcial de variables")
    prompt3 = (Prompt()
        .set_system("Eres un experto en [[domain]]")
        .set_user_input("Explica [[topic]] en [[language]]")
        .set_variables(domain="programación", topic="Python"))  # Falta 'language'
    
    is_valid, error = prompt3.validate()
    undefined = prompt3.get_undefined_variables()
    
    print(f"  Válido: {is_valid}")
    print(f"  ❌ Error: {error}")
    print(f"  Variables sin definir: {undefined}")


def demo_api_call_validation():
    """Demonstrate validation before API calls"""
    print("\n" + "=" * 60)
    print("DEMO 3: Validación antes de llamadas al API")
    print("=" * 60)
    
    client = create_client('gemini')
    client.select_model('gemini-2.0-flash-exp')
    
    # Test 1: Valid prompt - should work
    print("\nTest 1: Prompt válido - debería funcionar")
    valid_prompt = (Prompt()
        .set_user_input("Escribe un haiku sobre [[topic]]")
        .set_variable("topic", "la luna"))
    
    try:
        response, usage = client.get_response(valid_prompt)
        print(f"  ✅ Llamada exitosa!")
        print(f"  Respuesta: {response[:100]}...")
        print(f"  Tokens: {usage.total_tokens}")
    except ValueError as e:
        print(f"  ❌ Error de validación: {e}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 2: Invalid prompt - should fail before API call
    print("\nTest 2: Prompt con variables sin definir - debería fallar")
    invalid_prompt = (Prompt()
        .set_user_input("Escribe un [[style]] sobre [[topic]] en [[language]]")
        .set_variable("topic", "la luna"))  # Faltan 'style' y 'language'
    
    try:
        response, usage = client.get_response(invalid_prompt)
        print(f"  ❌ No debería llegar aquí!")
    except ValueError as e:
        print(f"  ✅ Error detectado antes de la llamada al API:")
        print(f"     {e}")
    except Exception as e:
        print(f"  ❌ Error inesperado: {e}")
    
    # Test 3: Empty prompt - should fail
    print("\nTest 3: Prompt vacío - debería fallar")
    empty_prompt = Prompt()
    
    try:
        response, usage = client.get_response(empty_prompt)
        print(f"  ❌ No debería llegar aquí!")
    except ValueError as e:
        print(f"  ✅ Error detectado antes de la llamada al API:")
        print(f"     {e}")
    except Exception as e:
        print(f"  ❌ Error inesperado: {e}")


def demo_fix_validation_errors():
    """Demonstrate how to fix validation errors"""
    print("\n" + "=" * 60)
    print("DEMO 4: Corrigiendo Errores de Validación")
    print("=" * 60)
    
    # Start with invalid prompt
    print("\nPaso 1: Crear prompt con variables sin definir")
    prompt = (Prompt()
        .set_user_input("Analiza [[text]] en [[language]]"))
    
    is_valid, error = prompt.validate()
    print(f"  Válido: {is_valid}")
    print(f"  Error: {error}")
    print(f"  Variables sin definir: {prompt.get_undefined_variables()}")
    
    # Fix by adding missing variables
    print("\nPaso 2: Agregar variables faltantes")
    undefined = prompt.get_undefined_variables()
    print(f"  Agregando: {undefined}")
    
    prompt.set_variables(
        text="Hello world",
        language="español"
    )
    
    is_valid, error = prompt.validate()
    print(f"  Válido: {is_valid}")
    print(f"  Error: {error}")
    print(f"  Variables sin definir: {prompt.get_undefined_variables()}")
    
    # Now it should work
    print("\nPaso 3: Intentar llamada al API")
    try:
        client = create_client('gemini')
        client.select_model('gemini-2.0-flash-exp')
        client.set_temperature(0.7).set_max_tokens(100)
        
        response, usage = client.get_response(prompt)
        print(f"  ✅ Llamada exitosa!")
        print(f"  Respuesta: {response[:150]}...")
        print(f"  Tokens: {usage.total_tokens}")
    except Exception as e:
        print(f"  ❌ Error: {e}")


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("PROMPT VALIDATION - DEMOS")
    print("=" * 60)
    
    try:
        demo_validation_success()
    except Exception as e:
        print(f"Demo 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        demo_validation_errors()
    except Exception as e:
        print(f"Demo 2 failed: {e}")
    
    try:
        demo_api_call_validation()
    except Exception as e:
        print(f"Demo 3 failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        demo_fix_validation_errors()
    except Exception as e:
        print(f"Demo 4 failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Demos completados!")
    print("=" * 60)


if __name__ == "__main__":
    main()
