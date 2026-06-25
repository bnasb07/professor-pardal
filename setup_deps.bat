@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 exit /b 1
)

.venv\Scripts\pip.exe install --upgrade pip --quiet

.venv\Scripts\pip.exe install ^
    fastapi uvicorn[standard] python-multipart pdfplumber python-docx ^
    aiofiles httpx Pillow duckduckgo-search pydantic ^
    anthropic openai google-generativeai ^
    chromadb sentence-transformers ^
    pywebview pystray ^
    --quiet

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe gerar_icone.py >nul 2>&1
)
