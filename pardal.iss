; ──────────────────────────────────────────────────────────────────────────────
; Professor Pardal — Inno Setup Script
; Cria um instalador .exe profissional para Windows
; ──────────────────────────────────────────────────────────────────────────────

#define AppName      "Professor Pardal"
#define AppVersion   "1.0"
#define AppPublisher "Professor Pardal"
#define AppURL       "http://localhost:8765"
#define AppExeName   "ProfessorPardal.exe"
#define AppDir       "{userappdata}\ProfessorPardal"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={userappdata}\ProfessorPardal
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=ProfessorPardal_Setup
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSmallImageFile=icon.ico
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\icon.ico
UninstallDisplayName={#AppName}
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon";     Description: "Criar atalho na Área de Trabalho";    GroupDescription: "Atalhos:"; Flags: checked
Name: "startupicon";     Description: "Iniciar com o Windows";                GroupDescription: "Opções:";  Flags: unchecked

[Files]
; Arquivos do app
Source: "main.py";              DestDir: "{app}"; Flags: ignoreversion
Source: "janela.py";            DestDir: "{app}"; Flags: ignoreversion
Source: "config.json";          DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "gerar_icone.py";       DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico";             DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt";     DestDir: "{app}"; Flags: ignoreversion
Source: "services\*";           DestDir: "{app}\services"; Flags: ignoreversion recursesubdirs
Source: "static\*";             DestDir: "{app}\static";   Flags: ignoreversion recursesubdirs
Source: "study_materials\*";    DestDir: "{app}\study_materials"; Flags: ignoreversion recursesubdirs skipifsourcedoesntexist

; Lançador .exe (wrapper que chama pythonw)
Source: "launcher\ProfessorPardal.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\study_materials"

[Icons]
Name: "{group}\{#AppName}";        Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Desinstalar";       Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Registry]
; Iniciar com Windows (opcional)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "ProfessorPardal"; \
  ValueData: """{app}\{#AppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; Instala dependências Python durante a instalação
Filename: "{cmd}"; Parameters: "/c ""{app}\setup_deps.bat"""; \
  WorkingDir: "{app}"; Flags: runhidden waituntilterminated; \
  StatusMsg: "Instalando dependências (pode demorar alguns minutos)..."

; Abre o app após instalar
Filename: "{app}\{#AppExeName}"; Description: "Abrir Professor Pardal agora"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im pythonw.exe /fi ""WINDOWTITLE eq Professor Pardal*"""; \
  Flags: runhidden

[Code]
// Verifica se Python 3.8+ está instalado
function IsPythonInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
  if not Result then
    Result := Exec('python3', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
begin
  if not IsPythonInstalled() then
  begin
    MsgBox(
      'Python não foi encontrado no seu computador.' + #13#10 +
      #13#10 +
      'Instale o Python 3.10 ou superior em:' + #13#10 +
      'https://python.org/downloads' + #13#10 +
      #13#10 +
      'IMPORTANTE: Marque "Add Python to PATH" durante a instalação.' + #13#10 +
      #13#10 +
      'Após instalar o Python, execute este instalador novamente.',
      mbError, MB_OK
    );
    Result := False;
  end else
    Result := True;
end;
