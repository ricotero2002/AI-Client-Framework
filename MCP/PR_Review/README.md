# GitHub PR Review with MCP + Notion Integration

**Servidor MCP para Análisis Automático de Pull Requests con Integración a Notion**

Un servidor MCP (Model Context Protocol) que permite a agentes de IA analizar Pull Requests de GitHub y crear documentación automática en Notion, facilitando code reviews asistidos por LLM.

---

## 🎯 Características Principales

### 1. **Integración GitHub**
- Fetch automático de cambios en PRs
- Análisis de diffs línea por línea
- Extracción de metadatos (autor, fecha, commits, etc.)

### 2. **Servidor MCP con FastMCP**
- Exposición de herramientas vía Model Context Protocol
- Compatible con cualquier cliente MCP (Claude Desktop, custom clients)
- Comunicación vía stdio

### 3. **Integración Notion**
- Creación automática de páginas de análisis
- Formato estructurado de code reviews
- Organización jerárquica en workspace

### 4. **Análisis Asistido por IA**
- Los LLMs pueden usar las herramientas para:
  - Leer PRs completos
  - Identificar bugs potenciales
  - Sugerir mejoras
  - Generar documentación

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Agent (Claude, GPT, etc.)                 │
│              "Analiza el PR #123 de repo/project"                │
└──────────────────────┬──────────────────────────────────────────┘
                       │ MCP Protocol (stdio)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PR Analyzer MCP Server                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Tool 1: fetch_pr(repo_owner, repo_name, pr_number)      │  │
│  │  - Llama a GitHub API                                    │  │
│  │  - Extrae diffs, commits, metadata                       │  │
│  │  - Retorna JSON estructurado                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Tool 2: create_notion_page(title, content)              │  │
│  │  - Crea página en Notion workspace                       │  │
│  │  - Formatea contenido como bloques                       │  │
│  │  - Retorna confirmación                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────┬──────────────────────┘
                       │                   │
                       ▼                   ▼
              ┌────────────────┐   ┌──────────────┐
              │  GitHub API    │   │  Notion API  │
              └────────────────┘   └──────────────┘
```

---

## 📁 Estructura del Proyecto

```
MCP/PR_Review/
├── pr_analyzer.py           # Servidor MCP principal
├── github_integration.py    # Cliente GitHub API
├── client_test.py           # Cliente de prueba
├── webhook_server.py        # Webhook para automatización (opcional)
├── requirements.txt
└── README.md
```

---

## 🚀 Instalación y Configuración

### Requisitos

```bash
pip install fastmcp notion-client python-dotenv requests
```

### Configuración de APIs

#### 1. GitHub Personal Access Token

1. Ir a GitHub Settings → Developer settings → Personal access tokens
2. Generar nuevo token con permisos:
   - `repo` (acceso a repositorios privados)
   - `public_repo` (solo repos públicos)
3. Copiar el token

#### 2. Notion Integration

1. Ir a https://www.notion.so/my-integrations
2. Crear nueva integración
3. Copiar el "Internal Integration Token"
4. Compartir una página de Notion con la integración:
   - Abrir página en Notion
   - Click en "..." → "Add connections"
   - Seleccionar tu integración
5. Copiar el Page ID de la URL:
   ```
   https://www.notion.so/workspace/Page-Title-abc123def456
                                                 ^^^^^^^^^^^ (Page ID)
   ```

### Variables de Entorno

Crear archivo `.env` en `MCP/PR_Review/`:
```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxx
NOTION_PAGE_ID=abc123def456
```

---

## 💻 Uso del Sistema

### Modo 1: Como Servidor MCP (Recomendado)

#### Configurar Claude Desktop

Editar `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "github-pr-review": {
      "command": "python",
      "args": [
        "C:\\Users\\Agustin\\Desktop\\Agustin\\IA\\MCP\\PR_Review\\pr_analyzer.py"
      ],
      "env": {
        "GITHUB_TOKEN": "ghp_xxxx",
        "NOTION_API_KEY": "secret_xxxx",
        "NOTION_PAGE_ID": "abc123"
      }
    }
  }
}
```

#### Usar en Claude

```
User: Analiza el PR #42 del repositorio facebook/react

Claude: [Usa fetch_pr automáticamente]
Aquí está el análisis del PR #42:

Cambios principales:
- Archivo: src/components/Button.jsx
  - Líneas 15-20: Refactorización de event handlers
  - Mejora: Uso de useCallback para optimización
  
Posibles issues:
- Línea 18: Falta validación de props.onClick

¿Quieres que cree un documento en Notion con este análisis?

User: Sí, por favor

Claude: [Usa create_notion_page automáticamente]
✅ Página creada en Notion: "PR #42 Analysis - React Button Component"
```

### Modo 2: Cliente Python Personalizado

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def analyze_pr():
    server_params = StdioServerParameters(
        command="python",
        args=["pr_analyzer.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Llamar a fetch_pr
            result = await session.call_tool(
                "fetch_pr",
                arguments={
                    "repo_owner": "facebook",
                    "repo_name": "react",
                    "pr_number": 42
                }
            )
            
            print(result.content)
            
            # Crear página en Notion
            await session.call_tool(
                "create_notion_page",
                arguments={
                    "title": "PR #42 Analysis",
                    "content": "Análisis detallado..."
                }
            )

asyncio.run(analyze_pr())
```

### Modo 3: Testing Directo

```bash
python client_test.py
```

---

## 🔧 Componentes Técnicos

### 1. **pr_analyzer.py** (Servidor MCP)

```python
from mcp.server.fastmcp import FastMCP

class PRAnalyzer:
    def __init__(self):
        self.mcp = FastMCP("github_pr_analysis")
        self._register_tools()
    
    def _register_tools(self):
        @self.mcp.tool()
        async def fetch_pr(repo_owner: str, repo_name: str, pr_number: int):
            """Fetch changes from a GitHub pull request."""
            pr_info = fetch_pr_changes(repo_owner, repo_name, pr_number)
            return pr_info
        
        @self.mcp.tool()
        async def create_notion_page(title: str, content: str):
            """Create a Notion page with PR analysis."""
            # Lógica de creación en Notion
            return f"Notion page '{title}' created successfully!"
    
    def run(self):
        self.mcp.run(transport="stdio")
```

**Características:**
- Decorador `@self.mcp.tool()` expone funciones como herramientas MCP
- Comunicación vía stdio (compatible con Claude Desktop)
- Logging a stderr para debugging

### 2. **github_integration.py** (Cliente GitHub)

```python
import requests
import os

def fetch_pr_changes(repo_owner: str, repo_name: str, pr_number: int):
    """Fetch PR details and file changes from GitHub API"""
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"}
    
    # Fetch PR metadata
    pr_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
    pr_response = requests.get(pr_url, headers=headers)
    pr_data = pr_response.json()
    
    # Fetch file changes
    files_url = f"{pr_url}/files"
    files_response = requests.get(files_url, headers=headers)
    files_data = files_response.json()
    
    return {
        "title": pr_data["title"],
        "author": pr_data["user"]["login"],
        "state": pr_data["state"],
        "created_at": pr_data["created_at"],
        "files_changed": len(files_data),
        "additions": pr_data["additions"],
        "deletions": pr_data["deletions"],
        "files": [
            {
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
                "patch": f.get("patch", "")
            }
            for f in files_data
        ]
    }
```

### 3. **Integración Notion**

```python
from notion_client import Client

notion = Client(auth=os.getenv("NOTION_API_KEY"))
page_id = os.getenv("NOTION_PAGE_ID")

notion.pages.create(
    parent={"type": "page_id", "page_id": page_id},
    properties={
        "title": {
            "title": [{"text": {"content": title}}]
        }
    },
    children=[
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content}}]
            }
        }
    ]
)
```

---

## 📊 Ejemplo de Análisis Completo

### Input (Usuario a Claude)

```
Analiza el PR #123 de microsoft/vscode y crea un reporte en Notion
```

### Proceso Interno

1. **Claude llama a `fetch_pr`**:
   ```json
   {
     "repo_owner": "microsoft",
     "repo_name": "vscode",
     "pr_number": 123
   }
   ```

2. **Servidor MCP retorna datos**:
   ```json
   {
     "title": "Fix: Memory leak in extension host",
     "author": "john-doe",
     "state": "open",
     "files_changed": 3,
     "additions": 45,
     "deletions": 12,
     "files": [
       {
         "filename": "src/vs/workbench/api/node/extHost.ts",
         "status": "modified",
         "additions": 30,
         "deletions": 8,
         "patch": "@@ -150,7 +150,10 @@ class ExtensionHost {\n..."
       }
     ]
   }
   ```

3. **Claude analiza los cambios**:
   - Identifica el problema (memory leak)
   - Revisa el patch línea por línea
   - Detecta mejoras (uso de WeakMap)
   - Sugiere tests adicionales

4. **Claude llama a `create_notion_page`**:
   ```json
   {
     "title": "PR #123 Analysis - VSCode Memory Leak Fix",
     "content": "## Summary\nThis PR fixes a memory leak...\n\n## Changes\n- File: extHost.ts\n  - Replaced Map with WeakMap...\n\n## Recommendations\n- Add unit tests for cleanup..."
   }
   ```

5. **Output Final**:
   ```
   ✅ Análisis completado y documentado en Notion
   
   Resumen:
   - PR #123 soluciona memory leak en extension host
   - 3 archivos modificados (+45, -12 líneas)
   - Cambio principal: WeakMap para auto-cleanup
   - Recomendación: Agregar tests de lifecycle
   
   📄 Documento creado: "PR #123 Analysis - VSCode Memory Leak Fix"
   ```

---

## 🔍 Casos de Uso

### 1. **Code Review Asistido**
```
User: Revisa el PR #456 de mi-org/mi-repo y dame feedback sobre:
- Posibles bugs
- Mejoras de performance
- Violaciones de best practices

Claude: [Analiza y retorna feedback detallado]
```

### 2. **Documentación Automática**
```
User: Para cada PR abierto en mi-org/mi-repo, crea un documento en Notion con:
- Resumen de cambios
- Archivos afectados
- Impacto estimado

Claude: [Itera sobre PRs y crea documentos]
```

### 3. **Detección de Riesgos**
```
User: Analiza el PR #789 y marca si:
- Modifica código de autenticación
- Cambia esquemas de base de datos
- Afecta APIs públicas

Claude: [Analiza y clasifica riesgos]
```

### 4. **Onboarding de Desarrolladores**
```
User: Explica qué hace el PR #101 como si fuera para un junior developer

Claude: [Genera explicación didáctica y la guarda en Notion]
```

---

## 🛠️ Extensiones Posibles

### 1. **Webhook para Automatización**

```python
# webhook_server.py
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/github-webhook")
async def handle_pr_event(request: Request):
    payload = await request.json()
    
    if payload["action"] == "opened":
        pr_number = payload["pull_request"]["number"]
        repo = payload["repository"]["full_name"]
        
        # Trigger análisis automático
        await analyze_and_document_pr(repo, pr_number)
    
    return {"status": "ok"}
```

**Configurar en GitHub:**
1. Repo Settings → Webhooks → Add webhook
2. Payload URL: `https://tu-servidor.com/github-webhook`
3. Content type: `application/json`
4. Events: Pull requests

### 2. **Integración con Slack**

```python
@self.mcp.tool()
async def notify_slack(channel: str, message: str):
    """Send PR analysis to Slack channel"""
    slack_client.chat_postMessage(channel=channel, text=message)
```

### 3. **Análisis de Seguridad**

```python
@self.mcp.tool()
async def security_scan(repo_owner: str, repo_name: str, pr_number: int):
    """Scan PR for security vulnerabilities"""
    pr_data = fetch_pr_changes(repo_owner, repo_name, pr_number)
    
    # Buscar patrones peligrosos
    issues = []
    for file in pr_data["files"]:
        if "password" in file["patch"].lower():
            issues.append("Possible hardcoded password")
        if "eval(" in file["patch"]:
            issues.append("Dangerous eval() usage")
    
    return {"security_issues": issues}
```

### 4. **Métricas de PR**

```python
@self.mcp.tool()
async def pr_metrics(repo_owner: str, repo_name: str, pr_number: int):
    """Calculate PR complexity metrics"""
    pr_data = fetch_pr_changes(repo_owner, repo_name, pr_number)
    
    return {
        "complexity_score": calculate_complexity(pr_data),
        "review_time_estimate": estimate_review_time(pr_data),
        "test_coverage_impact": analyze_test_coverage(pr_data)
    }
```

---

## 🚨 Troubleshooting

### Error: "GitHub API rate limit exceeded"

**Solución:**
- Usar token autenticado (aumenta límite a 5000 req/hora)
- Implementar caching de respuestas
- Usar GitHub Apps en lugar de Personal Access Tokens

### Error: "Notion page not found"

**Verificar:**
1. Page ID es correcto
2. Integración tiene acceso a la página
3. API key es válida

### Error: "MCP server not responding"

**Debug:**
```bash
# Ejecutar servidor manualmente para ver errores
python pr_analyzer.py

# Ver logs en stderr
python pr_analyzer.py 2> debug.log
```

---

## 📚 Referencias

- **MCP Protocol**: https://modelcontextprotocol.io/
- **FastMCP**: https://github.com/jlowin/fastmcp
- **GitHub API**: https://docs.github.com/en/rest
- **Notion API**: https://developers.notion.com/

---

**Parte del AI Client Framework - MCP Suite**  
**Versión:** 1.0.0  
**Última actualización:** 2026-02-04
