"""
Definición del Agente Médico usando Google ADK.

Componentes:
- Cerebro: LLM (Azure OpenAI gpt-4o-mini por defecto, configurable)
- Skills: Herramientas del MCP de Graphiti (search_memory_facts, add_memory, etc.)
- Memoria: InMemorySessionService (gestión automática del historial de conversación)
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset, SseConnectionParams

from . import config


def _setup_azure_env():
    """Configura las variables de entorno que LiteLLM necesita para Azure OpenAI."""
    if config.AGENT_MODEL.startswith("azure/"):
        os.environ.setdefault("AZURE_API_KEY", config.AZURE_API_KEY)
        os.environ.setdefault("AZURE_API_BASE", config.AZURE_API_BASE)
        os.environ.setdefault("AZURE_API_VERSION", config.AZURE_API_VERSION)


def create_agent() -> LlmAgent:
    """
    Crea el agente médico con:
    - LLM como cerebro (configurable via AGENT_MODEL)
    - McpToolset conectado al servidor Graphiti via SSE
    """
    _setup_azure_env()

    # ── Cerebro: Modelo LLM ──────────────────────────────────────────────
    model = LiteLlm(model=config.AGENT_MODEL)

    # ── Skills: Herramientas del MCP de Graphiti ─────────────────────────
    mcp_tools = McpToolset(
        connection_params=SseConnectionParams(
            url=config.MCP_SERVER_URL,
        )
    )

    # ── Agente ───────────────────────────────────────────────────────────
    agent = LlmAgent(
        name=config.AGENT_NAME,
        model=model,
        instruction=config.AGENT_INSTRUCTION,
        tools=[mcp_tools],
    )

    return agent


def create_runner() -> tuple[Runner, InMemorySessionService]:
    """
    Crea el Runner completo con:
    - Agent (cerebro + skills)
    - SessionService (memoria de conversación)

    Returns:
        Tupla de (Runner, InMemorySessionService)
    """
    agent = create_agent()

    # ── Memoria: Servicio de sesiones en memoria ─────────────────────────
    session_service = InMemorySessionService()

    # ── Orquestador: Runner ──────────────────────────────────────────────
    runner = Runner(
        agent=agent,
        app_name=config.APP_NAME,
        session_service=session_service,
    )

    return runner, session_service
