"""
API REST del Agente Médico con FastAPI.

Endpoints:
    POST /chat              → Enviar mensaje y recibir respuesta
    POST /sessions          → Crear nueva sesión de conversación
    GET  /sessions/{id}     → Ver historial de una sesión
    DELETE /sessions/{id}   → Eliminar sesión

Uso:
    python -m agente.api
"""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Cargar .env antes de importar config
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google.adk.runners import Runner
from google.genai import types

from . import config
from .agent import create_runner


# ─── Modelos Pydantic (Request / Response) ────────────────────────────────────


class ChatRequest(BaseModel):
    """Petición de chat."""

    message: str = Field(..., min_length=1, description="Mensaje del usuario")
    session_id: str | None = Field(
        None, description="ID de sesión. Si no se envía, se crea una nueva."
    )


class ChatResponse(BaseModel):
    """Respuesta del chat."""

    response: str = Field(..., description="Respuesta del agente")
    session_id: str = Field(..., description="ID de la sesión usada")


class SessionResponse(BaseModel):
    """Respuesta al crear una sesión."""

    session_id: str
    message: str


class HealthResponse(BaseModel):
    """Respuesta de salud del servicio."""

    status: str
    model: str
    mcp_url: str


# ─── Estado global ────────────────────────────────────────────────────────────

_runner: Runner | None = None
_session_service = None
_active_sessions: set[str] = set()


# ─── Lifecycle ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa el runner y session_service al arrancar el servidor."""
    global _runner, _session_service

    print("⏳ Inicializando agente y conectando al MCP de Graphiti...")
    _runner, _session_service = create_runner()
    print("✅ Agente inicializado correctamente.")
    print(f"   Modelo:  {config.AGENT_MODEL}")
    print(f"   MCP URL: {config.MCP_SERVER_URL}")

    yield

    print("🛑 Apagando servidor...")


# ─── App FastAPI ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Doctor AI API",
    description="API del Agente Médico con Grafo de Conocimiento (Google ADK + MCP Graphiti)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: permitir llamadas desde cualquier frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _ensure_session(session_id: str) -> str:
    """Crea la sesión si no existe. Devuelve el session_id."""
    if session_id not in _active_sessions:
        await _session_service.create_session(
            app_name=config.APP_NAME,
            user_id="api_user",
            session_id=session_id,
        )
        _active_sessions.add(session_id)
    return session_id


async def _run_turn(session_id: str, message: str) -> str:
    """Ejecuta un turno de conversación y devuelve la respuesta."""
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)],
    )

    response_text = ""
    async for event in _runner.run_async(
        user_id="api_user",
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text

    return response_text


# ─── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    """Estado de salud del servicio."""
    return HealthResponse(
        status="ok",
        model=config.AGENT_MODEL,
        mcp_url=config.MCP_SERVER_URL,
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Enviar un mensaje al agente y recibir su respuesta.

    - Si envías `session_id`, continúa la conversación existente (con memoria).
    - Si no envías `session_id`, se crea una sesión nueva automáticamente.
    """
    if _runner is None:
        raise HTTPException(status_code=503, detail="Agente no inicializado")

    # Crear o reusar sesión
    session_id = request.session_id or str(uuid.uuid4())
    await _ensure_session(session_id)

    # Ejecutar turno
    try:
        response = await _run_turn(session_id, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del agente: {str(e)}")

    if not response:
        raise HTTPException(
            status_code=500,
            detail="El agente no generó respuesta. Intenta reformular tu pregunta.",
        )

    return ChatResponse(response=response, session_id=session_id)


@app.post("/sessions", response_model=SessionResponse, tags=["Sesiones"])
async def create_session():
    """Crear una nueva sesión de conversación."""
    if _session_service is None:
        raise HTTPException(status_code=503, detail="Agente no inicializado")

    session_id = str(uuid.uuid4())
    await _ensure_session(session_id)

    return SessionResponse(
        session_id=session_id,
        message="Sesión creada correctamente",
    )


@app.delete("/sessions/{session_id}", response_model=SessionResponse, tags=["Sesiones"])
async def delete_session(session_id: str):
    """Eliminar una sesión y su historial de conversación."""
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    try:
        await _session_service.delete_session(
            app_name=config.APP_NAME,
            user_id="api_user",
            session_id=session_id,
        )
    except Exception:
        pass  # La sesión puede no existir en el service pero sí en nuestro tracking

    _active_sessions.discard(session_id)

    return SessionResponse(
        session_id=session_id,
        message="Sesión eliminada correctamente",
    )


# ─── Entry point ─────────────────────────────────────────────────────────────

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8089"))

if __name__ == "__main__":
    import uvicorn

    print()
    print("=" * 65)
    print("  🏥  DOCTOR AI — API REST")
    print("=" * 65)
    print(f"  Servidor:  http://{API_HOST}:{API_PORT}")
    print(f"  Docs:      http://localhost:{API_PORT}/docs")
    print(f"  Modelo:    {config.AGENT_MODEL}")
    print(f"  MCP URL:   {config.MCP_SERVER_URL}")
    print("=" * 65)
    print()

    uvicorn.run(
        "agente.api:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
    )
