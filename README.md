# MedGraph-RAG: Medical Knowledge Graph with Local RAG

Este proyecto utiliza **Graphiti (MCP)** sobre **Neo4j** para crear una memoria dinámica de grafos de conocimiento médico, permitiendo consultas semánticas y razonamiento RAG (Retrieval-Augmented Generation) mediante modelos locales.

## Arquitectura

- **Base de Datos**: Neo4j (Grafos y Vectores).
- **IA Local**: LM Studio (sirviendo modelos compatibles con la API de OpenAI).
- **Framework**: Graphiti Core + MCP Server.
- **Orquestación**: Antigravity (AI Agent).

## Ajustes para Modelos Locales (LM Studio)

Para que el servidor MCP de Graphiti funcione correctamente con modelos locales (evitando llamadas a la API oficial de OpenAI), hemos realizado varios ajustes críticos en el código y la configuración:

### 1. Configuración del Servidor (`mcp-graphiti/graphiti/mcp_server/config/config.yaml`)

Se debe usar el proveedor `openai` incluso para modelos locales, especificando la URL de LM Studio:

```yaml
llm:
  provider: "openai"
  model: "gpt-oss:120b" # Nombre del modelo cargado en LM Studio
  providers:
    openai:
      api_url: "http://127.0.0.1:1234/v1" # URL local (NO usar api_base)
      api_key: "dummy" # Requerido por la librería aunque no se valide localmente

embedder:
  provider: "openai" # Usar el endpoint de embeddings de LM Studio
  model: "text-embedding-all-minilm-l6-v2-embedding"
  dimensions: 384
  providers:
    openai:
      api_url: "http://127.0.0.1:1234/v1"
      api_key: "dummy"
```

> [!IMPORTANT]
> El campo correcto en el esquema de configuración es `api_url`. El uso de `api_base` causará que el parámetro sea ignorado.

### 2. Correcciones en el Código Fuente

- **Soporte de `base_url` en LLM**: Se modificó `src/services/factories.py` para asegurar que el parámetro `api_url` de la configuración se pase correctamente como `base_url` al inicializar los clientes OpenAI. Antiguamente se omitía, causando que intentara conectar con los servidores reales de OpenAI.
- **Reranker Local**: Se implementó una `RerankerFactory` y se actualizó `src/graphiti_mcp_server.py` para inicializar y pasar un reranker local. Antes, Graphiti intentaba crear un reranker por defecto que fallaba por falta de clave API.
- **Detección de Embedder**: Se cambió el proveedor de embeddings de `sentence_transformers` (no soportado por la librería core en este contexto) a `openai` apuntando a la API local de LM Studio.

## Requisitos de Ejecución

1. **Neo4j**: Debe estar corriendo en el puerto `7687` (Bolt).
   - *Nota*: Si Docker da error de "port already allocated", asegúrate de cerrar Neo4j Desktop o detener contenedores huérfanos.
2. **LM Studio**:
   - Servidor HTTP local activado en el puerto `1234`.
   - Modelo cargado y configurado para aceptar peticiones externas.
3. **Servidor MCP**:
   ```powershell
   cd mcp-graphiti\graphiti\mcp_server
   uv run main.py --database-provider neo4j
   ```

## Notas Técnicas
La librería `graphiti-core` requiere que todos los clientes (LLM, Embedder, Reranker) estén explícitamente configurados al trabajar offline o con modelos locales para evitar que la inicialización por defecto intente validar credenciales inexistentes de OpenAI.
