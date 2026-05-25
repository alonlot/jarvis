"""Routines manager — add/edit/remove scheduled prompts."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..core.assistant import Assistant


class _EditDialog(QDialog):
    def __init__(self, parent=None, *, name="", cron="0 8 * * 1-5", prompt="", ask=True):
        super().__init__(parent)
        self.setWindowTitle("Routine")
        self.resize(540, 380)

        self.name = QLineEdit(name)
        self.cron = QLineEdit(cron)
        self.cron.setPlaceholderText("min hour dom mon dow  (e.g. 0 8 * * 1-5)")
        self.prompt = QPlainTextEdit(prompt)
        self.ask = QCheckBox("Ask before acting"); self.ask.setChecked(ask)

        form = QFormLayout()
        form.addRow("Name", self.name)
        form.addRow("Cron", self.cron)
        form.addRow("Prompt", self.prompt)
        form.addRow("", self.ask)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        v = QVBoxLayout(self); v.addLayout(form); v.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        if not self.name.text().strip():
            QMessageBox.warning(self, "Missing", "Name is required."); return
        if not self.cron.text().strip():
            QMessageBox.warning(self, "Missing", "Cron is required."); return
        if not self.prompt.toPlainText().strip():
            QMessageBox.warning(self, "Missing", "Prompt is required."); return
        self.accept()

    def values(self) -> dict:
        return {
            "name": self.name.text().strip(),
            "cron": self.cron.text().strip(),
            "prompt": self.prompt.toPlainText().strip(),
            "ask_before_acting": self.ask.isChecked(),
        }


class RoutinesDialog(QDialog):
    def __init__(self, assistant: Assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.cfg = assistant.config
        self.setWindowTitle("Routines")
        self.resize(720, 420)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Cron", "Prompt"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        add_btn = QPushButton("Add…");      add_btn.clicked.connect(self._add)
        edit_btn = QPushButton("Edit…");    edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("Remove");    del_btn.clicked.connect(self._remove)
        run_btn = QPushButton("Run now");   run_btn.clicked.connect(self._run_now)

        btns = QHBoxLayout()
        for b in (add_btn, edit_btn, del_btn, run_btn):
            btns.addWidget(b)
        btns.addStretch(1)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)

        v = QVBoxLayout(self)
        v.addWidget(self.table, 1)
        v.addLayout(btns)
        v.addWidget(bb)

        self._reload()

    def _reload(self) -> None:
        routines = list(self.cfg.get("routines") or [])
        self.table.setRowCount(len(routines))
        for i, r in enumerate(routines):
            self.table.setItem(i, 0, QTableWidgetItem(r.get("name", "")))
            self.table.setItem(i, 1, QTableWidgetItem(r.get("cron", "")))
            preview = (r.get("prompt", "") or "").splitlines()[0][:120]
            self.table.setItem(i, 2, QTableWidgetItem(preview))

    def _routines(self) -> list[dict]:
        return list(self.cfg.get("routines") or [])

    def _save(self, routines: list[dict]) -> None:
        self.cfg.set("routines", routines)
        self.cfg.save()
        if self.assistant.scheduler:
            self.assistant.scheduler.reload()
        self._reload()

    def _add(self) -> None:
        dlg = _EditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            rts = self._routines()
            rts.append(dlg.values())
            self._save(rts)

    def _selected_row(self) -> int:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def _edit(self) -> None:
        i = self._selected_row()
        if i < 0:
            return
        rts = self._routines()
        cur = rts[i]
        dlg = _EditDialog(self, name=cur.get("name", ""), cron=cur.get("cron", ""),
                          prompt=cur.get("prompt", ""), ask=cur.get("ask_before_acting", True))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            rts[i] = dlg.values()
            self._save(rts)

    def _remove(self) -> None:
        i = self._selected_row()
        if i < 0:
            return
        rts = self._routines()
        if QMessageBox.question(self, "Remove",
                                f"Remove routine '{rts[i].get('name')}'?") == QMessageBox.StandardButton.Yes:
            del rts[i]
            self._save(rts)

    def _run_now(self) -> None:
        i = self._selected_row()
        if i < 0:
            return
        name = self._routines()[i].get("name", "")
        # Fire and forget — the response will arrive via the normal chat flow.
        import threading
        threading.Thread(
            target=self.assistant.run_routine_by_name, args=(name,), daemon=True
        ).start()
        QMessageBox.information(self, "Routine started",
                                f"Running '{name}' in the background.")
