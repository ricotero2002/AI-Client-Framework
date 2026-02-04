# Human-in-the-Loop IDL Agent

**Agente Autónomo con Supervisión Humana y Sistema de Rollback Automático**

Un agente inteligente basado en **LangGraph** y **MCP (Model Context Protocol)** que ejecuta comandos de terminal de forma autónoma, con aprobación humana para operaciones peligrosas, sistema de backup/restore automático, y capacidad de aprendizaje de errores pasados.

---

## 🎯 Características Principales

### 1. **Arquitectura de Doble Agente**
- **Planner Agent**: Genera planes estructurados con evaluación de riesgo (safe/unsafe)
- **Executor Agent**: Ejecuta el plan usando herramientas MCP con lógica ReAct

### 2. **Supervisión Humana Inteligente**
- **Aprobación selectiva**: Solo solicita aprobación para operaciones peligrosas
- **Puntos de interrupción**: `human_approval` (pre-ejecución) y `user_verification` (post-ejecución)
- **Feedback estructurado**: Captura razones de rechazo para aprendizaje

### 3. **Sistema de Backup y Rollback**
- **Backup automático**: Crea copias temporales antes de operaciones unsafe
- **Límite de tamaño**: Solo hace backup si el directorio es < 500MB
- **Restauración inteligente**: Si el usuario rechaza cambios, restaura el estado previo
- **Cleanup automático**: Elimina backups temporales al finalizar

### 4. **Aprendizaje de Errores (Golden Dataset)**
- **Persistencia de feedback**: Guarda rechazos en `golden_dataset.json`
- **Inyección en prompts**: Los últimos 3 errores se incluyen en el contexto del planner
- **Mejora continua**: El agente aprende de sus errores y evita repetirlos

### 5. **Protección contra Alucinaciones**
- **Path Injection Fix**: Middleware que fuerza el path correcto en cada tool call
- **Validación estricta**: Detecta y corrige paths alucinados por el LLM
- **Atomic Execution**: Cada comando se ejecuta en un terminal limpio

### 6. **Auditoría Completa**
- **Logging detallado**: Todas las acciones se registran en `execution_audit.log`
- **Timestamps**: Cada entrada tiene fecha/hora exacta
- **Trazabilidad**: Queries, planes, comandos, outputs y decisiones humanas

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│                  "Borra el archivo más grande"                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PLANNER NODE                                  │
│  - Analiza la tarea                                             │
│  - Genera plan paso a paso                                      │
│  - Evalúa riesgo (safe/unsafe)                                  │
│  - Aprende de errores pasados (Golden Dataset)                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  ¿Es seguro?   │
              └────────┬───────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
      [SAFE]                     [UNSAFE]
         │                           │
         │                           ▼
         │              ┌─────────────────────────┐
         │              │   HUMAN_APPROVAL        │
         │              │  Usuario aprueba/rechaza│
         │              └──────────┬──────────────┘
         │                         │
         │                    [APROBADO]
         │                         │
         │                         ▼
         │              ┌─────────────────────────┐
         │              │   CREATE_BACKUP         │
         │              │  Backup automático      │
         │              └──────────┬──────────────┘
         │                         │
         └─────────────┬───────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT NODE (ReAct Loop)                       │
│  - Ejecuta comandos con run_server_command                      │
│  - Path Injection Fix (fuerza path correcto)                    │
│  - Verifica resultados                                          │
│  - Itera hasta completar tarea (max 20 iteraciones)             │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  USER_VERIFICATION                               │
│  Usuario verifica cambios: Aprobar / Rechazar                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
    [APROBADO]                  [RECHAZADO]
         │                           │
         ▼                           ▼
┌──────────────────┐    ┌────────────────────────┐
│  FINAL_SUMMARY   │    │   RESTORE_BACKUP       │
│  Resumen final   │    │  Rollback completo     │
└────────┬─────────┘    └──────────┬─────────────┘
         │                         │
         ▼                         ▼
       [END]              ┌────────────────────┐
                          │  PLANNER (retry)   │
                          │  Con feedback      │
                          └────────────────────┘
```

---

## 📁 Estructura del Proyecto

```
Human_IDL/
├── client.py                  # Agente principal con LangGraph
├── server_terminal.py         # Servidor MCP con herramienta run_server_command
├── execution_audit.log        # Log de auditoría (auto-generado)
├── golden_dataset.json        # Dataset de errores aprendidos (auto-generado)
└── README.md
```

---

## 🚀 Instalación y Configuración

### Requisitos Previos
- Python 3.10+
- PowerShell (Windows)
- API Key de Google Gemini

### 1. Instalar Dependencias

```bash
pip install langgraph langchain-mcp-adapters mcp python-dotenv pydantic
```

### 2. Configurar Variables de Entorno

Crear archivo `.env` en el directorio raíz del proyecto (IA/):
```env
GEMINI_API_KEY=tu_api_key_aqui
```

### 3. Verificar Instalación

```bash
python client.py --help
```

---

## 💻 Uso del Sistema

### Ejecución Básica

```bash
python client.py server_terminal.py
```

### Flujo de Interacción

1. **Ingresar Query**:
   ```
   👤 Query (o 'quit'): Borra el archivo más grande
   ```

2. **Especificar Directorio**:
   ```
   📂 Directorio: C:\Users\Agustin\Desktop\Test
   ```

3. **El sistema genera un plan**:
   ```
   📋 PLAN (UNSAFE):
   1. Find largest file: Get-ChildItem -File -Recurse | Sort-Object Length -Descending | Select-Object -First 1
   2. Delete it: Remove-Item -Force
   3. Verify deletion: Test-Path
   ```

4. **Aprobación Humana** (solo si es UNSAFE):
   ```
   ⚠️ PLAN PROPUESTO: [plan detallado]
   ¿Aprobar ejecución? (s/n): s
   ```

5. **Ejecución Automática**:
   ```
   [TOOL] run_server_command
   [OUTPUT] C:\Users\Agustin\Desktop\Test\large_file.zip
   [TOOL] run_server_command
   [OUTPUT] Deleted
   [TOOL] run_server_command
   [OUTPUT] False
   ```

6. **Verificación Final**:
   ```
   🤖 El agente indica que ha terminado.
   ¿Verificar cambios? (s = Aprobar / n = Rechazar y Restaurar): s
   ```

7. **Resumen Final**:
   ```
   📊 FINAL SUMMARY:
   Successfully deleted the largest file (large_file.zip, 500MB).
   Verified deletion with Test-Path returning False.
   ```

---

## 🔧 Componentes Técnicos

### 1. **Planner Node**

**Responsabilidades:**
- Analizar la query del usuario
- Generar plan estructurado con Pydantic (`PlanResponse`)
- Evaluar riesgo (safe/unsafe)
- Incorporar feedback de errores pasados

**Structured Output:**
```python
class PlanResponse(BaseModel):
    plan: str = Field(description="The detailed step-by-step plan.")
    is_safe: bool = Field(description="True if read-only, False if modifies files.")
```

**Few-Shot Examples:**
```python
PLANNER_EXAMPLES = [
    {
        "user": "Busca la imagen más pesada y bórrala.",
        "assistant": json.dumps({
            "plan": "1. Identify and delete the largest image...",
            "is_safe": False
        })
    },
    ...
]
```

### 2. **Agent Orchestrator Node**

**Responsabilidades:**
- Ejecutar el plan usando herramientas MCP
- Aplicar lógica ReAct (Thought → Tool Call → Observation)
- Validar y corregir paths alucinados
- Iterar hasta completar la tarea

**Path Injection Fix:**
```python
if fc["name"] == "run_server_command":
    correct_path = state["target_dir"]
    current_path = fc["args"].get("path", "")
    
    if current_path != correct_path:
        print_debug_step("FIX", f"Path Hallucination Detected: '{current_path}' -> Forces to: '{correct_path}'")
        fc["args"]["path"] = correct_path
```

### 3. **Backup Manager**

**Métodos:**
- `create_backup(target_dir)`: Crea copia temporal
- `restore_backup(backup_path, target_dir)`: Restaura estado previo
- `delete_backup(backup_path)`: Limpia backup temporal
- `cleanup_all()`: Limpia todos los backups activos

**Límites:**
```python
MAX_BACKUP_SIZE_MB = 500  # Solo hace backup si dir < 500MB
```

### 4. **Golden Dataset Manager**

**Estructura del Dataset:**
```json
[
  {
    "query": "Borra todos los archivos .log",
    "rejected_plan": "1. Remove-Item *.log -Recurse -Force",
    "reason": "No verificó antes de borrar, podría eliminar logs importantes"
  }
]
```

**Inyección en Prompts:**
```python
def get_formatted_feedback(self):
    prompt = "\n### 🧠 LEARNINGS FROM PAST MISTAKES:\n"
    for item in self.data[-3:]:  # Últimos 3 errores
        prompt += f"- Mistake: For '{item['query']}', plan rejected because: '{item['reason']}'.\n"
    return prompt
```

### 5. **Audit Logger**

**Formato de Logs:**
```
[2026-02-04 12:30:45] [USER_QUERY]
Query: Borra el archivo más grande
Context: C:\Users\Agustin\Desktop\Test
--------------------------------------------------------------------------------
[2026-02-04 12:30:47] [PLANNER]
Proposed Plan: 1. Find largest file...
Safe: False
--------------------------------------------------------------------------------
[2026-02-04 12:30:50] [APPROVAL_DECISION]
Plan: [plan detallado]
Decision: s
--------------------------------------------------------------------------------
[2026-02-04 12:30:55] [COMMAND_ATTEMPT]
Tool: run_server_command
Args: {'command': 'Get-ChildItem -File | Sort-Object Length -Descending | Select-Object -First 1', 'path': 'C:\\Users\\Agustin\\Desktop\\Test'}
--------------------------------------------------------------------------------
[2026-02-04 12:30:56] [TOOL_OUTPUT]
Tool: run_server_command
Output: C:\Users\Agustin\Desktop\Test\large_file.zip...
--------------------------------------------------------------------------------
[2026-02-04 12:31:00] [VERIFICATION]
User APPROVED changes.
--------------------------------------------------------------------------------
[2026-02-04 12:31:02] [FINAL_SUMMARY]
Successfully deleted the largest file (large_file.zip, 500MB)...
--------------------------------------------------------------------------------
```

---

## 🛡️ Protecciones y Validaciones

### 1. **Atomic Execution Rule**
```
CRITICAL: The terminal resets after every tool call.
Variables ($x) are LOST. Use piping or single commands.
```

**Ejemplo Correcto:**
```powershell
Get-ChildItem -Include *.png,*.jpg -Recurse | Sort-Object Length -Descending | Select-Object -First 1 | Remove-Item -Force -PassThru
```

**Ejemplo Incorrecto:**
```powershell
$file = Get-ChildItem -File | Sort-Object Length -Descending | Select-Object -First 1
Remove-Item $file  # ❌ $file no existe en el nuevo terminal
```

### 2. **Path Strictness**
```
You MUST use exactly path='{target_dir}' for every tool call.
Do NOT use the user query as a path.
```

### 3. **Output Visibility**
```
DO NOT use 'Write-Host'. It is invisible to you.
ALWAYS use 'Write-Output'.
```

### 4. **One-Shot Execution**
```
If the user asks for a SINGLE action (e.g., "delete the largest file"),
find it, delete it, verify it is gone, and then STOP.
DO NOT loop to find the "next" largest file.
```

### 5. **Max Iterations**
```python
MAX_ITERATIONS = 20  # Previene loops infinitos
```

---

## 📊 Ejemplos de Uso

### Ejemplo 1: Operación Segura (Sin Aprobación)

**Query:** "Listame los 3 archivos más grandes"

**Flujo:**
1. Planner genera plan con `is_safe: True`
2. Se salta `human_approval`
3. Agent ejecuta directamente
4. Usuario verifica resultado final

**Comando Ejecutado:**
```powershell
Get-ChildItem -File -Recurse | Sort-Object Length -Descending | Select-Object -First 3 | Select-Object Name, @{Name='Size(MB)';Expression={$_.Length / 1MB}}
```

### Ejemplo 2: Operación Peligrosa (Con Aprobación y Backup)

**Query:** "Borra todos los archivos .tmp"

**Flujo:**
1. Planner genera plan con `is_safe: False`
2. Sistema solicita aprobación humana
3. Usuario aprueba
4. Sistema crea backup automático
5. Agent ejecuta comandos
6. Usuario verifica cambios
7. Si aprueba → Elimina backup
8. Si rechaza → Restaura backup y re-planifica

**Comandos Ejecutados:**
```powershell
# 1. Listar archivos .tmp
Get-ChildItem -Filter *.tmp -Recurse | Select-Object FullName

# 2. Eliminar
Get-ChildItem -Filter *.tmp -Recurse | Remove-Item -Force

# 3. Verificar
Get-ChildItem -Filter *.tmp -Recurse
```

### Ejemplo 3: Rollback por Rechazo

**Query:** "Reorganiza los archivos por tipo"

**Flujo:**
1. Planner genera plan de reorganización
2. Usuario aprueba
3. Backup creado
4. Agent mueve archivos a carpetas por extensión
5. Usuario verifica y **rechaza** (no le gusta la organización)
6. Sistema restaura backup
7. Usuario da feedback: "Prefiero organización por fecha, no por tipo"
8. Feedback se guarda en `golden_dataset.json`
9. Planner genera nuevo plan considerando el feedback
10. Ciclo se repite

---

## 🧠 Integración con el Framework

### Uso del Wrapper de Prompts

```python
from prompt import Prompt, convert_langchain_tool_to_gemini

# Crear prompt estructurado
prompt = Prompt()
prompt.set_system(get_planner_prompt(target_dir))
prompt.set_output_schema(PlanResponse)

# Agregar few-shot examples
for ex in PLANNER_EXAMPLES:
    prompt.add_few_shot_example(ex['user'], ex['assistant'])

# Agregar query del usuario
prompt.add_user_message(user_input)

# Obtener respuesta con validación automática
resp, _ = client.get_response(prompt)
_, plan_data, _ = prompt.validate_response(resp)
```

### Conversión de Herramientas MCP a Gemini

```python
# Cargar herramientas MCP
lc_tools = await load_mcp_tools(session)

# Convertir a formato Gemini
gemini_tools = [convert_langchain_tool_to_gemini(t) for t in lc_tools]

# Agregar al prompt
prompt.set_tools(gemini_tools)
```

### Manejo de Tool Calls

```python
# Agregar mensajes de herramientas al historial
for msg in state["messages"]:
    if isinstance(msg, ToolMessage):
        prompt.add_tool_message(msg.name, str(msg.content)[:10000], msg.tool_call_id)
```

---

## 🔍 Debugging y Monitoreo

### Debug Visual en Terminal

```python
def print_debug_step(step_type: str, content: str, extra: str = ""):
    colors = {
        "PLAN": "\033[96m",      # Cyan
        "TOOL": "\033[93m",      # Yellow
        "OUTPUT": "\033[90m",    # Gray
        "ERROR": "\033[91m",     # Red
        "SUCCESS": "\033[92m",   # Green
        "AUDIT": "\033[95m"      # Magenta
    }
    print(f"{colors[step_type]}[{step_type}]\033[0m {content} {extra}")
```

**Salida:**
```
[PLAN] 1. Find largest file: Get-ChildItem...
[TOOL] run_server_command
[OUTPUT] C:\Users\Agustin\Desktop\Test\large_file.zip
[SUCCESS] Backup temporal creado en: C:\Temp\agent_backup_xyz
```

### Análisis de Logs

```bash
# Ver últimas 50 líneas del log
Get-Content execution_audit.log -Tail 50

# Buscar errores
Select-String -Path execution_audit.log -Pattern "ERROR"

# Filtrar por tipo de entrada
Select-String -Path execution_audit.log -Pattern "\[VERIFICATION\]"
```

---

## ⚙️ Configuración Avanzada

### Ajustar Límites

```python
# En client.py
MAX_ITERATIONS = 20          # Máximo de iteraciones del agente
MAX_BACKUP_SIZE_MB = 500     # Tamaño máximo para backup automático
```

### Cambiar Modelo

```python
# En client.py, línea ~211
client.select_model('gemini-2.5-flash')  # Cambiar a otro modelo
```

### Personalizar Few-Shot Examples

```python
PLANNER_EXAMPLES = [
    {
        "user": "Tu ejemplo de query",
        "assistant": json.dumps({
            "plan": "Tu plan paso a paso",
            "is_safe": False  # o True
        })
    }
]
```

---

## 🚨 Limitaciones Conocidas

1. **Solo PowerShell**: Actualmente solo funciona en Windows con PowerShell
2. **Backup limitado**: No hace backup de directorios > 500MB
3. **Contexto limitado**: Máximo 20 iteraciones por tarea
4. **Sin paralelización**: Comandos se ejecutan secuencialmente
5. **Dependencia de LLM**: La calidad del plan depende del modelo usado

---

## 🔮 Trabajo Futuro

### 1. **Multi-Platform Support**
- Soporte para Bash (Linux/Mac)
- Detección automática de OS
- Comandos multiplataforma

### 2. **Backup Incremental**
- Solo guardar archivos modificados
- Compresión de backups
- Soporte para directorios grandes

### 3. **Paralelización**
- Ejecutar comandos independientes en paralelo
- Detección automática de dependencias

### 4. **Mejoras en Aprendizaje**
- Fine-tuning del planner con golden dataset
- Clustering de errores similares
- Sugerencias proactivas basadas en historial

### 5. **UI Web**
- Dashboard para monitoreo en tiempo real
- Visualización de grafos de ejecución
- Aprobación remota de operaciones

### 6. **Integración con Git**
- Commits automáticos antes de operaciones peligrosas
- Rollback usando git reset
- Tracking de cambios en repositorios

---

**Desarrollado como parte del AI Client Framework**  
**Versión:** 1.0.0  
**Última actualización:** 2026-02-04
