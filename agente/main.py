"""
CLI interactivo del Agente Médico.

Punto de entrada principal. Ejecuta un bucle de conversación donde el usuario
puede chatear con Doctor AI, que consulta automáticamente el Grafo de Conocimiento
Médico a través del MCP de Graphiti.

Uso:
    python -m agente.main
"""

import asyncio
import os
import uuid
from pathlib import Path

# Cargar variables de entorno desde .env ANTES de importar config
from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

from google.adk.runners import Runner
from google.genai import types

from . import config
from .agent import create_runner


def _print_banner():
    """Muestra el banner de bienvenida."""
    print()
    print("=" * 65)
    print("  🏥  DOCTOR AI — Agente Médico con Grafo de Conocimiento")
    print("=" * 65)
    print(f"  Modelo:    {config.AGENT_MODEL}")
    print(f"  MCP URL:   {config.MCP_SERVER_URL}")
    print("-" * 65)
    print("  Escribe tu pregunta médica. Comandos especiales:")
    print("    'salir' / 'exit'  → Terminar la conversación")
    print("    'nueva' / 'new'   → Nueva conversación (resetea memoria)")
    print("=" * 65)
    print()


async def _run_turn(runner: Runner, user_id: str, session_id: str, message: str) -> str:
    """
    Ejecuta un turno de conversación y devuelve la respuesta del agente.

    El Runner se encarga de:
    1. Cargar el historial de la sesión (memoria)
    2. Enviar el mensaje + historial al LLM
    3. Si el LLM decide usar una herramienta, ejecutarla via MCP
    4. Generar la respuesta final
    5. Guardar todo en la sesión (memoria actualizada)
    """
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)],
    )

    response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        # Recoger solo los eventos finales del agente (no los intermedios de herramientas)
        if event.is_final_response():
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text

    return response_text


async def main():
    """Bucle principal del CLI interactivo."""
    _print_banner()

    # ── Crear Runner + Session Service ───────────────────────────────────
    print("⏳ Inicializando agente y conectando al MCP de Graphiti...")
    try:
        runner, session_service = create_runner()
    except Exception as e:
        print(f"\n❌ Error al inicializar el agente: {e}")
        print("   Asegúrate de que el servidor MCP de Graphiti está ejecutándose.")
        print(f"   URL esperada: {config.MCP_SERVER_URL}")
        return

    print("✅ Agente inicializado correctamente.\n")

    # ── Variables de sesión ───────────────────────────────────────────────
    user_id = "medgraph_user"
    session_id = str(uuid.uuid4())

    # Crear sesión inicial
    session = await session_service.create_session(
        app_name=config.APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    print(f"📋 Sesión creada: {session_id[:8]}...\n")

    # ── Bucle de conversación ────────────────────────────────────────────
    while True:
        try:
            user_input = input("👤 Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 ¡Hasta luego!")
            break

        if not user_input:
            continue

        # Comando: salir
        if user_input.lower() in ("salir", "exit", "quit"):
            print("\n👋 ¡Hasta luego! Cuídate mucho.")
            break

        # Comando: nueva conversación
        if user_input.lower() in ("nueva", "new", "reset"):
            session_id = str(uuid.uuid4())
            session = await session_service.create_session(
                app_name=config.APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )
            print(f"\n🔄 Nueva conversación iniciada (sesión: {session_id[:8]}...)\n")
            continue

        # Ejecutar turno
        print("\n🧠 Pensando...", end="", flush=True)
        try:
            response = await _run_turn(runner, user_id, session_id, user_input)
            print("\r" + " " * 20 + "\r", end="")  # Limpiar "Pensando..."

            if response:
                print()
                print("=" * 60)
                print("👨‍⚕️ DOCTOR AI:")
                print(response)
                print("=" * 60)
                print()
            else:
                print("⚠️  El agente no generó respuesta. Intenta reformular tu pregunta.\n")

        except Exception as e:
            print(f"\r\n❌ Error durante la consulta: {e}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Conversación interrumpida. ¡Hasta luego!")
