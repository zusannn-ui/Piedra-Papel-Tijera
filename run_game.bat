@echo off
title Stone - Paper - Scissors AI Arena
cd /d "%~dp0"
echo.
echo  ====================================================
echo    Stone - Paper - Scissors  vs  Predictive AI
echo  ====================================================
echo.

:: Matar cualquier proceso que use el puerto 8000
echo [1/3] Liberando puerto 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Abrir el navegador despues de 3 segundos (en segundo plano)
echo [2/3] El navegador abrira en 3 segundos...
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

:: Iniciar el servidor en primer plano (muestra logs, Ctrl+C para detener)
echo [3/3] Iniciando servidor FastAPI...
echo.
echo  Presiona Ctrl+C para detener el servidor.
echo.
venv\Scripts\python.exe -m uvicorn main:app --port 8000 --reload

pause
