# medGraph-RAG — Setup

## 1. Crear entorno virtual

```powershell
cd c:\Development\medGraph-RAG
python -m venv .venv
```

## 2. Activar entorno virtual

```powershell
.venv\Scripts\activate
```

## 3. Instalar dependencias

```powershell
pip install -r requirements.txt
```

## 4. Configurar credenciales

Copia el fichero de ejemplo y edítalo con tus credenciales:

```powershell
copy .env.example .env
```

Edita `.env` con:
- **GEMINI_API_KEY**: tu API key de Google AI Studio ([https://aistudio.google.com/apikey](https://aistudio.google.com/apikey))
- **NEO4J_PASSWORD**: la contraseña de tu base de datos Neo4j

## 5. Neo4j

Asegúrate de tener Neo4j corriendo en `bolt://localhost:7687`. Puedes usar:
- [Neo4j Desktop](https://neo4j.com/download/)
- Docker: `docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j`

## 6. Ejecutar

```powershell
# Paso 1: Convertir Excel → YAML
python csv_to_yaml.py

# Paso 2: Ingestar YAML → Neo4j (con Graphiti + Gemini)
python ingest_graphiti.py
```

## 7. Verificar en Neo4j

Abre [http://localhost:7474](http://localhost:7474) y ejecuta:

```cypher
MATCH (n) RETURN n LIMIT 100
```

## 8. Consultar con IA (MCP Server)

Hemos instalado **Graphiti MCP Server** para que agentes de IA (como Claude Desktop o Cursor) puedan consultar tu grafo.

### Opcion A: Lanzar el servidor manualmente (para Cursor/Windsurf)
Ejecuta el script incluido:
```powershell
.\run_mcp_server.bat
```
En Cursor, añade un nuevo servidor MCP de tipo **"command"** y pon la ruta absoluta a ese script `.bat`.

### Opcion B: Claude Desktop
Copia el contenido del archivo `claude_desktop_config_example.json` en la configuración de Claude Desktop (suele estar en `%APPDATA%\Claude\claude_desktop_config.json`). Claude arrancará el servidor automáticamente en segundo plano al iniciar.
