@echo off
title Construindo instalador do Professor Pardal...
color 0A
cls
echo.
echo  =========================================
echo   Professor Pardal - Construir Instalador
echo  =========================================
echo.
cd /d "%~dp0"

REM ── Passo 1: Verifica venv ───────────────────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo ERRO: Execute iniciar.bat primeiro para criar o ambiente.
    pause & exit /b
)
set PYTHON=.venv\Scripts\python.exe
set PYTHONW=.venv\Scripts\pythonw.exe

REM ── Passo 2: Garante PyInstaller instalado ───────────────────────────────
echo [1/3] Verificando PyInstaller...
%PYTHON% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    .venv\Scripts\pip.exe install pyinstaller --quiet
)

REM ── Passo 3: Cria ProfessorPardal.exe (launcher leve) ───────────────────
echo [2/3] Criando launcher exe...
%PYTHON% criar_launcher.py
if errorlevel 1 ( echo ERRO ao criar launcher. & pause & exit /b )

REM ── Passo 4: Verifica Inno Setup ────────────────────────────────────────
echo [3/3] Procurando Inno Setup...

set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="" (
    echo.
    echo  Inno Setup nao encontrado.
    echo.
    echo  Para criar o instalador .exe:
    echo  1. Baixe gratis em: https://jrsoftware.org/isdl.php
    echo  2. Instale o Inno Setup 6
    echo  3. Execute este script novamente
    echo.
    echo  O launcher ProfessorPardal.exe ja foi criado na pasta "launcher\".
    echo  Voce pode usa-lo diretamente ou aguardar o Inno Setup para o instalador.
    echo.
    pause & exit /b
)

REM ── Passo 5: Compila o instalador ────────────────────────────────────────
if not exist "dist" mkdir dist
echo Compilando instalador com Inno Setup...
%ISCC% pardal.iss
if errorlevel 1 ( echo ERRO na compilacao do instalador. & pause & exit /b )

echo.
echo  =========================================
echo   Concluido!
echo  =========================================
echo.
if exist "dist\ProfessorPardal_Setup.exe" (
    echo   Instalador: dist\ProfessorPardal_Setup.exe
    for %%F in ("dist\ProfessorPardal_Setup.exe") do echo   Tamanho: %%~zF bytes
    echo.
    set /p OPEN="Abrir a pasta dist? (S/N): "
    if /i "%OPEN%"=="S" explorer dist
) else (
    echo   launcher\ProfessorPardal.exe criado com sucesso.
)
pause
