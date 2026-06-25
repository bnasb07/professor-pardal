"""
Professor Pardal — janela Qt nativa (PySide6 + QWebEngineView).
Execute com pythonw.exe para rodar sem terminal.
"""
import os
import sys
import time
import threading
import traceback
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent
PORT = 8765

os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

# pythonw.exe tem stdout/stderr None — corrige antes de qualquer import
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

_LOG = BASE_DIR / "pardal_debug.log"


def _log(msg: str):
    try:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _start_server():
    try:
        import uvicorn
        _log(f"Iniciando uvicorn na porta {PORT}...")
        uvicorn.run("main:app", host="127.0.0.1", port=PORT, log_level="error")
    except Exception:
        _log(f"ERRO no servidor:\n{traceback.format_exc()}")


def _server_ready(timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    _log(f"Iniciando. sys.executable={sys.executable}")

    # Segunda instância → apenas ignora (janela já está aberta)
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
        _log("Servidor já rodando — segunda instância ignorada.")
        return
    except Exception:
        pass

    # Inicia servidor FastAPI em thread daemon
    threading.Thread(target=_start_server, daemon=True).start()

    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QSystemTrayIcon, QMenu, QMessageBox,
    )
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QIcon, QAction

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Professor Pardal")
    app.setOrganizationName("Professor Pardal")
    app.setQuitOnLastWindowClosed(False)  # fecha → minimiza para bandeja

    icon_path = BASE_DIR / "icon.ico"
    icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
    app.setWindowIcon(icon)

    # Aguarda o servidor FastAPI estar pronto
    _log("Aguardando servidor...")
    if not _server_ready(timeout=30):
        _log("TIMEOUT: servidor não iniciou em 30 s.")
        QMessageBox.critical(
            None,
            "Professor Pardal",
            "O servidor não iniciou.\n\n"
            "Verifique se as dependências estão instaladas:\n"
            "  pip install -r requirements.txt",
        )
        sys.exit(1)

    _log("Servidor pronto. Criando janela Qt...")

    # ── Janela principal ──────────────────────────────────────────────────────

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Professor Pardal")
            self.resize(1280, 820)
            self.setMinimumSize(960, 640)
            self.setWindowIcon(icon)
            # Fundo escuro enquanto o WebEngine carrega
            self.setStyleSheet("QMainWindow { background: #0d1117; }")

            # Perfil sem cache em disco para não acumular dados
            profile = QWebEngineProfile("pardal", self)
            profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)

            self._view = QWebEngineView(self)
            s = self._view.settings()
            s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, False)

            self._view.setUrl(QUrl(f"http://127.0.0.1:{PORT}/"))
            self.setCentralWidget(self._view)

        def closeEvent(self, event):
            event.ignore()
            self.hide()
            tray.showMessage(
                "Professor Pardal",
                "Continua rodando na bandeja do sistema.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )

    win = MainWindow()

    # ── Bandeja do sistema ────────────────────────────────────────────────────

    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip("Professor Pardal")

    tray_menu = QMenu()

    act_open = QAction("Abrir Professor Pardal")
    act_open.triggered.connect(
        lambda: (win.showNormal(), win.raise_(), win.activateWindow())
    )

    act_quit = QAction("Sair")
    act_quit.triggered.connect(app.quit)

    tray_menu.addAction(act_open)
    tray_menu.addSeparator()
    tray_menu.addAction(act_quit)
    tray.setContextMenu(tray_menu)

    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            win.showNormal()
            win.raise_()
            win.activateWindow()

    tray.activated.connect(on_tray_activated)
    tray.show()

    win.show()
    _log("Janela Qt aberta.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
