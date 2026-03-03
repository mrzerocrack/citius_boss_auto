#!/usr/bin/env python3
"""Launcher GUI all-in-one untuk automation Citius Boss."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import signal

try:
    import psutil
except Exception:
    psutil = None  # type: ignore

try:
    from PySide6.QtCore import QProcess, Qt, QUrl
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Citius Boss Auto - All In One")
        self.resize(1300, 800)

        self.modules: Dict[str, ModuleRuntime] = {m.key: ModuleRuntime(m) for m in MODULES}
        self.python_exec = sys.executable or "python"

        self._build_ui()
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
        self.btn_open_folder = QPushButton("Buka Folder")
        self.btn_open_script = QPushButton("Buka Script")
        self.btn_open_needs = QPushButton("Buka Kebutuhan")
        self.btn_start.clicked.connect(self._start_selected)
        self.btn_stop.clicked.connect(self._stop_selected)
        self.btn_stop_all.clicked.connect(self._stop_all)
        self.btn_open_folder.clicked.connect(self._open_folder_selected)
        self.btn_open_script.clicked.connect(self._open_script_selected)
        self.btn_open_needs.clicked.connect(self._open_needs_selected)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_stop_all)
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
        proc.readyReadStandardOutput.connect(lambda k=spec.key: self._read_stdout(k))
        proc.readyReadStandardError.connect(lambda k=spec.key: self._read_stderr(k))
        proc.started.connect(lambda k=spec.key: self._set_status(k, "Running"))
        proc.finished.connect(lambda code, status, k=spec.key: self._on_finished(k, code, status))
        rt.process = proc
        self._append_log(spec.key, f"[START] cwd={spec.folder} cmd={self.python_exec} -u {spec.script}")
        proc.start()

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
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
