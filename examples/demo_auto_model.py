"""
Demo: Automatic Pydantic Model Creation from Fields
Shows how adding fields creates a real Pydantic model for validation
"""
import sys
import io
import json
from prompt import Prompt
from client_factory import create_client

# Configure UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def demo_automatic_model_creation():
    """Demonstrate automatic Pydantic model creation"""
    print("=" * 60)
    print("DEMO: Automatic Pydantic Model Creation")
    print("=" * 60)
    
    # Create prompt by adding fields one by one
    prompt = (Prompt()
        .set_system("Eres un asistente que analiza películas.")
        .add_output_field(
            name="title",
            field_type="string",
            description="Título de la película",
            required=True
        )
        .add_output_field(
            name="rating",
            field_type="integer",
            description="Calificación del 1 al 10",
            required=True,
            ge=1,
            le=10
        )
        .add_output_field(
            name="genres",
            field_type="array",
            description="Lista de géneros",
            required=True
        )
        .add_output_field(
            name="review",
            field_type="string",
            description="Reseña de la película",
            required=True,
            min_length=50
        )
        .add_output_field(
            name="recommended",
            field_type="boolean",
            description="Si la recomiendas o no",
            required=True
        )
        .add_output_field(
            name="similar_movies",
            field_type="array",
            description="Películas similares",
            required=False
        )
        .set_user_input("Analiza la película Inception"))
    
    print("\n✅ Campos agregados al prompt")
    print(f"   Total de campos: {len(prompt._structured_output_fields)}")
    
    # Get the Pydantic model (this creates it automatically)
    print("\n🔨 Obteniendo modelo Pydantic...")
    model = prompt.get_pydantic_model()
    
    if model:
        print(f"✅ Modelo Pydantic creado automáticamente!")
        print(f"   Nombre del modelo: {model.__name__}")
        print(f"   Campos del modelo: {list(model.model_fields.keys())}")
        
        # Show model schema
        schema = model.model_json_schema()
        print(f"\n📋 JSON Schema generado:")
        print(json.dumps(schema, indent=2, ensure_ascii=False))
        
        # Test validation with valid data
        print("\n" + "-" * 60)
        print("TEST 1: Validación con datos válidos")
        valid_data = {
            "title": "Inception",
            "rating": 9,
            "genres": ["Sci-Fi", "Thriller"],
            "review": "Una película increíble que te hace cuestionar la realidad y los sueños.",
            "recommended": True,
            "similar_movies": ["The Matrix", "Interstellar"]
        }
        
        try:
            validated = model(**valid_data)
            print("✅ Validación exitosa!")
            print(f"   Tipo: {type(validated)}")
            print(f"   Title: {validated.title}")
            print(f"   Rating: {validated.rating}/10")
            print(f"   Recommended: {validated.recommended}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test validation with invalid data (rating out of range)
        print("\n" + "-" * 60)
        print("TEST 2: Validación con rating inválido (15/10)")
        invalid_data = {
            "title": "Inception",
            "rating": 15,  # Invalid: > 10
            "genres": ["Sci-Fi"],
            "review": "Excelente película",
            "recommended": True
        }
        
        try:
            validated = model(**invalid_data)
            print("✅ Validación exitosa (no debería pasar)")
        except Exception as e:
            print(f"❌ Validación falló (esperado):")
            print(f"   {e}")
        
        # Test validation with missing required field
        print("\n" + "-" * 60)
        print("TEST 3: Validación con campo requerido faltante")
        incomplete_data = {
            "title": "Inception",
            "rating": 9,
            # Missing 'genres', 'review', 'recommended'
        }
        
        try:
            validated = model(**incomplete_data)
            print("✅ Validación exitosa (no debería pasar)")
        except Exception as e:
            print(f"❌ Validación falló (esperado):")
            print(f"   Error: Campo requerido faltante")
        
        # Test validation with review too short
        print("\n" + "-" * 60)
        print("TEST 4: Validación con review muy corta")
        short_review_data = {
            "title": "Inception",
            "rating": 9,
            "genres": ["Sci-Fi"],
            "review": "Buena",  # Too short (< 50 chars)
            "recommended": True
        }
        
        try:
            validated = model(**short_review_data)
            print("✅ Validación exitosa (no debería pasar)")
        except Exception as e:
            print(f"❌ Validación falló (esperado):")
            print(f"   Error: Review muy corta")
        
        # Now test with actual Gemini response
        print("\n" + "=" * 60)
        print("TEST 5: Validación con respuesta real de Gemini")
        print("=" * 60)
        
        try:
            client = create_client('gemini')
            client.select_model('gemini-2.0-flash-exp')
            
            response, usage = client.get_response(
                prompt,
                response_mime_type="application/json",
                response_schema=schema
            )
            
            print(f"\n📥 Respuesta recibida ({len(response)} chars)")
            
            # Validate using prompt's method
            is_valid, validated_data, error = prompt.validate_response(response)
            
            if is_valid:
                print(f"\n✅ Respuesta VÁLIDA!")
                print(f"\n📊 Datos validados:")
                print(f"   Title: {validated_data.title}")
                print(f"   Rating: {validated_data.rating}/10")
                print(f"   Genres: {', '.join(validated_data.genres)}")
                print(f"   Recommended: {'Sí' if validated_data.recommended else 'No'}")
                print(f"   Review: {validated_data.review[:100]}...")
                if validated_data.similar_movies:
                    print(f"   Similar movies: {', '.join(validated_data.similar_movies)}")
                
                print(f"\n💰 Tokens: {usage.total_tokens}")
            else:
                print(f"\n❌ Respuesta INVÁLIDA!")
                print(f"Error: {error}")
                
        except Exception as e:
            print(f"❌ Error en consulta: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print("❌ No se pudo crear el modelo Pydantic")


if __name__ == "__main__":
    demo_automatic_model_creation()
