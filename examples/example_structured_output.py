"""
Example: Structured Output with Pydantic
Demonstrates how to use structured output in Prompt class
"""
import sys
import io
import json
from prompt import Prompt
from client_factory import create_client
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

# Configure UTF-8 encoding for terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def validate_json_response(response_text: str, schema: dict, example_name: str):
    """Validate and pretty-print JSON response"""
    try:
        # Parse JSON
        response_data = json.loads(response_text)
        
        # Pretty print
        print(f"\n✅ Response JSON válido ({example_name}):")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        
        # Check required fields from schema
        if 'required' in schema:
            missing_fields = [f for f in schema['required'] if f not in response_data]
            if missing_fields:
                print(f"\n⚠️ Campos requeridos faltantes: {missing_fields}")
            else:
                print(f"\n✅ Todos los campos requeridos presentes")
        
        return True, response_data
        
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Respuesta no es JSON válido")
        print(f"   {e}")
        print(f"\nRespuesta recibida:")
        print(response_text[:200])
        return False, None


def example_build_schema_field_by_field():
    """Example 1: Building schema field by field"""
    print("=" * 60)
    print("EXAMPLE 1: Building Schema Field by Field")
    print("=" * 60)
    
    # Create prompt with structured output built field by field
    prompt = (Prompt()
        .set_system("Eres un profesor de filosofía que explica conceptos usando el método socrático.")
        .add_output_field(
            name="explanation",
            field_type="string",
            description="Explicación socrática del tema usando preguntas y respuestas",
            required=True,
            min_length=100
        )
        .add_output_field(
            name="key_questions",
            field_type="array",
            description="Lista de preguntas clave para reflexionar",
            required=True
        )
        .add_output_field(
            name="difficulty_level",
            field_type="integer",
            description="Nivel de dificultad del 1 al 10",
            required=True,
            ge=1,
            le=10
        )
        .add_output_field(
            name="related_concepts",
            field_type="array",
            description="Conceptos relacionados para explorar",
            required=False
        )
        .set_user_input("Explica qué es la justicia"))
    
    # Print the prompt structure
    print("\nPrompt structure:")
    print(prompt.print_formatted(max_length=80))
    
    # Get the JSON schema
    schema = prompt.get_output_schema()
    print("\nGenerated JSON Schema:")
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    
    # Use with client
    print("\n" + "-" * 60)
    print("Sending to Gemini...")
    try:
        client = create_client('gemini')
        client.select_model('gemini-2.0-flash-exp')
        
        # For Gemini, we need to pass the schema in the config
        response, usage = client.get_response(
            prompt,
            response_mime_type="application/json",
            response_schema=schema
        )
        
        # Validate response
        is_valid, data = validate_json_response(response, schema, "Example 1")
        
        print(f"\nTokens used: {usage.total_tokens}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_using_pydantic_model():
    """Example 2: Using a Pydantic model directly"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Using Pydantic Model")
    print("=" * 60)
    
    # Define Pydantic model
    class PhilosophicalExplanation(BaseModel):
        """Explicación filosófica estructurada"""
        explanation: str = Field(
            description="Explicación socrática del concepto",
            min_length=100
        )
        key_questions: List[str] = Field(
            description="Preguntas clave para reflexionar"
        )
        difficulty_level: int = Field(
            description="Nivel de dificultad del 1 al 10",
            ge=1,
            le=10
        )
        related_concepts: Optional[List[str]] = Field(
            default=None,
            description="Conceptos relacionados"
        )
    
    # Create prompt with Pydantic model
    prompt = (Prompt()
        .set_system("Eres un profesor de filosofía que explica conceptos usando el método socrático.")
        .set_output_schema(PhilosophicalExplanation)
        .set_user_input("Explica qué es la libertad"))
    
    # Print the prompt structure
    print("\nPrompt structure:")
    print(prompt.print_formatted(max_length=80))
    
    # Get the JSON schema
    schema = prompt.get_output_schema()
    print("\nGenerated JSON Schema:")
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    
    print(f"\nHas structured output: {prompt.has_structured_output()}")
    
    # Query Gemini
    print("\n" + "-" * 60)
    print("Sending to Gemini...")
    try:
        client = create_client('gemini')
        client.select_model('gemini-2.0-flash-exp')
        
        response, usage = client.get_response(
            prompt,
            response_mime_type="application/json",
            response_schema=schema
        )
        
        # Validate with Pydantic
        is_valid, data = validate_json_response(response, schema, "Example 2")
        
        if is_valid and data:
            try:
                # Validate with Pydantic model
                validated = PhilosophicalExplanation(**data)
                print(f"\n✅ Pydantic validation passed!")
                print(f"   Difficulty level: {validated.difficulty_level}/10")
                print(f"   Questions count: {len(validated.key_questions)}")
            except ValidationError as e:
                print(f"\n❌ Pydantic validation failed:")
                print(e)
        
        print(f"\nTokens used: {usage.total_tokens}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_mixed_content():
    """Example 3: Structured output with few-shot examples"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Structured Output with Few-Shot Examples")
    print("=" * 60)
    
    # Create prompt with few-shot examples and structured output
    prompt = (Prompt()
        .set_system("Eres un tutor de matemáticas que explica conceptos paso a paso.")
        .add_few_shot_example(
            user="Explica qué es una derivada",
            assistant='{"explanation": "Una derivada mide la tasa de cambio instantánea...", "steps": ["Entender el concepto de límite", "Aplicar la definición"], "difficulty": 7}'
        )
        .add_output_field(
            name="explanation",
            field_type="string",
            description="Explicación clara del concepto matemático",
            required=True
        )
        .add_output_field(
            name="steps",
            field_type="array",
            description="Pasos para entender el concepto",
            required=True
        )
        .add_output_field(
            name="difficulty",
            field_type="integer",
            description="Dificultad del 1 al 10",
            required=True,
            ge=1,
            le=10
        )
        .add_output_field(
            name="example",
            field_type="string",
            description="Ejemplo práctico",
            required=False
        )
        .set_user_input("Explica qué es una integral"))
    
    # Print the prompt
    print("\nPrompt structure:")
    print(prompt.print_formatted(max_length=80))
    
    # Analyze for caching
    client = create_client('gemini')
    analysis = prompt.analyze_for_caching(client.count_tokens)
    
    print(f"\nCaching Analysis:")
    print(f"  Static tokens: {analysis.static_tokens}")
    print(f"  Dynamic tokens: {analysis.dynamic_tokens}")
    print(f"  Cacheable: {analysis.cacheable_percentage:.1f}%")
    
    # Query Gemini
    print("\n" + "-" * 60)
    print("Sending to Gemini...")
    try:
        schema = prompt.get_output_schema()
        
        response, usage = client.get_response(
            prompt,
            response_mime_type="application/json",
            response_schema=schema
        )
        
        is_valid, data = validate_json_response(response, schema, "Example 3")
        
        print(f"\nTokens used: {usage.total_tokens}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_complex_schema():
    """Example 4: Complex nested schema"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Complex Nested Schema")
    print("=" * 60)
    
    class Source(BaseModel):
        """Fuente de información"""
        title: str
        url: Optional[str] = None
        reliability: int = Field(ge=1, le=10)
    
    class Argument(BaseModel):
        """Argumento con evidencia"""
        claim: str = Field(description="Afirmación principal")
        evidence: List[str] = Field(description="Evidencias que apoyan la afirmación")
        sources: List[Source] = Field(description="Fuentes de información")
        strength: int = Field(ge=1, le=10, description="Fuerza del argumento")
    
    class DebateAnalysis(BaseModel):
        """Análisis completo de un debate"""
        topic: str
        arguments_for: List[Argument]
        arguments_against: List[Argument]
        conclusion: str = Field(min_length=50)
        confidence: float = Field(ge=0.0, le=1.0)
    
    # Create prompt
    prompt = (Prompt()
        .set_system("Eres un analista de debates que evalúa argumentos de forma objetiva.")
        .set_output_schema(DebateAnalysis)
        .set_user_input("Analiza el debate sobre la inteligencia artificial y el empleo"))
    
    # Get schema
    schema = prompt.get_output_schema()
    print("\nComplex nested schema:")
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    
    # Query Gemini
    print("\n" + "-" * 60)
    print("Sending to Gemini...")
    try:
        client = create_client('gemini')
        client.select_model('gemini-2.0-flash-exp')
        
        response, usage = client.get_response(
            prompt,
            response_mime_type="application/json",
            response_schema=schema
        )
        
        print(f"\nRaw response length: {len(response)} characters")
        
        # Use the new validate_response method from Prompt
        print("\n" + "-" * 60)
        print("Validating response with Prompt.validate_response()...")
        is_valid, validated_data, error = prompt.validate_response(response)
        
        if is_valid:
            print(f"\n✅ Response is VALID!")
            print(f"\nValidated data type: {type(validated_data)}")
            
            # If it's a Pydantic model, show details
            if isinstance(validated_data, BaseModel):
                print(f"\n📊 Analysis Summary:")
                print(f"   Topic: {validated_data.topic}")
                print(f"   Arguments for: {len(validated_data.arguments_for)}")
                print(f"   Arguments against: {len(validated_data.arguments_against)}")
                print(f"   Confidence: {validated_data.confidence:.2%}")
                print(f"   Conclusion length: {len(validated_data.conclusion)} chars")
                
                # Show first argument details
                if validated_data.arguments_for:
                    first_arg = validated_data.arguments_for[0]
                    print(f"\n   📌 First argument FOR:")
                    print(f"      Claim: {first_arg.claim[:100]}...")
                    print(f"      Evidence items: {len(first_arg.evidence)}")
                    print(f"      Sources: {len(first_arg.sources)}")
                    print(f"      Strength: {first_arg.strength}/10")
                    
                    if first_arg.sources:
                        print(f"\n      First source:")
                        print(f"         Title: {first_arg.sources[0].title}")
                        print(f"         Reliability: {first_arg.sources[0].reliability}/10")
                
                # Show JSON representation
                print(f"\n📄 Full JSON response:")
                print(json.dumps(validated_data.model_dump(), indent=2, ensure_ascii=False))
            else:
                # It's a dict
                print(f"\n📄 Response data:")
                print(json.dumps(validated_data, indent=2, ensure_ascii=False))
        else:
            print(f"\n❌ Response is INVALID!")
            print(f"Error: {error}")
            print(f"\nRaw response preview:")
            print(response[:500])
        
        print(f"\n💰 Tokens used: {usage.total_tokens}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("STRUCTURED OUTPUT - USAGE EXAMPLES")
    print("=" * 60)
    '''
    try:
        example_build_schema_field_by_field()
    except Exception as e:
        print(f"Example 1 failed: {e}")
    
    try:
        example_using_pydantic_model()
    except Exception as e:
        print(f"Example 2 failed: {e}")
    
    try:
        example_mixed_content()
    except Exception as e:
        print(f"Example 3 failed: {e}")
    '''
    try:
        example_complex_schema()
    except Exception as e:
        print(f"Example 4 failed: {e}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()