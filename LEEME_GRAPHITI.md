# Configuración y Uso de Graphiti MCP Server en medGraph-RAG

Este proyecto cuenta con un servidor MCP de Graphiti configurado específicamente para interactuar mediante **Azure OpenAI** (`gpt-4o-mini` y `text-embedding-3-large`) con una base de datos local **Neo4j**, extrayendo relaciones médicas de texto plano de manera autónoma.

A continuación, los pasos para ejecutar la pila de tecnología y realizar tus consultas RAG.

---

## 1. Arrancar el Servidor MCP

El servidor *siempre* se debe ejecutar desde el subdirectorio de Graphiti para que detecte correctamente su entorno virtual (`.venv`) y los archivos de configuración asociados.

Abre una **Terminal 1** y ejecuta:

```powershell
# Moverse a la carpeta base del servidor
cd c:\Development\medGraph-RAG\mcp-graphiti\graphiti\mcp_server

# Configurar el bypass de la API key global
# (Previene que la librería base intente validar contra OpenAI estándar)
$env:OPENAI_API_KEY="dummy"

# Lanzar el servidor expuesto en http://localhost:8088/sse
.\.venv\Scripts\python.exe main.py
```

> **Importante:** Debes dejar esta terminal ejecutándose ininterrumpidamente. Aquí podrás ver cómo se encolan los trabajos y cómo Azure OpenAI va parseando los nodos.

---

## 2. Realizar Pruebas Locales (Test de Conectividad)

Mientras el servidor se ejecuta, abre una **Terminal 2**. Puedes permanecer en la raíz del proyecto para este y todos los demás comandos:

```powershell
cd c:\Development\medGraph-RAG
```

Para comprobar que el protocolo SSE permite iniciar sesión y que Neo4j responde de manera correcta, usa el test de protocolo:

```powershell
uv run --with mcp .\pruebas_locales\test_mcp.py
```

Deberás ver que se exponen 9 herramientas (ej: `add_memory`, `search_nodes`, etc.) y el `get_status` retorna `"ok"`.

---

## 3. Demostración RAG (Extracción y Respuesta)

He creado un script asíncrono (`test_medicina.py`) que imita a la perfección el funcionamiento de un agente inteligente utilizando el Knowledge Graph de la siguiente manera:

1. **Agrega Memoria**: Inyecta una ficha de paciente (con patologías y medicamentos) hacia Azure OpenAI.
2. **Espera**: Pausa por unos segundos para dar tiempo a que Graphiti asimile semánticamente las relaciones y construya el grafo en Neo4j.
3. **Hace Query**: Busca un síntoma en particular y recaba los "Facts" desde Neo4j.
4. **Sintetiza la respuesta**: Envía los fragmentos a un modelo de texto de Azure OpenAI para generar un diálogo natural estilo médico.

Para ejecutar este RAG completo en tu consola de pruebas, lanza:

```powershell
uv run --with mcp --with openai .\pruebas_locales\test_medicina.py
```

---

## Notas y Cambios Realizados en el Sistema

* **Configuración del YAML**: Modificamos el fichero `c:\Development\medGraph-RAG\mcp-graphiti\graphiti\mcp_server\config\config.yaml` definiendo explicitamente la conexión a `azure_openai`, limitando el protocolo web de vuelta a su clásico `sse` con el puerto `8088`, lo cual permite que aplicaciones base de python (e integraciones externas como Claude u otros agentes) interactúen sin formato HTTP complejo.
* **Overvride del Cliente Core**: Al existir un bug en la propia librería `graphiti_core` oficial con Azure OpenAI (omitieron devolver la cuenta de tokens), se introdujo en el código del servidor (`azure_openai_client.py`) un parche compatible para subsanarlo. 
* Si se destruye/reinstala el entorno virtual `.venv` de Graphiti, se debe volver a aplicar el parche del archivo de cliente de Azure.
