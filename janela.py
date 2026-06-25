"""
Professor Pardal — janela nativa WebView2 + bandeja do sistema.
Execute com pythonw.exe para rodar sem terminal.
"""
import os
import sys
import time
import threading
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent
PORT = 8765

os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))


# ── Servidor FastAPI ──────────────────────────────────────────────────────────

def _start_server():
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, log_level="error")


def _server_ready(timeout=25) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


# ── Bandeja do sistema ────────────────────────────────────────────────────────

def _run_tray(window):
    try:
        import pystray
        from PIL import Image

        icon_path = BASE_DIR / "icon.ico"
        img = Image.open(icon_path).resize((64, 64)).convert("RGBA") \
            if icon_path.exists() \
            else Image.new("RGBA", (64, 64), (26, 27, 34, 255))

        def on_abrir(icon, item):
            window.show()

        def on_sair(icon, item):
            icon.stop()
            window.destroy()

        menu = pystray.Menu(
            pystray.MenuItem("Abrir Professor Pardal", on_abrir, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", on_sair),
        )
        tray = pystray.Icon("ProfessorPardal", img, "Professor Pardal", menu)
        tray.run()
    except Exception as e:
        print(f"[Tray] Erro: {e}", file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Se já há uma instância rodando, traz a janela para frente e sai
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
        return
    except Exception:
        pass

    # Inicia servidor em thread daemon
    threading.Thread(target=_start_server, daemon=True).start()

    # Aguarda servidor estar pronto
    if not _server_ready():
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk(); root.withdraw()
            messagebox.showerror(
                "Professor Pardal",
                "O servidor não iniciou.\nVerifique se as dependências estão instaladas."
            )
        except Exception:
            pass
        sys.exit(1)

    import webview

    window = webview.create_window(
        title="Professor Pardal",
        url=f"http://127.0.0.1:{PORT}",
        width=1280,
        height=820,
        min_size=(960, 640),
        text_select=True,
        background_color="#0d1117",
    )

    # Fecha → minimiza para bandeja em vez de sair
    def ao_fechar():
        try:
            window.hide()
        except Exception:
            pass
        return False  # cancela o fechamento

    window.events.closing += ao_fechar

    # Bandeja em thread separada
    threading.Thread(target=_run_tray, args=(window,), daemon=True).start()

    # Inicia loop GUI na thread principal (bloqueia até destroy())
    webview.start(debug=False)


if __name__ == "__main__":
    main()
