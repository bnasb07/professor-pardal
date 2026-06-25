"""
Cria um ProfessorPardal.exe leve usando PyInstaller.
Esse exe apenas chama pythonw.exe janela.py no diretório correto.
Resultado: ~5 MB, sem console, com ícone correto.
"""
import subprocess
import sys
import os
from pathlib import Path

BASE = Path(__file__).parent


STUB = '''\
import os, sys, subprocess
from pathlib import Path

here = Path(sys.executable).parent  # pasta do .exe
script = here / "janela.py"
pythonw = here / ".venv" / "Scripts" / "pythonw.exe"

if not pythonw.exists():
    pythonw = Path(sys.executable).parent / "pythonw.exe"

os.chdir(here)
subprocess.Popen(
    [str(pythonw), str(script)],
    cwd=str(here),
    close_fds=True,
)
'''

def main():
    try:
        import PyInstaller
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"])

    stub_path = BASE / "_launcher_stub.py"
    stub_path.write_text(STUB)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        f"--icon={BASE / 'icon.ico'}",
        "--name=ProfessorPardal",
        f"--distpath={BASE}",
        "--workpath=build_tmp",
        "--specpath=build_tmp",
        "--noconfirm",
        str(stub_path),
    ]

    print("Construindo ProfessorPardal.exe...")
    result = subprocess.run(cmd, cwd=str(BASE))
    stub_path.unlink(missing_ok=True)

    exe = BASE / "ProfessorPardal.exe"
    if exe.exists():
        print(f"\nLauncher criado: {exe}  ({exe.stat().st_size // 1024} KB)")
    else:
        print("\n✗ Falha ao criar launcher.")
        sys.exit(1)


if __name__ == "__main__":
    main()
