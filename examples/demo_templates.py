"""
Demo: Template Variables and File Attachments
Shows how to use dynamic variables and attach multimedia files
"""
import sys
import io
from prompt import Prompt
from client_factory import create_client

# Configure UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def demo_template_variables():
    """Demonstrate template variable usage"""
    print("=" * 60)
    print("DEMO 1: Template Variables")
    print("=" * 60)
    
    # Create a template prompt with variables
    template = (Prompt()
        .set_system("Eres un asistente que analiza textos.")
        .set_user_input("""
Analiza el siguiente texto y responde en [[language]]:

Texto: "[[text]]"

Enfócate en: [[focus]]
"""))
    
    print("\n📝 Template creado con variables:")
    print("  - [[text]]")
    print("  - [[language]]")
    print("  - [[focus]]")
    
    # Test 1: Spanish analysis
    print("\n" + "-" * 60)
    print("TEST 1: Análisis en español")
    print("-" * 60)
    
    prompt1 = template.clone().set_variables(
        text="The quick brown fox jumps over the lazy dog",
        language="español",
        focus="gramática y estructura"
    )
    
    print("\nVariables aplicadas:")
    print(f"  text: 'The quick brown fox...'")
    print(f"  language: 'español'")
    print(f"  focus: 'gramática y estructura'")
    
    messages = prompt1.to_messages()
    print(f"\nMensaje generado:")
    print(messages[-1]['content'])
    
    # Test 2: English analysis
    print("\n" + "-" * 60)
    print("TEST 2: Análisis en inglés")
    print("-" * 60)
    
    prompt2 = template.clone().set_variables(
        text="La vida es bella",
        language="English",
        focus="sentiment and tone"
    )
    
    print("\nVariables aplicadas:")
    print(f"  text: 'La vida es bella'")
    print(f"  language: 'English'")
    print(f"  focus: 'sentiment and tone'")
    
    # Send to Gemini
    try:
        client = create_client('gemini')
        client.select_model('gemini-2.0-flash-exp')
        client.set_temperature(0.7).set_max_tokens(150)
        
        response, usage = client.get_response(prompt2)
        
        print(f"\n✅ Respuesta de Gemini:")
        print(response)
        print(f"\n💰 Tokens: {usage.total_tokens}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Multiple uses of same template
    print("\n" + "-" * 60)
    print("TEST 3: Reutilización de template")
    print("-" * 60)
    
    texts_to_analyze = [
        ("Hello world", "tono emocional"),
        ("I love programming", "palabras clave"),
        ("The weather is nice", "contexto")
    ]
    
    print("\nAnalizando múltiples textos con el mismo template:")
    for text, focus in texts_to_analyze:
        prompt = template.clone().set_variables(
            text=text,
            language="español",
            focus=focus
        )
        print(f"\n  📄 Texto: '{text}' | Enfoque: {focus}")
        # En producción, aquí enviarías cada prompt al cliente


def demo_file_attachments():
    """Demonstrate file attachment functionality"""
    print("\n" + "=" * 60)
    print("DEMO 2: File Attachments")
    print("=" * 60)
    
    # Create prompt with file attachment
    prompt = Prompt().set_user_input("Analiza esta imagen y describe lo que ves")
    
    # Note: For this demo, we'll show the structure without actual files
    print("\n📎 Métodos disponibles para adjuntar archivos:")
    print("  - attach_file(path, mime_type, description)")
    print("  - attach_image(path, description)")
    print("  - attach_pdf(path, description)")
    print("  - attach_video(path, description)")
    
    print("\n" + "-" * 60)
    print("Ejemplo de estructura:")
    print("-" * 60)
    
    # Show how it would work (without actual files)
    example_code = '''
# Adjuntar una imagen
prompt = (Prompt()
    .set_user_input("Describe esta imagen")
    .attach_image("photo.jpg", description="Foto de paisaje"))

# Adjuntar un PDF
prompt = (Prompt()
    .set_user_input("Resume este documento")
    .attach_pdf("contract.pdf", description="Contrato legal"))

# Adjuntar un video
prompt = (Prompt()
    .set_user_input("Analiza este video")
    .attach_video("presentation.mp4", description="Presentación corporativa"))

# Múltiples archivos
prompt = (Prompt()
    .set_user_input("Compara estas imágenes")
    .attach_image("before.jpg", description="Antes")
    .attach_image("after.jpg", description="Después"))
'''
    
    print(example_code)
    
    print("\n📋 Información de archivos adjuntos:")
    print("  Cada archivo incluye:")
    print("    - path: Ruta al archivo")
    print("    - mime_type: Tipo MIME (auto-detectado)")
    print("    - description: Descripción opcional")
    print("    - type: Categoría (image, video, pdf, audio, document)")


def demo_combined_features():
    """Demonstrate combining templates with variables"""
    print("\n" + "=" * 60)
    print("DEMO 3: Templates + Variables Combinados")
    print("=" * 60)
    
    # Create a reusable template for document analysis
    doc_analysis_template = (Prompt()
        .set_system("""Eres un analista de documentos experto.
Tu tarea es analizar documentos y proporcionar insights en [[output_language]].""")
        .set_user_input("""
Documento: [[doc_name]]
Tipo: [[doc_type]]

Pregunta específica: [[question]]

Por favor, proporciona un análisis detallado.
"""))
    
    print("\n📋 Template de análisis de documentos creado")
    print("   Variables: doc_name, doc_type, question, output_language")
    
    # Use case 1: Contract analysis
    print("\n" + "-" * 60)
    print("Caso 1: Análisis de contrato")
    print("-" * 60)
    
    contract_prompt = doc_analysis_template.clone().set_variables(
        doc_name="Contrato de Servicios 2024",
        doc_type="Contrato legal",
        question="¿Cuáles son las cláusulas de terminación?",
        output_language="español"
    )
    
    print("\n✅ Prompt generado para contrato")
    messages = contract_prompt.to_messages()
    print(f"Sistema: {messages[0]['content'][:80]}...")
    print(f"Usuario: {messages[1]['content'][:100]}...")
    
    # Use case 2: Report analysis
    print("\n" + "-" * 60)
    print("Caso 2: Análisis de reporte")
    print("-" * 60)
    
    report_prompt = doc_analysis_template.clone().set_variables(
        doc_name="Q4 Financial Report",
        doc_type="Financial document",
        question="What are the key revenue trends?",
        output_language="English"
    )
    
    print("\n✅ Prompt generado para reporte")
    messages = report_prompt.to_messages()
    print(f"System: {messages[0]['content'][:80]}...")
    print(f"User: {messages[1]['content'][:100]}...")
    
    print("\n💡 Ventajas del sistema de templates:")
    print("  ✓ Reutilización de prompts complejos")
    print("  ✓ Consistencia en múltiples consultas")
    print("  ✓ Fácil personalización con variables")
    print("  ✓ Separación de estructura y contenido")
    print("  ✓ Mantenimiento simplificado")


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("TEMPLATE VARIABLES & FILE ATTACHMENTS - DEMOS")
    print("=" * 60)
    
    try:
        demo_template_variables()
    except Exception as e:
        print(f"Demo 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        demo_file_attachments()
    except Exception as e:
        print(f"Demo 2 failed: {e}")
    
    try:
        demo_combined_features()
    except Exception as e:
        print(f"Demo 3 failed: {e}")
    
    print("\n" + "=" * 60)
    print("Demos completados!")
    print("=" * 60)


if __name__ == "__main__":
    main()
