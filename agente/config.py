"""
Configuración centralizada del Agente Médico.

Todas las variables son configurables via variables de entorno.
"""

import os

# ─── Modelo LLM (Cerebro) ────────────────────────────────────────────────────
# Formato LiteLLM: "azure/<deployment-name>" para Azure OpenAI
# Ejemplos: "azure/gpt-4o-mini", "gemini-2.0-flash", "openai/gpt-4o"
AGENT_MODEL = os.getenv("AGENT_MODEL", "azure/gpt-4o-mini")

# ─── Azure OpenAI (cuando AGENT_MODEL usa prefijo "azure/") ──────────────────
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "301bf807e142479888927616f902292d")
AZURE_API_BASE = os.getenv(
    "AZURE_API_BASE",
    "https://cor-ai-gnplatform-dev-openai-sweden.openai.azure.com/",
)
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2025-03-01-preview")

# ─── Servidor MCP de Graphiti ─────────────────────────────────────────────────
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8088/sse")

# ─── Metadatos del Agente ─────────────────────────────────────────────────────
APP_NAME = "medgraph_agent"
AGENT_NAME = "doctor_ai"

# ─── System Prompt (Instrucciones del Agente) ────────────────────────────────
AGENT_INSTRUCTION = """Eres un asistente médico experto llamado Doctor AI. 
Tu rol es ayudar a profesionales de la salud y pacientes respondiendo preguntas médicas 
de forma precisa, clara y empática.

## Capacidades
Tienes acceso a un Grafo de Conocimiento Médico a través de herramientas MCP. 
SIEMPRE que el usuario haga una pregunta médica o sobre un paciente:

1. **Busca primero** en la memoria del grafo usando `search_memory_facts` para encontrar 
   hechos relevantes del historial.
2. **Busca nodos** con `search_nodes` si necesitas información sobre entidades específicas 
   (medicamentos, diagnósticos, pacientes).
3. **Agrega memorias** con `add_memory` cuando el usuario proporcione nueva información 
   clínica relevante que deba persistir en el grafo.

## Reglas
- Si encuentras información en el grafo, úsala como base principal de tu respuesta.
- Si NO encuentras información relevante, responde con tu conocimiento médico general, 
  pero aclara que no tienes datos específicos del historial del paciente.
- Responde siempre en español.
- Sé preciso y profesional pero accesible.
- Si el usuario proporciona datos clínicos (historial, diagnósticos, medicamentos), 
  ofrécete a guardarlos en la memoria del grafo.
- NUNCA inventes datos de pacientes que no estén en el grafo.
"""
