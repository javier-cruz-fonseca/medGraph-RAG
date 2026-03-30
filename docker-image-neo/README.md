# Base de Datos Neo4j - medGraph-RAG

Credenciales imagen neo4j: `neo4j` / `neo4jneo4j`

## Cómo restaurar la base de datos en un nuevo ordenador

El archivo `neo4j.zip` contiene todos los datos de la base de datos de grafos ya procesada. Para levantarla en otro equipo con la misma información, sigue estos pasos:

### 1. Requisitos previos
- Tener [Docker](https://www.docker.com/products/docker-desktop/) instalado y en ejecución en el nuevo equipo.

### 2. Descomprimir los datos
1. Copia el archivo `neo4j.zip` al nuevo ordenador.
2. Descomprímelo en una ubicación conocida. Al descomprimirlo, obtendrás una carpeta llamada `neo4j` que dentro contiene la carpeta `data`.

### 3. Levantar el contenedor
Abre una terminal y ejecuta el siguiente comando, asegurándote de reemplazar `/ruta/absoluta/a/tu/carpeta/neo4j/data` por la ruta real donde has descomprimido la carpeta.

**En Mac / Linux:**
```bash
docker run -d \
  --name neo4j-medgraph \
  -p 7474:7474 \
  -p 7687:7687 \
  -v /ruta/absoluta/a/tu/carpeta/neo4j/data:/data \
  -e NEO4J_AUTH=neo4j/neo4jneo4j \
  neo4j:2026.02.3
```
*(Tip: Si abres la terminal justo donde está la carpeta `neo4j`, puedes usar `-v $(pwd)/neo4j/data:/data`)*

**En Windows (Command Prompt / PowerShell):**
```powershell
docker run -d ^
  --name neo4j-medgraph ^
  -p 7474:7474 ^
  -p 7687:7687 ^
  -v C:\ruta\absoluta\a\tu\carpeta\neo4j\data:/data ^
  -e NEO4J_AUTH=neo4j/neo4jneo4j ^
  neo4j:2026.02.3
```

### 4. Verificar la instalación
1. Abre tu navegador y accede a: [http://localhost:7474](http://localhost:7474)
2. Inicia sesión con el usuario `neo4j` y la contraseña `neo4jneo4j`.
3. Todos tus nodos y relaciones estarán disponibles y listos para consultarse.

---

## Método alternativo: Usando un dump de la base de datos

Si en lugar de compartir la carpeta completa prefieres usar un archivo `.dump` de Neo4j, sigue estos pasos:

### 1. Generar el dump (en el ordenador original)
Para crear el dump, el contenedor debe estar detenido o la base de datos pausada. Ejecuta:
```bash
# 1. Detener el contenedor actual
docker stop <nombre_o_id_del_contenedor>

# 2. Generar el dump usando un contenedor temporal
docker run --rm -v /ruta/absoluta/a/tu/carpeta/neo4j/data:/data neo4j:2026.02.3 neo4j-admin database dump neo4j --to-path=/data

# 3. Volver a arrancar el contenedor
docker start <nombre_o_id_del_contenedor>
```
Esto creará un archivo `neo4j.dump` dentro de tu carpeta `data`.

### 2. Cargar el dump (en el nuevo ordenador)
Debes tener el archivo `neo4j.dump` en una carpeta del ordenador (ej: `C:\ruta\nueva\neo4j\data`).

```bash
# 1. Cargar el dump en la nueva carpeta usando un contenedor temporal
docker run --rm -v C:\ruta\nueva\neo4j\data:/data neo4j:2026.02.3 neo4j-admin database load neo4j --from-path=/data/neo4j.dump --overwrite-destination

# 2. Levantar el contenedor final apuntando a esa carpeta
docker run -d \
  --name neo4j-medgraph \
  -p 7474:7474 \
  -p 7687:7687 \
  -v C:\ruta\nueva\neo4j\data:/data \
  -e NEO4J_AUTH=neo4j/neo4jneo4j \
  neo4j:2026.02.3
```
