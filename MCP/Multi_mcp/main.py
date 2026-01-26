import contextlib
from fastapi import FastAPI
from echo_server import mcp as echo_mcp
from fastapi.routing import Mount
from math_server import mcp as math_mcp
# Create a combined lifespan to manage both session managers
@contextlib.asynccontextmanager
async def lifespan (app: FastAPI):
    async with contextlib. AsyncExitStack() as stack:
        await stack.enter_async_context(echo_mcp.session_manager.run())
        await stack.enter_async_context(math_mcp.session_manager.run())
        yield

app = FastAPI(lifespan=lifespan)
app.mount("/echo", echo_mcp.streamable_http_app()) ## this is http://0.0.0.0:8000/echo/mcp 
app.mount("/math", math_mcp.streamable_http_app()) ## this is http://0.0.0.0:8000/math/mcp


print("Rutas registradas en FastAPI:")
for route in app.routes:
    if isinstance(route, Mount):
        print(f"📂 Mount: {route.path} -> {route.name}")
        # Intentamos ver las rutas internas del sub-app montado
        for sub_route in route.app.routes:
            print(f"   └── 📍 {route.path}{sub_route.path}")
    else:
        print(f"📍 {route.path}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)