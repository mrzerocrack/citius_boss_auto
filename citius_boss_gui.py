#!/usr/bin/env python3
"""Launcher GUI all-in-one untuk automation Citius Boss."""

from __future__ import annotations

import configparser
import os
import shutil
import sys
import subprocess
import secrets
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional
import signal
from urllib.parse import urlparse

try:
    import psutil
except Exception:
    psutil = None  # type: ignore

try:
    from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QFileDialog,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QPlainTextEdit,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:
    print("PySide6 belum terpasang. Install dulu: pip install PySide6")
    print(f"Detail: {exc}")
    raise SystemExit(1)


@dataclass(frozen=True)
class ModuleSpec:
    key: str
    name: str
    folder: Path
    script: str
    description: str
    needs: List[str]

    @property
    def script_path(self) -> Path:
        return self.folder / self.script


ROOT_DIR = Path(__file__).resolve().parent

MODULES: List[ModuleSpec] = [
    ModuleSpec(
        key="aap",
        name="AAP - Auto Appointment",
        folder=ROOT_DIR / "aap",
        script="auto_ap.py",
        description="Polling appointment ticket dan update status ke Sistrack.",
        needs=["Internet", "Akun login Sistrack", "Captcha manual saat awal"],
    ),
    ModuleSpec(
        key="acan",
        name="ACAN - Auto Cancel",
        folder=ROOT_DIR / "acan",
        script="autocancel.py",
        description="Proses cancel ticket berdasarkan list_tiket.txt.",
        needs=[
            "File list_tiket.txt",
            "Sumber list: https://1gen.citius.co.id/api/shintei/autotools/get_list_cancel_ticket",
        ],
    ),
    ModuleSpec(
        key="aclose",
        name="ACLOSE - Auto Close",
        folder=ROOT_DIR / "aclose",
        script="autoclose.py",
        description="Proses close ticket berdasarkan list_tiket.txt.",
        needs=[
            "File list_tiket.txt",
            "Sumber list: https://1gen.citius.co.id/api/shintei/autotools/get_list_closed_ticket",
        ],
    ),
    ModuleSpec(
        key="aclose_fix",
        name="ACLOSE - Benerin Tiket",
        folder=ROOT_DIR / "aclose",
        script="benerin_tiket.py",
        description="Utility perbaikan tiket (mode batch dari list_tiket.txt).",
        needs=["File list_tiket.txt"],
    ),
    ModuleSpec(
        key="aclose_excel",
        name="ACLOSE Tanpa Upload (Excel)",
        folder=ROOT_DIR / "aclose_tanpa_upload",
        script="autoclose.py",
        description="Auto close berbasis template Excel doc.xlsx.",
        needs=["File doc.xlsx", "Hapus last_line_proccessed.txt untuk restart dari awal"],
    ),
    ModuleSpec(
        key="apend",
        name="APEND - Auto Pending",
        folder=ROOT_DIR / "apend",
        script="autopending.py",
        description="Polling ticket pending dan update suspend di Sistrack.",
        needs=["Internet", "Akun login Sistrack"],
    ),
    ModuleSpec(
        key="acrea",
        name="ACREA - Mail Scraper",
        folder=ROOT_DIR / "acrea",
        script="mailscraper.py",
        description="Scraping Gmail untuk auto create ticket.",
        needs=["Internet", "Login Gmail", "Konfigurasi xpath/token API aktif"],
    ),
]


class ModuleRuntime:
    def __init__(self, spec: ModuleSpec) -> None:
        self.spec = spec
        self.process: Optional[QProcess] = None
        self.status: str = "Idle"
        self.log_widget: Optional[QPlainTextEdit] = None


class AttachMarkerServer:
    def __init__(self, host: str = "127.0.0.1", preferred_port: int = 18765) -> None:
        self.host = host
        self.preferred_port = int(preferred_port)
        self.token = secrets.token_urlsafe(12)
        self.marker_path = f"/citius-attach/{self.token}"
        self.port: int = 0
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def marker_url(self) -> str:
        if self.port <= 0:
            return ""
        return f"http://{self.host}:{self.port}{self.marker_path}"

    @property
    def is_running(self) -> bool:
        return self._httpd is not None and self.port > 0

    def start(self) -> None:
        marker_path = self.marker_path
        marker_token = self.token

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/health":
                    payload = b'{"ok":true}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if parsed.path == marker_path:
                    body = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Citius Attach Marker</title></head>
<body style="font-family:sans-serif;line-height:1.5;padding:24px">
<h2>Citius Attach Marker</h2>
<p>Tab ini dipakai untuk identifikasi browser yang akan di-attach Selenium.</p>
<p><b>Token:</b> {marker_token}</p>
</body>
</html>""".encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                payload = b"Not Found"
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, fmt: str, *args) -> None:  # noqa: A003
                return

        last_error: Optional[Exception] = None
        for port in (self.preferred_port, 0):
            try:
                self._httpd = ThreadingHTTPServer((self.host, port), _Handler)
                self.port = int(self._httpd.server_address[1])
                break
            except Exception as exc:
                last_error = exc
                self._httpd = None
                self.port = 0

        if not self._httpd or self.port <= 0:
            raise RuntimeError(f"Gagal start attach marker server: {last_error}")

        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._httpd:
            return
        try:
            self._httpd.shutdown()
        except Exception:
            pass
        try:
            self._httpd.server_close()
        except Exception:
            pass
        self._httpd = None
        self.port = 0


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Citius Boss Auto - All In One")
        self.resize(1300, 800)

        self.modules: Dict[str, ModuleRuntime] = {m.key: ModuleRuntime(m) for m in MODULES}
        self.python_exec = sys.executable or "python"
        self.attach_server: Optional[AttachMarkerServer] = None
        self.attach_marker_url: str = ""
        self.attach_debug_port: int = int(os.environ.get("CITIUS_ATTACH_DEBUG_PORT", "9222"))
        self.attach_user_data_dir: str = self._default_attach_user_data_dir()

        self._build_ui()
        self._start_attach_marker_server()
        self._refresh_table()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        top = QHBoxLayout()
        self.python_label = QLabel(f"Python: {self.python_exec}")
        btn_pick_python = QPushButton("Pilih Python")
        btn_pick_python.clicked.connect(self._pick_python)
        top.addWidget(self.python_label, 1)
        top.addWidget(btn_pick_python)
        layout.addLayout(top)

        attach_row = QHBoxLayout()
        self.attach_label = QLabel("Attach Marker: (belum aktif)")
        self.btn_copy_attach = QPushButton("Copy Attach URL")
        self.btn_open_attach = QPushButton("Buka Attach URL")
        self.btn_open_attach_browser = QPushButton("Buka Browser Attach")
        self.btn_copy_attach.clicked.connect(self._copy_attach_url)
        self.btn_open_attach.clicked.connect(self._open_attach_url)
        self.btn_open_attach_browser.clicked.connect(self._open_attach_browser)
        self.btn_copy_attach.setEnabled(False)
        self.btn_open_attach.setEnabled(False)
        self.btn_open_attach_browser.setEnabled(False)
        attach_row.addWidget(self.attach_label, 1)
        attach_row.addWidget(self.btn_copy_attach)
        attach_row.addWidget(self.btn_open_attach)
        attach_row.addWidget(self.btn_open_attach_browser)
        layout.addLayout(attach_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        splitter.addWidget(left)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Modul", "Script", "Status", "Folder"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_select_module)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        left_layout.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop_all = QPushButton("Stop All")
        self.btn_update = QPushButton("Update")
        self.btn_open_folder = QPushButton("Buka Folder")
        self.btn_open_script = QPushButton("Buka Script")
        self.btn_open_needs = QPushButton("Buka Kebutuhan")
        self.btn_start.clicked.connect(self._start_selected)
        self.btn_stop.clicked.connect(self._stop_selected)
        self.btn_stop_all.clicked.connect(self._stop_all)
        self.btn_update.clicked.connect(self._update_project_clicked)
        self.btn_open_folder.clicked.connect(self._open_folder_selected)
        self.btn_open_script.clicked.connect(self._open_script_selected)
        self.btn_open_needs.clicked.connect(self._open_needs_selected)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_stop_all)
        btn_row.addWidget(self.btn_update)
        btn_row.addWidget(self.btn_open_folder)
        btn_row.addWidget(self.btn_open_script)
        btn_row.addWidget(self.btn_open_needs)
        left_layout.addLayout(btn_row)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        splitter.addWidget(right)

        info_group = QGroupBox("Detail Modul")
        info_layout = QVBoxLayout(info_group)
        self.lbl_name = QLabel("-")
        self.lbl_desc = QLabel("-")
        self.lbl_desc.setWordWrap(True)
        self.list_needs = QListWidget()
        info_layout.addWidget(self.lbl_name)
        info_layout.addWidget(self.lbl_desc)
        info_layout.addWidget(self.list_needs)
        right_layout.addWidget(info_group, 0)

        log_group = QGroupBox("Log")
        log_layout = QGridLayout(log_group)
        self.log_views: Dict[str, QPlainTextEdit] = {}
        for i, mod in enumerate(MODULES):
            box = QPlainTextEdit()
            box.setReadOnly(True)
            box.setPlaceholderText(f"Log {mod.name}")
            self.log_views[mod.key] = box
            self.modules[mod.key].log_widget = box
            log_layout.addWidget(QLabel(mod.name), i, 0)
            log_layout.addWidget(box, i, 1)
        right_layout.addWidget(log_group, 1)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

    def _pick_python(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Pilih Python Executable")
        if not path:
            return
        self.python_exec = path
        self.python_label.setText(f"Python: {self.python_exec}")

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(MODULES))
        for row, spec in enumerate(MODULES):
            runtime = self.modules[spec.key]
            self.table.setItem(row, 0, QTableWidgetItem(spec.name))
            self.table.setItem(row, 1, QTableWidgetItem(spec.script))
            self.table.setItem(row, 2, QTableWidgetItem(runtime.status))
            self.table.setItem(row, 3, QTableWidgetItem(str(spec.folder)))
        self.table.resizeColumnsToContents()

    def _start_attach_marker_server(self) -> None:
        server = AttachMarkerServer()
        try:
            server.start()
        except Exception as exc:
            self.attach_server = None
            self.attach_marker_url = ""
            self.attach_label.setText(f"Attach Marker: gagal start ({exc})")
            self.btn_copy_attach.setEnabled(False)
            self.btn_open_attach.setEnabled(False)
            self.btn_open_attach_browser.setEnabled(False)
            return

        self.attach_server = server
        self.attach_marker_url = server.marker_url
        self.attach_label.setText(f"Attach Marker: {self.attach_marker_url}")
        self.btn_copy_attach.setEnabled(True)
        self.btn_open_attach.setEnabled(True)
        self.btn_open_attach_browser.setEnabled(True)

    def _copy_attach_url(self) -> None:
        if not self.attach_marker_url:
            return
        QApplication.clipboard().setText(self.attach_marker_url)

    def _open_attach_url(self) -> None:
        if not self.attach_marker_url:
            return
        QDesktopServices.openUrl(QUrl(self.attach_marker_url))

    def _default_attach_user_data_dir(self) -> str:
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA") or str(ROOT_DIR)
            return str(Path(base) / "CitiusBossAuto" / "attach_profile")
        if sys.platform == "darwin":
            return str(Path.home() / "Library" / "Application Support" / "CitiusBossAuto" / "attach_profile")
        return str(Path.home() / ".cache" / "citius_attach_profile")

    def _resolve_chrome_binary(self) -> str:
        env_bin = (os.environ.get("CHROME_BINARY") or "").strip()
        if env_bin and Path(env_bin).exists():
            return env_bin

        candidates: List[str] = []
        if os.name == "nt":
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
            program_w6432 = os.environ.get("ProgramW6432", r"C:\Program Files")
            program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
            candidates.extend(
                [
                    shutil.which("chrome.exe") or "",
                    shutil.which("chrome") or "",
                    os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe")
                    if local_app_data
                    else "",
                    os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(program_w6432, "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
                ]
            )
        elif sys.platform == "darwin":
            candidates.extend(
                [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",
                ]
            )
        else:
            candidates.extend(
                [
                    shutil.which("google-chrome") or "",
                    shutil.which("google-chrome-stable") or "",
                    "/opt/google/chrome/chrome",
                    shutil.which("chromium-browser") or "",
                    shutil.which("chromium") or "",
                ]
            )

        for path in candidates:
            if path and Path(path).exists():
                return path
        return ""

    def _open_attach_browser(self) -> None:
        if not self.attach_marker_url:
            QMessageBox.critical(self, "Attach Marker", "Attach marker URL belum aktif.")
            return

        chrome_bin = self._resolve_chrome_binary()
        if not chrome_bin:
            QMessageBox.critical(
                self,
                "Chrome Tidak Ditemukan",
                "Chrome binary tidak ditemukan. Set env CHROME_BINARY atau install Google Chrome.",
            )
            return

        profile_dir = Path(self.attach_user_data_dir)
        try:
            profile_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Siapkan Profile", f"Gagal membuat profile attach:\n{exc}")
            return

        args = [
            chrome_bin,
            f"--remote-debugging-port={self.attach_debug_port}",
            f"--user-data-dir={str(profile_dir)}",
            "--no-first-run",
            "--no-default-browser-check",
            self.attach_marker_url,
        ]
        try:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Buka Browser Attach", f"{exc}")
            return

        QMessageBox.information(
            self,
            "Browser Attach Dibuka",
            "Browser attach-ready sudah dibuka.\n"
            f"Port: {self.attach_debug_port}\n"
            f"Profile: {profile_dir}\n\n"
            "Silakan login Gmail di browser tersebut (sekali saja), lalu jalankan modul ACREA.",
        )

    def _current_spec(self) -> Optional[ModuleSpec]:
        row = self.table.currentRow()
        if row < 0:
            return None
        return MODULES[row]

    def _on_select_module(self) -> None:
        spec = self._current_spec()
        if spec is None:
            self.lbl_name.setText("-")
            self.lbl_desc.setText("-")
            self.list_needs.clear()
            return
        self.lbl_name.setText(f"{spec.name} [{spec.script}]")
        self.lbl_desc.setText(spec.description)
        self.list_needs.clear()
        for item in spec.needs:
            QListWidgetItem(item, self.list_needs)

    def _append_log(self, key: str, text: str) -> None:
        rt = self.modules[key]
        if rt.log_widget is None:
            return
        rt.log_widget.appendPlainText(text.rstrip())
        bar = rt.log_widget.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _set_status(self, key: str, status: str) -> None:
        self.modules[key].status = status
        self._refresh_table()

    def _start_selected(self) -> None:
        spec = self._current_spec()
        if spec is None:
            QMessageBox.warning(self, "Info", "Pilih modul dulu.")
            return
        self._start_module(spec)

    def _start_module(self, spec: ModuleSpec) -> None:
        rt = self.modules[spec.key]
        if rt.process and rt.process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.information(self, "Info", f"{spec.name} sedang berjalan.")
            return
        if not spec.script_path.is_file():
            QMessageBox.critical(self, "Error", f"Script tidak ditemukan: {spec.script_path}")
            return

        proc = QProcess(self)
        proc.setWorkingDirectory(str(spec.folder))
        proc.setProgram(self.python_exec)
        proc.setArguments(["-u", spec.script])
        env = QProcessEnvironment.systemEnvironment()
        self._inject_module_env(spec, env)
        proc.setProcessEnvironment(env)
        proc.readyReadStandardOutput.connect(lambda k=spec.key: self._read_stdout(k))
        proc.readyReadStandardError.connect(lambda k=spec.key: self._read_stderr(k))
        proc.started.connect(lambda k=spec.key: self._set_status(k, "Running"))
        proc.finished.connect(lambda code, status, k=spec.key: self._on_finished(k, code, status))
        rt.process = proc
        self._append_log(spec.key, f"[START] cwd={spec.folder} cmd={self.python_exec} -u {spec.script}")
        if spec.key == "acrea" and self.attach_marker_url:
            self._append_log(spec.key, f"[INFO] Attach marker URL: {self.attach_marker_url}")
            self._append_log(
                spec.key,
                "[INFO] Buka Chrome manual dengan --remote-debugging-port=<port> "
                "lalu buka URL marker di profil yang mau dipakai.",
            )
        proc.start()

    def _inject_module_env(self, spec: ModuleSpec, env: QProcessEnvironment) -> None:
        if spec.key != "acrea":
            return
        if not self.attach_marker_url:
            return
        env.insert("CHROME_ATTACH_EXISTING", "1")
        env.insert("CHROME_ATTACH_TARGET_URL", self.attach_marker_url)
        env.insert("CHROME_DEBUG_PORT", str(self.attach_debug_port))
        # Default timeout lebih panjang karena attach menunggu user buka tab marker.
        if not env.contains("CHROME_ATTACH_TIMEOUT"):
            env.insert("CHROME_ATTACH_TIMEOUT", "300")

    def _read_stdout(self, key: str) -> None:
        rt = self.modules[key]
        if not rt.process:
            return
        data = bytes(rt.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self._append_log(key, data)

    def _read_stderr(self, key: str) -> None:
        rt = self.modules[key]
        if not rt.process:
            return
        data = bytes(rt.process.readAllStandardError()).decode("utf-8", errors="replace")
        if data:
            self._append_log(key, data)

    def _on_finished(self, key: str, code: int, _status: QProcess.ExitStatus) -> None:
        self._set_status(key, f"Stopped (exit={code})")
        self._append_log(key, f"[STOP] exit={code}")

    def _stop_selected(self) -> None:
        spec = self._current_spec()
        if spec is None:
            return
        self._stop_module(spec.key)

    def _stop_module(self, key: str) -> None:
        rt = self.modules[key]
        proc = rt.process
        if not proc or proc.state() == QProcess.ProcessState.NotRunning:
            return
        pid = int(proc.processId())
        self._append_log(key, f"[STOP] terminate requested pid={pid}")

        # Paksa matikan process tree (python + chromedriver + chrome UC) agar tidak nyangkut.
        if pid > 0 and psutil is not None:
            self._kill_process_tree(key, pid)
            # Tunggu signal finished dari QProcess sebentar.
            proc.waitForFinished(3000)
            return

        # Fallback jika psutil tidak tersedia.
        proc.terminate()
        if not proc.waitForFinished(5000):
            self._append_log(key, "[STOP] kill forced (fallback)")
            proc.kill()
            proc.waitForFinished(3000)

    def _kill_process_tree(self, key: str, root_pid: int) -> None:
        if psutil is None:
            return
        try:
            parent = psutil.Process(root_pid)
        except psutil.NoSuchProcess:
            self._append_log(key, f"[STOP] pid {root_pid} sudah tidak ada")
            return
        except Exception as exc:
            self._append_log(key, f"[STOP] gagal akses pid {root_pid}: {exc}")
            return

        try:
            children = parent.children(recursive=True)
        except Exception:
            children = []
        targets = [*children, parent]
        if not targets:
            return

        self._append_log(key, f"[STOP] kill tree size={len(targets)}")

        for p in targets:
            try:
                p.terminate()
            except psutil.NoSuchProcess:
                pass
            except Exception:
                pass

        gone, alive = psutil.wait_procs(targets, timeout=5)
        if alive:
            self._append_log(key, f"[STOP] force kill alive={len(alive)}")
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
                except Exception:
                    # Last resort: signal SIGKILL jika kill() gagal.
                    try:
                        os.kill(p.pid, signal.SIGKILL)
                    except Exception:
                        pass
            psutil.wait_procs(alive, timeout=3)

    def _stop_all(self) -> None:
        for key in self.modules:
            self._stop_module(key)

    def _running_module_names(self) -> List[str]:
        running: List[str] = []
        for spec in MODULES:
            proc = self.modules[spec.key].process
            if proc and proc.state() != QProcess.ProcessState.NotRunning:
                running.append(spec.name)
        return running

    def _update_project_clicked(self) -> None:
        running = self._running_module_names()
        if running:
            QMessageBox.warning(
                self,
                "Update Ditolak",
                "Stop dulu semua proses sebelum update.\n"
                + "\n".join(f"- {name}" for name in running),
            )
            return

        answer = QMessageBox.question(
            self,
            "Konfirmasi Update",
            "Tarik versi terbaru sekarang? (jika ada perubahan lokal, bisa terkena overwrite)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            ok, detail = self._update_project()
        finally:
            QApplication.restoreOverrideCursor()

        if ok:
            QMessageBox.information(self, "Update Berhasil", detail)
        else:
            QMessageBox.critical(self, "Update Gagal", detail)

    def _update_project(self) -> tuple[bool, str]:
        remote_name, _remote_url, branch = self._read_git_target()
        if not shutil.which("git"):
            return (
                False,
                "Git tidak ditemukan di OS.\n"
                "Project ini wajib pakai git update. Install dulu git lalu jalankan ulang GUI.",
            )
        ok, msg = self._run_git_pull(remote_name, branch)
        return ok, msg

    def _read_git_target(self) -> tuple[str, str, str]:
        remote_name = "origin"
        branch = "main"
        remote_url = ""
        git_dir = ROOT_DIR / ".git"

        head_path = git_dir / "HEAD"
        if head_path.is_file():
            try:
                head_content = head_path.read_text(encoding="utf-8", errors="replace").strip()
                if head_content.startswith("ref: refs/heads/"):
                    branch = head_content.rsplit("/", 1)[-1] or branch
            except Exception:
                pass

        config_path = git_dir / "config"
        if not config_path.is_file():
            return remote_name, remote_url, branch

        cfg = configparser.ConfigParser()
        try:
            cfg.read(config_path, encoding="utf-8")
        except Exception:
            return remote_name, remote_url, branch

        branch_section = f'branch "{branch}"'
        if cfg.has_section(branch_section):
            remote_name = cfg.get(branch_section, "remote", fallback=remote_name)
            merge_ref = cfg.get(branch_section, "merge", fallback=f"refs/heads/{branch}")
            if merge_ref.startswith("refs/heads/"):
                branch = merge_ref.rsplit("/", 1)[-1] or branch

        remote_section = f'remote "{remote_name}"'
        if cfg.has_section(remote_section):
            remote_url = cfg.get(remote_section, "url", fallback="")
        elif cfg.has_section('remote "origin"'):
            remote_name = "origin"
            remote_url = cfg.get('remote "origin"', "url", fallback="")

        return remote_name, remote_url, branch

    def _run_git_pull(self, remote_name: str, branch: str) -> tuple[bool, str]:
        cmd = ["git", "-C", str(ROOT_DIR), "pull", "--ff-only", remote_name, branch]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except Exception as exc:
            return False, f"git pull gagal dijalankan: {exc}"

        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        detail_lines = [f"$ {' '.join(cmd)}", f"exit={result.returncode}"]
        if out:
            detail_lines.append(f"stdout:\n{out}")
        if err:
            detail_lines.append(f"stderr:\n{err}")
        return result.returncode == 0, "\n".join(detail_lines)

    def _open_folder_selected(self) -> None:
        spec = self._current_spec()
        if spec is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(spec.folder)))

    def _open_script_selected(self) -> None:
        spec = self._current_spec()
        if spec is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(spec.script_path)))

    def _open_needs_selected(self) -> None:
        spec = self._current_spec()
        if spec is None:
            return

        # Shortcut buka file yang sering dipakai berdasarkan modul.
        candidates: List[Path] = []
        if spec.key in {"acan", "aclose", "aclose_fix"}:
            candidates.append(spec.folder / "list_tiket.txt")
        if spec.key == "aclose_excel":
            candidates.append(spec.folder / "doc.xlsx")
        if spec.key == "acrea":
            candidates.append(spec.folder / "bot_status.txt")

        opened = False
        for path in candidates:
            if path.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
                opened = True
                break
        if not opened:
            QMessageBox.information(
                self,
                "Info",
                "File kebutuhan default belum ditemukan. Silakan buka folder modul dan buat file kebutuhannya.",
            )

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._stop_all()
        if self.attach_server:
            self.attach_server.stop()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    if not shutil.which("git"):
        QMessageBox.critical(
            None,
            "Git Wajib",
            "Git tidak ditemukan di OS.\n"
            "Silakan install git terlebih dahulu, lalu jalankan kembali citius_boss_gui.py.",
        )
        return 1
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
