# 🏥 Doctor AI — Agente Médico con Google ADK

Agente de IA médico construido con **Google Agent Development Kit (ADK)** que se conecta
al servidor MCP de Graphiti para consultar el Grafo de Conocimiento Médico almacenado en Neo4j.

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    Agente ADK                            │
│                                                          │
│  👤 Usuario ──► 🔄 Runner ──► 🧠 LLM (Azure OpenAI)    │
│                    │               │                     │
│                    ▼               ▼                     │
│              💾 Memoria      🔧 McpToolset              │
│         (SessionService)     (SSE → Graphiti)            │
│                                    │                     │
└────────────────────────────────────┼─────────────────────┘
                                     │
                              ┌──────▼──────┐
                              │ MCP Server  │
                              │  Graphiti   │
                              │ :8088/sse   │
                              └──────┬──────┘
                                     │
                              ┌──────▼──────┐
                              │   Neo4j     │
                              │ Knowledge   │
                              │   Graph     │
                              └─────────────┘
```

## Componentes

| Componente | Descripción | Tecnología |
|---|---|---|
| **Cerebro** | Razona, decide qué herramientas usar, genera respuestas | Azure OpenAI gpt-4o-mini (configurable) |
| **Skills** | Herramientas del MCP: buscar hechos, agregar memorias, etc. | `McpToolset` + SSE |
| **Memoria** | Historial de conversación entre turnos | `InMemorySessionService` |
| **Orquestador** | Coordina el flujo completo | `Runner` de ADK |

## Requisitos

1. Python 3.10+
2. El servidor MCP de Graphiti ejecutándose en `http://localhost:8088/sse`
3. Neo4j ejecutándose en `bolt://localhost:7687`

## Instalación

```bash
cd c:\Development\medGraph-RAG

# Crear entorno virtual (si no existe)
python -m venv agente\.venv

# Activar entorno virtual
agente\.venv\Scripts\activate

# Instalar dependencias
pip install -r agente\requirements.txt
```

## Configuración

Edita el archivo `agente/.env` con tus credenciales:

```env
# Modelo LLM (cerebro del agente)
AGENT_MODEL=azure/gpt-4o-mini

# Azure OpenAI
AZURE_API_KEY=tu_api_key
AZURE_API_BASE=https://tu-endpoint.openai.azure.com/
AZURE_API_VERSION=2025-03-01-preview

# MCP Server
MCP_SERVER_URL=http://localhost:8088/sse
```

### Cambiar el modelo LLM

El modelo se configura via variable de entorno `AGENT_MODEL`. Ejemplos:

| Modelo | Valor de `AGENT_MODEL` |
|---|---|
| Azure OpenAI GPT-4o-mini | `azure/gpt-4o-mini` |
| Azure OpenAI GPT-4o | `azure/gpt-4o` |
| Google Gemini Flash | `gemini-2.0-flash` |
| OpenAI GPT-4o | `openai/gpt-4o` |

## Uso

### 1. Arrancar el MCP Server (Terminal 1)

```powershell
cd c:\Development\medGraph-RAG\mcp-graphiti\graphiti\mcp_server
$env:OPENAI_API_KEY="dummy"
.\.venv\Scripts\python.exe main.py
```

### 2. Ejecutar el Agente (Terminal 2)

```powershell
cd c:\Development\medGraph-RAG
agente\.venv\Scripts\activate
python -m agente.main
```

### Comandos del CLI

| Comando | Acción |
|---|---|
| Cualquier texto | Envía la pregunta al agente |
| `salir` / `exit` | Termina la conversación |
| `nueva` / `new` | Inicia nueva conversación (resetea memoria) |

## Ejemplo de uso

```
👤 Tú: El paciente Juan García tiene diabetes tipo 2 y toma Metformina 850mg
🧠 Pensando...

============================================================
👨‍⚕️ DOCTOR AI:
He registrado la información del paciente Juan García en el grafo de conocimiento:
- Diagnóstico: Diabetes Tipo 2
- Medicamento: Metformina 850mg
¿Hay algo más que quieras agregar a su historial?
============================================================

👤 Tú: ¿Qué medicamentos toma Juan?
🧠 Pensando...

============================================================
👨‍⚕️ DOCTOR AI:
Según el historial en el grafo de conocimiento, Juan García actualmente
toma Metformina 850mg como tratamiento para su Diabetes Tipo 2.
============================================================
```
