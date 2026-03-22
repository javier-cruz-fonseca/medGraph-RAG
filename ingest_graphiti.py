"""
ingest_graphiti.py
==================
Lee los archivos YAML generados por csv_to_yaml.py e ingesta cada uno
como un episodio en Graphiti, que almacena el grafo de conocimiento en Neo4j.

Usa LM Studio (LLM local) y Gemini (embeddings).

Prerrequisitos:
    1. Neo4j corriendo (local o remoto)
    2. Fichero .env configurado (ver .env.example)
    3. pip install -r requirements.txt

Uso:
    python ingest_graphiti.py
"""

import asyncio
import glob
import os
import shutil
import sys

import yaml
from dotenv import load_dotenv

# ── Cargar variables de entorno desde .env ─────────────────────────────────────
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
GEMINI_EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

# LM Studio (LLM local)
LMSTUDIO_BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.environ.get("LMSTUDIO_MODEL", "google/gemma-3-4b")

# Directorio con los YAML de medicamentos (entrada)
INGEST_INPUT_DIR = os.environ.get("INGEST_INPUT_DIR", os.path.join("data", "medicines_yaml"))
# Directorio donde se mueven los ficheros ya procesados
INGEST_PROCESSED_DIR = os.environ.get("INGEST_PROCESSED_DIR", os.path.join("data", "medicines_yaml_processed"))

# Límite de ficheros a procesar (para pruebas). Poner None para procesar todos.
LIMIT = None


# ── Funciones auxiliares ───────────────────────────────────────────────────────

def yaml_to_text(data: dict) -> str:
    """
    Convierte un diccionario YAML de un medicamento a texto legible
    para que Graphiti pueda extraer entidades y relaciones.
    """
    lines = []

    name = data.get("name", "Desconocido")
    lines.append(f"Medicamento: {name}")
    lines.append("")

    # Información básica
    basic = data.get("basic_information", {})
    if basic:
        lines.append("== Información Básica ==")
        for key, value in basic.items():
            if value:
                label = key.replace("_", " ").title()
                lines.append(f"  {label}: {value}")
        lines.append("")

    # Información terapéutica
    therapeutic = data.get("therapeutic_information", {})
    if therapeutic:
        lines.append("== Información Terapéutica ==")
        for key, value in therapeutic.items():
            if value:
                label = key.replace("_", " ").title()
                lines.append(f"  {label}: {value}")
        lines.append("")

    # Clasificación regulatoria
    regulatory = data.get("regulatory_classification", {})
    if regulatory:
        lines.append("== Clasificación Regulatoria ==")
        for key, value in regulatory.items():
            if value:
                label = key.replace("_", " ").title()
                lines.append(f"  {label}: {value}")
        lines.append("")

    # Detalles de autorización
    auth = data.get("authorization_details", {})
    if auth:
        lines.append("== Detalles de Autorización ==")
        for key, value in auth.items():
            if value:
                label = key.replace("_", " ").title()
                lines.append(f"  {label}: {value}")
        lines.append("")

    # Metadatos
    meta = data.get("metadata", {})
    if meta:
        lines.append("== Metadatos ==")
        for key, value in meta.items():
            if value:
                label = key.replace("_", " ").title()
                lines.append(f"  {label}: {value}")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    # ── Validar credenciales ──
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY no está configurada (necesaria para embeddings).")
        print("   Configúrala en el fichero .env (ver .env.example)")
        sys.exit(1)

    if not NEO4J_PASSWORD:
        print("[ERROR] NEO4J_PASSWORD no está configurada.")
        print("   Configúrala en el fichero .env (ver .env.example)")
        sys.exit(1)

    # ── Importar Graphiti y clientes ──
    try:
        from graphiti_core import Graphiti
        from graphiti_core.nodes import EpisodeType
    except ImportError:
        print("[ERROR] graphiti-core no está instalado.")
        print("   Ejecuta: pip install -r requirements.txt")
        sys.exit(1)

    try:
        from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
        from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    except ImportError:
        print("[ERROR] Dependencias no instaladas.")
        print("   Ejecuta: pip install graphiti-core[google-genai]")
        sys.exit(1)

    # ── Crear carpeta de procesados si no existe ──
    os.makedirs(INGEST_PROCESSED_DIR, exist_ok=True)

    # ── Recoger archivos YAML ──
    yaml_files = sorted(glob.glob(os.path.join(INGEST_INPUT_DIR, "*.yaml")))
    if not yaml_files:
        print(f"[ERROR] No se encontraron archivos .yaml en '{INGEST_INPUT_DIR}/'")
        print("   Ejecuta primero: python csv_to_yaml.py")
        sys.exit(1)

    # Aplicar límite si está configurado
    if LIMIT is not None:
        yaml_files = yaml_files[:LIMIT]

    print(f"[INFO] Encontrados {len(yaml_files)} archivos YAML para ingestar.")
    print(f"[INFO] Conectando a Neo4j: {NEO4J_URI}")
    print(f"[INFO] Usando LM Studio LLM: {LMSTUDIO_MODEL} en {LMSTUDIO_BASE_URL}")
    print(f"[INFO] Usando Gemini embeddings: {GEMINI_EMBEDDING_MODEL}")

    # ── Configurar LLM con LM Studio (API OpenAI-compatible) ──
    llm_config = LLMConfig(
        api_key="lm-studio",  # LM Studio no requiere API key real, pero el campo es obligatorio
        model=LMSTUDIO_MODEL,
        small_model=LMSTUDIO_MODEL,
        base_url=LMSTUDIO_BASE_URL,
    )
    llm_client = OpenAIGenericClient(config=llm_config)

    # ── Configurar embeddings con Gemini (free tier: 1K RPD) ──
    embed_config = GeminiEmbedderConfig(
        api_key=GEMINI_API_KEY,
        embedding_model=GEMINI_EMBEDDING_MODEL,
    )
    embedder = GeminiEmbedder(config=embed_config)

    # ── Configurar cross-encoder/reranker con LM Studio ──
    reranker_config = LLMConfig(
        api_key="lm-studio",
        model=LMSTUDIO_MODEL,
        base_url=LMSTUDIO_BASE_URL,
    )
    cross_encoder = OpenAIRerankerClient(config=reranker_config)

    # ── Inicializar Graphiti ──
    graphiti = Graphiti(
        NEO4J_URI,
        NEO4J_USER,
        NEO4J_PASSWORD,
        llm_client=llm_client,
        embedder=embedder,
        cross_encoder=cross_encoder,
    )

    try:
        # Inicializar el grafo (crea índices y constraints en Neo4j)
        await graphiti.build_indices_and_constraints()
        print("[OK] Índices de Neo4j inicializados.")

        # ── Ingestar cada archivo como un episodio ──
        success = 0
        errors = 0

        import time
        from datetime import datetime

        # Delay entre episodios (LM Studio local no tiene rate limits, pero
        # el embedder de Gemini sí: reducido a 2s para dar margen)
        DELAY_BETWEEN_EPISODES = 2  # segundos
        MAX_RETRIES = 5

        for i, yaml_path in enumerate(yaml_files, 1):
            filename = os.path.basename(yaml_path)

            try:
                # Leer y parsear YAML
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not data:
                    print(f"   [WARN] Archivo vacío: {filename}")
                    errors += 1
                    continue

                medicine_name = data.get("name", "Desconocido")

                # Convertir YAML a texto legible para Graphiti
                content = yaml_to_text(data)

                print(f"   [INFO] ({i}/{len(yaml_files)}) Ingestando: {medicine_name}")

                # Reintentar con backoff si hay rate limiting
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        await graphiti.add_episode(
                            name=f"Medicine: {medicine_name}",
                            episode_body=content,
                            source=EpisodeType.text,
                            source_description=f"EMA Medicine Report - {medicine_name}",
                            reference_time=datetime.now(),
                        )
                        break  # Éxito, salir del bucle de reintentos
                    except Exception as retry_err:
                        if "Rate limit" in str(retry_err) and attempt < MAX_RETRIES:
                            wait_time = DELAY_BETWEEN_EPISODES * attempt
                            print(f"   [RETRY] Rate limit alcanzado. Esperando {wait_time}s (intento {attempt}/{MAX_RETRIES})...")
                            time.sleep(wait_time)
                        else:
                            raise  # Re-lanzar si no es rate limit o ya agotamos reintentos

                success += 1

                # Mover fichero procesado a la carpeta de procesados
                dest_path = os.path.join(INGEST_PROCESSED_DIR, filename)
                shutil.move(yaml_path, dest_path)
                print(f"   [MOVED] {filename} -> {INGEST_PROCESSED_DIR}/")

                if i % 10 == 0 or i == len(yaml_files):
                    print(f"   [PROGRESS] {i}/{len(yaml_files)} ({success} ok, {errors} errores)")

                # Pequeña pausa para dar margen al embedder de Gemini
                if i < len(yaml_files):
                    time.sleep(DELAY_BETWEEN_EPISODES)

            except Exception as e:
                errors += 1
                print(f"   [WARN] Error en '{filename}': {e}")

        print(f"\n[DONE] Ingesta completada:")
        print(f"   OK:     {success}")
        print(f"   Errors: {errors}")
        print(f"\n[INFO] Abre Neo4j Browser y ejecuta:")
        print(f"   MATCH (n) RETURN n LIMIT 100")

    finally:
        await graphiti.close()


if __name__ == "__main__":
    asyncio.run(main())
