# medGraph-RAG

Sistema de ingestión de datos médicos mediante grafos de conocimiento usando Graphiti y Neo4j. Soporta tanto LLMs locales (LM Studio) como Azure OpenAI para procesamiento enterprise-grade.

## 🚀 Características

- **Ingestión automatizada** de datos médicos desde archivos Excel
- **Grafo de conocimiento** con Graphiti + Neo4j
- **Multi-LLM**: Soporte para Azure OpenAI y LM Studio
- **Embeddings flexibles**: Gemini o Azure OpenAI
- **MCP Server** para consulta con agentes de IA
- **Retrocompatible** - funciona con configuraciones existentes

## 📋 Arquitectura

```
Excel/CSV → YAML → Graphiti → Neo4j → MCP Server → IA Agentes
```

1. **csv_to_yaml.py**: Convierte datos médicos de Excel a YAML estructurado
2. **ingest_graphiti.py**: Ingesta YAML en grafo de conocimiento usando LLM
3. **Graphiti MCP Server**: Expone el grafo para consulta por agentes IA

## 🛠️ Instalación y Configuración

### 1. Crear entorno virtual

```bash
cd /Users/8379/Development/tfm-javi/medGraph-RAG
python -m venv .venv
```

### 2. Activar entorno virtual

**Windows:**
```powershell
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar credenciales

Copia el fichero de ejemplo y edítalo con tus credenciales:

**Windows:**
```powershell
copy .env.example .env
```

**macOS/Linux:**
```bash
cp .env.example .env
```

Edita `.env` con una de estas opciones:

#### Opción A: Azure OpenAI (Recomendado para producción)
```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=tu_azure_api_key
AZURE_OPENAI_ENDPOINT=https://tu-recurso.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=tu-deployment-name
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=tu-embedding-deployment
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Neo4j (siempre requerido)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=tu_password_neo4j
```

#### Opción B: LM Studio + Gemini (Configuración original)
```env
# Google Gemini
GEMINI_API_KEY=tu_api_key_de_gemini  # Obtén en: https://aistudio.google.com/apikey

# LM Studio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=google/gemma-3-4b

# Neo4j (siempre requerido)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=tu_password_neo4j
```

**Nota**: El sistema detectará automáticamente qué configuración usar. Si configuras Azure OpenAI, usará Azure para LLM y embeddings. Si no, usará LM Studio + Gemini.

### 4. Neo4j

Asegúrate de tener Neo4j corriendo en `bolt://localhost:7687`. Puedes usar:

- **Neo4j Desktop**: [https://neo4j.com/download/](https://neo4j.com/download/)
- **Docker**: 
  ```bash
  docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j
  ```

## 🚀 Ejecución

```bash
# Paso 1: Convertir Excel → YAML
python csv_to_yaml.py

# Paso 2: Ingestar YAML → Neo4j (con Graphiti + Azure/LM Studio + Gemini)
python ingest_graphiti.py
```

El script detectará automáticamente qué configuración usar según las variables de entorno configuradas.

## 🔍 Verificación

Abre [http://localhost:7474](http://localhost:7474) (Neo4j Browser) y ejecuta:

```cypher
MATCH (n) RETURN n LIMIT 100
```

## 🤖 Consulta con IA (MCP Server)

Hemos instalado **Graphiti MCP Server** para que agentes de IA (como Claude Desktop o Cursor) puedan consultar tu grafo.

### Opción A: Lanzar servidor manualmente (para Cursor/Windsurf)
**Windows:**
```powershell
.\run_mcp_server.bat
```

**macOS/Linux:**
```bash
./run_mcp_server.bat
```

En Cursor, añade un nuevo servidor MCP de tipo **"command"** y pon la ruta absoluta a ese script `.bat`.

### Opción B: Claude Desktop
Copia el contenido del archivo `claude_desktop_config_example.json` en la configuración de Claude Desktop:

**Windows:**
- Ruta: `%APPDATA%\Claude\claude_desktop_config.json`

**macOS:**
- Ruta: `~/Library/Application Support/Claude/claude_desktop_config.json`

Claude arrancará el servidor automáticamente en segundo plano al iniciar.

## 📁 Estructura del Proyecto

```
medGraph-RAG/
├── README.md                    # Este archivo
├── SETUP.md                     # Guía de setup detallada
├── requirements.txt             # Dependencias Python
├── .env.example                 # Plantilla de variables de entorno
├── csv_to_yaml.py              # Conversión Excel → YAML
├── ingest_graphiti.py          # Ingestión YAML → Neo4j
├── run_mcp_server.bat          # Script para iniciar MCP server
├── claude_desktop_config_example.json  # Config ejemplo Claude
├── data/                        # Directorio de datos
│   ├── medicines_yaml/          # YAML procesados para ingestar
│   └── medicines_yaml_processed/  # YAML ya procesados
└── docker-image-neo/            # Configuración Docker Neo4j
```

## 🔧 Configuración Avanzada

### Variables de Entorno Disponibles

| Variable | Descripción | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | API key de Google AI Studio | - |
| `AZURE_OPENAI_API_KEY` | API key de Azure OpenAI | - |
| `AZURE_OPENAI_ENDPOINT` | Endpoint de recurso Azure | - |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment LLM | - |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Deployment embeddings | - |
| `AZURE_OPENAI_API_VERSION` | Versión API Azure | `2024-02-15-preview` |
| `LMSTUDIO_BASE_URL` | URL LM Studio | `http://localhost:1234/v1` |
| `LMSTUDIO_MODEL` | Modelo LM Studio | `google/gemma-3-4b` |
| `NEO4J_URI` | URI Neo4j | `bolt://localhost:7687` |
| `NEO4J_USER` | Usuario Neo4j | `neo4j` |
| `NEO4J_PASSWORD` | Contraseña Neo4j | - |
| `GEMINI_EMBEDDING_MODEL` | Modelo embeddings Gemini | `gemini-embedding-001` |

### Prioridad de Configuración

1. **Azure OpenAI completo** → Usa Azure para todo (LLM + embeddings)
2. **Azure LLM + Gemini embeddings** → Mix si solo hay deployment LLM
3. **LM Studio + Gemini** → Configuración original

## 🐛 Troubleshooting

### Problemas Comunes

**Error: "No se encontraron archivos .yaml"**
```bash
# Asegúrate de ejecutar primero:
python csv_to_yaml.py
```

**Error: "GEMINI_API_KEY no está configurada"**
```bash
# Configura tu API key en .env o usa Azure OpenAI
# Obtén API key en: https://aistudio.google.com/apikey
```

**Error de conexión Neo4j**
```bash
# Verifica que Neo4j esté corriendo:
docker ps | grep neo4j
# O inicia Neo4j Desktop
```

**Rate limits en Gemini**
- El código incluye reintentos automáticos con backoff
- Considera Azure OpenAI para mayor throughput

## 🤝 Contribución

1. Fork del repositorio
2. Crear feature branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -am 'Añadir nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Pull Request

## 📄 Licencia

Este proyecto está bajo licencia MIT - ver archivo LICENSE para detalles.

## 🙏 Agradecimientos

- **Graphiti**: Framework de grafos de conocimiento
- **Neo4j**: Base de datos de grafos
- **Azure OpenAI**: LLMs enterprise-grade
- **Google Gemini**: Embeddings y LLMs
- **LM Studio**: LLMs locales

---

**medGraph-RAG** - Transformando datos médicos en conocimiento consultable mediante grafos.
