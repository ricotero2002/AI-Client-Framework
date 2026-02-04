# Multi-MCP Server with FastAPI

**Servidor FastAPI que Expone Múltiples Servidores MCP vía HTTP**

Implementación de múltiples servidores MCP (Model Context Protocol) montados en una sola aplicación FastAPI, permitiendo que agentes de IA accedan a diferentes conjuntos de herramientas a través de endpoints HTTP independientes.

---

## 🎯 Características Principales

### 1. **Arquitectura Multi-Server**
- Múltiples servidores MCP en una sola app FastAPI
- Cada servidor tiene su propio namespace y herramientas
- Gestión unificada de lifecycle

### 2. **Exposición HTTP**
- Endpoints RESTful para cada servidor MCP
- Compatible con clientes HTTP estándar
- CORS habilitado para integraciones web

### 3. **Servidores Incluidos**
- **Echo Server**: Herramientas de ejemplo (echo, reverse)
- **Math Server**: Operaciones matemáticas (add, multiply)
- **Extensible**: Fácil agregar nuevos servidores

### 4. **Gestión de Sesiones**
- AsyncExitStack para lifecycle management
- Inicio/cierre coordinado de todos los servidores
- Manejo robusto de errores

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│                    http://0.0.0.0:8000                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
┌──────────────────┐        ┌──────────────────┐
│  /echo/mcp       │        │  /math/mcp       │
│  Echo MCP Server │        │  Math MCP Server │
└────────┬─────────┘        └────────┬─────────┘
         │                           │
         ▼                           ▼
┌──────────────────┐        ┌──────────────────┐
│  echo_tools:     │        │  math_tools:     │
│  - echo()        │        │  - add()         │
│  - reverse()     │        │  - multiply()    │
└──────────────────┘        └──────────────────┘
```

---

## 📁 Estructura del Proyecto

```
MCP/Multi_mcp/
├── main.py              # FastAPI app principal
├── echo_server.py       # Servidor MCP de echo
├── echo_tools.py        # Herramientas de echo
├── math_server.py       # Servidor MCP de math
├── math_tools.py        # Herramientas matemáticas
└── README.md
```

---

## 🚀 Instalación y Configuración

### Requisitos

```bash
pip install fastapi uvicorn fastmcp
```

### Ejecución

```bash
cd MCP/Multi_mcp
python main.py
```

**Salida:**
```
Rutas registradas en FastAPI:
📂 Mount: /echo -> echo
   └── 📍 /echo/mcp
📂 Mount: /math -> math
   └── 📍 /math/mcp

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 💻 Uso del Sistema

### Modo 1: Cliente HTTP (curl/Postman)

#### Listar Herramientas Disponibles

```bash
# Echo Server
curl http://localhost:8000/echo/mcp/tools

# Math Server
curl http://localhost:8000/math/mcp/tools
```

#### Llamar a una Herramienta

```bash
# Echo: Repetir mensaje
curl -X POST http://localhost:8000/echo/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "echo",
    "arguments": {"message": "Hello MCP!"}
  }'

# Math: Sumar números
curl -X POST http://localhost:8000/math/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "add",
    "arguments": {"a": 10, "b": 32}
  }'
```

### Modo 2: Cliente Python

```python
import requests

# Llamar a echo
response = requests.post(
    "http://localhost:8000/echo/mcp/call",
    json={
        "tool": "echo",
        "arguments": {"message": "Test"}
    }
)
print(response.json())  # {"result": "Test"}

# Llamar a math
response = requests.post(
    "http://localhost:8000/math/mcp/call",
    json={
        "tool": "multiply",
        "arguments": {"a": 5, "b": 7}
    }
)
print(response.json())  # {"result": 35}
```

### Modo 3: Integración con Agente LLM

```python
from client_factory import create_client
from prompt import Prompt

client = create_client('gemini')

# Definir herramientas disponibles
tools = [
    {
        "name": "echo",
        "description": "Repeat a message",
        "parameters": {
            "message": {"type": "string", "description": "Message to echo"}
        },
        "endpoint": "http://localhost:8000/echo/mcp/call"
    },
    {
        "name": "add",
        "description": "Add two numbers",
        "parameters": {
            "a": {"type": "number"},
            "b": {"type": "number"}
        },
        "endpoint": "http://localhost:8000/math/mcp/call"
    }
]

prompt = Prompt()
prompt.set_system("You have access to echo and math tools via HTTP.")
prompt.set_user_input("What is 15 + 27?")
prompt.set_tools(tools)

response, _ = client.get_response(prompt)
# Agent decides to call 'add' tool
# Execute HTTP request to math server
# Return result to user
```

---

## 🔧 Componentes Técnicos

### 1. **main.py** (Aplicación Principal)

```python
import contextlib
from fastapi import FastAPI
from echo_server import mcp as echo_mcp
from math_server import mcp as math_mcp

# Lifespan manager para coordinar múltiples servidores
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        # Iniciar ambos servidores
        await stack.enter_async_context(echo_mcp.session_manager.run())
        await stack.enter_async_context(math_mcp.session_manager.run())
        yield

app = FastAPI(lifespan=lifespan)

# Montar cada servidor en su propio path
app.mount("/echo", echo_mcp.streamable_http_app())
app.mount("/math", math_mcp.streamable_http_app())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Características:**
- `AsyncExitStack`: Gestiona lifecycle de múltiples async context managers
- `lifespan`: Hook de FastAPI para startup/shutdown
- `mount`: Monta sub-aplicaciones en rutas específicas

### 2. **echo_server.py** (Servidor Echo)

```python
from fastmcp import FastMCP
from echo_tools import echo, reverse

mcp = FastMCP("Echo Server")

@mcp.tool()
def echo_tool(message: str) -> str:
    """Repeat the input message"""
    return echo(message)

@mcp.tool()
def reverse_tool(text: str) -> str:
    """Reverse the input text"""
    return reverse(text)
```

### 3. **echo_tools.py** (Lógica de Herramientas)

```python
def echo(message: str) -> str:
    """Echo back the message"""
    return message

def reverse(text: str) -> str:
    """Reverse the text"""
    return text[::-1]
```

### 4. **math_server.py** (Servidor Math)

```python
from fastmcp import FastMCP
from math_tools import add, multiply

mcp = FastMCP("Math Server")

@mcp.tool()
def add_tool(a: float, b: float) -> float:
    """Add two numbers"""
    return add(a, b)

@mcp.tool()
def multiply_tool(a: float, b: float) -> float:
    """Multiply two numbers"""
    return multiply(a, b)
```

### 5. **math_tools.py** (Lógica Matemática)

```python
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b

def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b
```

---

## 🌐 Endpoints Disponibles

### Echo Server (`/echo/mcp`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/echo/mcp/tools` | Lista herramientas disponibles |
| POST | `/echo/mcp/call` | Ejecuta una herramienta |
| GET | `/echo/mcp/health` | Health check |

**Herramientas:**
- `echo_tool(message: str)`: Repite el mensaje
- `reverse_tool(text: str)`: Invierte el texto

### Math Server (`/math/mcp`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/math/mcp/tools` | Lista herramientas disponibles |
| POST | `/math/mcp/call` | Ejecuta una herramienta |
| GET | `/math/mcp/health` | Health check |

**Herramientas:**
- `add_tool(a: float, b: float)`: Suma dos números
- `multiply_tool(a: float, b: float)`: Multiplica dos números

---

## 📊 Ejemplos de Uso

### Ejemplo 1: Echo Simple

**Request:**
```bash
curl -X POST http://localhost:8000/echo/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "echo_tool",
    "arguments": {"message": "Hello World"}
  }'
```

**Response:**
```json
{
  "result": "Hello World"
}
```

### Ejemplo 2: Reverse Text

**Request:**
```bash
curl -X POST http://localhost:8000/echo/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "reverse_tool",
    "arguments": {"text": "MCP Server"}
  }'
```

**Response:**
```json
{
  "result": "revreS PCM"
}
```

### Ejemplo 3: Operaciones Matemáticas

**Request:**
```bash
curl -X POST http://localhost:8000/math/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "add_tool",
    "arguments": {"a": 42, "b": 58}
  }'
```

**Response:**
```json
{
  "result": 100
}
```

### Ejemplo 4: Multiplicación

**Request:**
```bash
curl -X POST http://localhost:8000/math/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "multiply_tool",
    "arguments": {"a": 12, "b": 8}
  }'
```

**Response:**
```json
{
  "result": 96
}
```

---

## 🛠️ Agregar Nuevos Servidores

### Paso 1: Crear Herramientas

```python
# weather_tools.py
def get_temperature(city: str) -> float:
    """Get current temperature for a city"""
    # Lógica de API weather
    return 22.5

def get_forecast(city: str, days: int) -> list:
    """Get weather forecast"""
    return [{"day": 1, "temp": 23}, {"day": 2, "temp": 21}]
```

### Paso 2: Crear Servidor MCP

```python
# weather_server.py
from fastmcp import FastMCP
from weather_tools import get_temperature, get_forecast

mcp = FastMCP("Weather Server")

@mcp.tool()
def temperature(city: str) -> float:
    """Get current temperature"""
    return get_temperature(city)

@mcp.tool()
def forecast(city: str, days: int = 3) -> list:
    """Get weather forecast"""
    return get_forecast(city, days)
```

### Paso 3: Integrar en main.py

```python
from weather_server import mcp as weather_mcp

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(echo_mcp.session_manager.run())
        await stack.enter_async_context(math_mcp.session_manager.run())
        await stack.enter_async_context(weather_mcp.session_manager.run())  # ← Nuevo
        yield

app.mount("/weather", weather_mcp.streamable_http_app())  # ← Nuevo endpoint
```

### Paso 4: Usar el Nuevo Servidor

```bash
curl -X POST http://localhost:8000/weather/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "temperature",
    "arguments": {"city": "Buenos Aires"}
  }'
```

---

## 🔍 Casos de Uso

### 1. **Microservicios de Herramientas**
- Cada servidor MCP es un microservicio independiente
- Escalado horizontal por servidor
- Deployment independiente

### 2. **API Gateway para Agentes**
- Punto único de acceso para múltiples capacidades
- Routing automático por namespace
- Autenticación centralizada

### 3. **Testing de Herramientas MCP**
- Endpoints HTTP fáciles de testear
- No requiere cliente MCP completo
- Integración con herramientas de testing estándar

### 4. **Integración Web**
- Llamadas AJAX desde frontend
- WebSockets para streaming (si se implementa)
- CORS configurado para cross-origin

---

## 🚀 Extensiones Posibles

### 1. **Autenticación**

```python
from fastapi import Header, HTTPException

async def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization[7:]
    # Verificar token
    return token

@app.post("/echo/mcp/call")
async def call_echo(request: dict, token: str = Depends(verify_token)):
    # Ejecutar con autenticación
    pass
```

### 2. **Rate Limiting**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/math/mcp/call")
@limiter.limit("10/minute")
async def call_math(request: Request):
    # Máximo 10 llamadas por minuto
    pass
```

### 3. **Logging y Métricas**

```python
from prometheus_client import Counter, Histogram

tool_calls = Counter('mcp_tool_calls_total', 'Total tool calls', ['server', 'tool'])
call_duration = Histogram('mcp_call_duration_seconds', 'Call duration', ['server', 'tool'])

@app.post("/echo/mcp/call")
async def call_echo(request: dict):
    tool_calls.labels(server='echo', tool=request['tool']).inc()
    with call_duration.labels(server='echo', tool=request['tool']).time():
        # Ejecutar herramienta
        pass
```

### 4. **WebSocket Support**

```python
from fastapi import WebSocket

@app.websocket("/echo/mcp/ws")
async def echo_websocket(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        result = await execute_tool(data['tool'], data['arguments'])
        await websocket.send_json({"result": result})
```

### 5. **Caching**

```python
from functools import lru_cache
import redis

redis_client = redis.Redis(host='localhost', port=6379)

@mcp.tool()
def cached_operation(param: str) -> str:
    cache_key = f"op:{param}"
    cached = redis_client.get(cache_key)
    
    if cached:
        return cached.decode()
    
    result = expensive_operation(param)
    redis_client.setex(cache_key, 3600, result)  # Cache 1 hora
    return result
```

---

## 🚨 Troubleshooting

### Error: "Port 8000 already in use"

**Solución:**
```bash
# Cambiar puerto en main.py
uvicorn.run(app, host="0.0.0.0", port=8001)

# O matar proceso existente
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Error: "Module 'fastmcp' not found"

**Solución:**
```bash
pip install fastmcp
# O si estás en venv
.venv\Scripts\activate
pip install fastmcp
```

### Error: "Lifespan startup failed"

**Debug:**
```python
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(echo_mcp.session_manager.run())
            await stack.enter_async_context(math_mcp.session_manager.run())
            yield
    except Exception as e:
        print(f"Lifespan error: {e}")
        import traceback
        traceback.print_exc()
        raise
```

## 🔮 Trabajo Futuro

1. **Dashboard de Monitoreo**: UI para ver llamadas en tiempo real
2. **Auto-discovery**: Registro dinámico de servidores
3. **Load Balancing**: Distribución de carga entre instancias
4. **Versioning**: Soporte para múltiples versiones de herramientas
5. **GraphQL API**: Alternativa a REST para queries complejas

---

**Parte del AI Client Framework - MCP Suite**  
**Versión:** 1.0.0  
**Última actualización:** 2026-02-04
