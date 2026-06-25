@echo off
title Professor Pardal
cd /d "%~dp0"

REM Encerra instância anterior na porta 8765
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8765 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

REM Usa o Python do venv se existir, senão cria
if not exist ".venv\Scripts\pythonw.exe" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python nao encontrado. Instale em python.org
        pause & exit /b
    )
    echo Criando ambiente virtual...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Instalando dependencias...
    pip install fastapi uvicorn[standard] python-multipart pdfplumber python-docx ^
        aiofiles httpx Pillow duckduckgo-search pydantic anthropic openai ^
        google-generativeai chromadb sentence-transformers pywebview pystray
)

REM Inicia com janela nativa (sem terminal)
.venv\Scripts\pythonw.exe janela.py
