@echo off
title Instalando Professor Pardal...
color 0A
cls
echo.
echo  =========================================
echo   Professor Pardal - Instalador
echo  =========================================
echo.

cd /d "%~dp0"
set APP_DIR=%~dp0
set APP_DIR=%APP_DIR:~0,-1%

REM ── Verifica Python ──────────────────────────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo ERRO: Python nao encontrado.
        echo Instale em: https://python.org/downloads
        echo Marque "Add Python to PATH" durante a instalacao.
        pause & exit /b
    )
    echo Criando ambiente virtual...
    python -m venv .venv
    if errorlevel 1 ( echo ERRO ao criar venv. & pause & exit /b )
)
set PYTHON="%APP_DIR%\.venv\Scripts\python.exe"
set PIP="%APP_DIR%\.venv\Scripts\pip.exe"

REM ── Instala dependencias se necessario ───────────────────────────────────
%PYTHON% -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias - aguarde...
    %PIP% install fastapi uvicorn[standard] python-multipart pdfplumber python-docx ^
        aiofiles httpx Pillow duckduckgo-search pydantic anthropic openai ^
        google-generativeai chromadb sentence-transformers "PySide6>=6.7.0"
    if errorlevel 1 ( echo ERRO na instalacao. & pause & exit /b )
)

REM ── Gera icone ───────────────────────────────────────────────────────────
if not exist "%APP_DIR%\icon.ico" (
    echo Gerando icone...
    %PYTHON% "%APP_DIR%\gerar_icone.py"
)
set ICON=%APP_DIR%\icon.ico

REM ── Cria atalho Desktop ──────────────────────────────────────────────────
set DESKTOP=%USERPROFILE%\Desktop
echo Criando atalho na area de trabalho...

> "%TEMP%\pardal_atalho.vbs" echo Set WS = CreateObject("WScript.Shell")
>> "%TEMP%\pardal_atalho.vbs" echo Set SC = WS.CreateShortcut("%DESKTOP%\Professor Pardal.lnk")
>> "%TEMP%\pardal_atalho.vbs" echo SC.TargetPath = "%APP_DIR%\ProfessorPardal.exe"
>> "%TEMP%\pardal_atalho.vbs" echo SC.WorkingDirectory = "%APP_DIR%"
>> "%TEMP%\pardal_atalho.vbs" echo SC.IconLocation = "%ICON%"
>> "%TEMP%\pardal_atalho.vbs" echo SC.Description = "Professor Pardal - Assistente de Estudos"
>> "%TEMP%\pardal_atalho.vbs" echo SC.WindowStyle = 1
>> "%TEMP%\pardal_atalho.vbs" echo SC.Save
cscript //nologo "%TEMP%\pardal_atalho.vbs"

REM ── Cria atalho Menu Iniciar ─────────────────────────────────────────────
set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
if not exist "%STARTMENU%\Professor Pardal" mkdir "%STARTMENU%\Professor Pardal"

> "%TEMP%\pardal_menu.vbs" echo Set WS = CreateObject("WScript.Shell")
>> "%TEMP%\pardal_menu.vbs" echo Set SC = WS.CreateShortcut("%STARTMENU%\Professor Pardal\Professor Pardal.lnk")
>> "%TEMP%\pardal_menu.vbs" echo SC.TargetPath = "%APP_DIR%\ProfessorPardal.exe"
>> "%TEMP%\pardal_menu.vbs" echo SC.WorkingDirectory = "%APP_DIR%"
>> "%TEMP%\pardal_menu.vbs" echo SC.IconLocation = "%ICON%"
>> "%TEMP%\pardal_menu.vbs" echo SC.Description = "Professor Pardal - Assistente de Estudos"
>> "%TEMP%\pardal_menu.vbs" echo SC.WindowStyle = 1
>> "%TEMP%\pardal_menu.vbs" echo SC.Save
cscript //nologo "%TEMP%\pardal_menu.vbs"

REM ── Cria desinstalador no menu ───────────────────────────────────────────
> "%STARTMENU%\Professor Pardal\Desinstalar.bat" echo @echo off
>> "%STARTMENU%\Professor Pardal\Desinstalar.bat" echo if exist "%DESKTOP%\Professor Pardal.lnk" del "%DESKTOP%\Professor Pardal.lnk"
>> "%STARTMENU%\Professor Pardal\Desinstalar.bat" echo rmdir /s /q "%STARTMENU%\Professor Pardal"
>> "%STARTMENU%\Professor Pardal\Desinstalar.bat" echo echo Professor Pardal desinstalado dos atalhos.
>> "%STARTMENU%\Professor Pardal\Desinstalar.bat" echo pause

del "%TEMP%\pardal_atalho.vbs" 2>nul
del "%TEMP%\pardal_menu.vbs"   2>nul

echo.
echo  =========================================
echo   Instalacao concluida!
echo  =========================================
echo.
echo   Atalhos criados:
echo   - Area de trabalho: "Professor Pardal"
echo   - Menu Iniciar ^> Professor Pardal
echo.
echo   Para desinstalar: Menu Iniciar ^> Professor Pardal ^> Desinstalar
echo.

set /p OPEN="Abrir o Professor Pardal agora? (S/N): "
if /i "%OPEN%"=="S" start "" "%APP_DIR%\ProfessorPardal.exe"

pause
