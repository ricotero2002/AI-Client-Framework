import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from notion_client import Client
from github_integration import fetch_pr_changes

# Cargar variables
load_dotenv()

app = FastAPI()

# --- Configuración de Notion (Igual que antes) ---
try:
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
    if not NOTION_API_KEY or not NOTION_PAGE_ID:
        raise ValueError("Faltan credenciales de Notion en .env")
    
    notion = Client(auth=NOTION_API_KEY)
except Exception as e:
    print(f"Error config: {e}")
    exit(1)

def create_notion_report(title: str, content: str):
    """Función auxiliar para escribir en Notion"""
    notion.pages.create(
        parent={"type": "page_id", "page_id": NOTION_PAGE_ID},
        properties={"title": {"title": [{"text": {"content": title}}]}},
        children=[{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content}}]
            }
        }]
    )

# --- Endpoint del Webhook ---
@app.post("/github-webhook")
async def handle_github_webhook(request: Request):
    """
    Este endpoint recibe los datos de GitHub cada vez que pasa algo en el repo.
    """
    payload = await request.json()
    
    # Verificamos qué tipo de evento es
    # GitHub manda una cabecera 'X-GitHub-Event', pero también está en el payload
    action = payload.get('action')
    
    # Solo nos interesa cuando se ABRE un PR (opened)
    if action == 'opened' and 'pull_request' in payload:
        pr = payload['pull_request']
        repo = payload['repository']
        
        pr_number = pr['number']
        repo_name = repo['name']
        repo_owner = repo['owner']['login']
        
        print(f"🔔 Detectado nuevo PR #{pr_number} en {repo_owner}/{repo_name}")
        
        # 1. Usamos tu función existente para analizar los cambios
        pr_analysis = fetch_pr_changes(repo_owner, repo_name, pr_number)
        
        if pr_analysis:
            # 2. Formateamos el contenido para Notion
            title = f"Nuevo PR: {pr_analysis['title']} (#{pr_number})"
            content = (
                f"Autor: {pr_analysis['author']}\n"
                f"Archivos cambiados: {pr_analysis['total_changes']}\n"
                f"Descripción: {pr_analysis['description']}\n"
                f"Estado: {pr_analysis['state']}"
            )
            
            # 3. Creamos la página en Notion
            try:
                create_notion_report(title, content)
                print("✅ Reporte creado en Notion exitosamente.")
                return {"status": "success", "message": "Reporte creado"}
            except Exception as e:
                print(f"❌ Error escribiendo en Notion: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
    return {"status": "ignored", "message": f"Evento '{action}' no procesado"}

if __name__ == "__main__":
    # Corremos el servidor en el puerto 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)