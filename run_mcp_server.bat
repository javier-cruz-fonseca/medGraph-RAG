@echo off
setlocal

:: Cambiar al directorio del script
cd /d "%~dp0"

echo [1/3] Activando entorno virtual...
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: El entorno virtual no existe. Ejecuta primero SETUP.md
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"

echo [2/3] Instalando graphiti-mcp y dependencias (si no estan instaladas)...
pip install -r requirements.txt > nul 2>&1

echo [3/3] Iniciando Servidor MCP de Graphiti (con Gemini y Neo4j)...
echo NOTA: Puedes usar este script como comando en Claude Desktop o Cursor
echo.

:: Forzamos que cargue las variables de entorno de .env usando el comando de python
:: Ejecutamos el servidor usando el código que hemos copiado localmente
python -c "import os; from dotenv import load_dotenv; load_dotenv(); os.system('python -m mcp_server.main')"

endlocal
