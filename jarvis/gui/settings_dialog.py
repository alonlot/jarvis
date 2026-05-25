"""Settings dialog — LLM / agents / TTS / STT / voice activation / overlay."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QMessageBox, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget,
)

from ..core.assistant import Assistant


def _row(form: QFormLayout, label: str, widget: QWidget) -> None:
    form.addRow(label, widget)


class SettingsDialog(QDialog):
    def __init__(self, assistant: Assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.cfg = assistant.config

        self.setWindowTitle("Jarvis settings")
        self.resize(620, 560)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_persona_tab(), "Persona")
        self.tabs.addTab(self._build_llm_tab("llm", "Chat LLM"), "Chat LLM")
        self.tabs.addTab(self._build_llm_tab("agents", "Agent backend"), "Agents")
        self.tabs.addTab(self._build_tts_tab(), "TTS")
        self.tabs.addTab(self._build_stt_tab(), "STT")
        self.tabs.addTab(self._build_voice_tab(), "Voice activation")
        self.tabs.addTab(self._build_overlay_tab(), "Overlay")
        self.tabs.addTab(self._build_git_tab(), "Git")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        v = QVBoxLayout(self)
        v.addWidget(self.tabs, 1)
        v.addWidget(buttons)

        # Holds (dotted_key, getter_callable) so save loops are concise.
        self._bindings: list[tuple[str, callable]] = []

    # ------------------------------------------------------------------
    def _bind_text(self, dotted: str, w: QLineEdit) -> QLineEdit:
        w.setText(str(self.cfg.get(dotted, "") or ""))
        self._bindings.append((dotted, w.text))
        return w

    def _bind_int(self, dotted: str, w: QSpinBox) -> QSpinBox:
        v = self.cfg.get(dotted)
        if isinstance(v, int):
            w.setValue(v)
        self._bindings.append((dotted, w.value))
        return w

    def _bind_float(self, dotted: str, w: QDoubleSpinBox) -> QDoubleSpinBox:
        v = self.cfg.get(dotted)
        if isinstance(v, (int, float)):
            w.setValue(float(v))
        self._bindings.append((dotted, w.value))
        return w

    def _bind_bool(self, dotted: str, w: QCheckBox) -> QCheckBox:
        w.setChecked(bool(self.cfg.get(dotted, False)))
        self._bindings.append((dotted, w.isChecked))
        return w

    def _bind_combo(self, dotted: str, w: QComboBox, options: list[str]) -> QComboBox:
        w.addItems(options)
        current = str(self.cfg.get(dotted, options[0]))
        if current in options:
            w.setCurrentText(current)
        self._bindings.append((dotted, w.currentText))
        return w

    # ------------------------------------------------------------------
    def _build_persona_tab(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w)
        _row(f, "Name", self._bind_text("persona.name", QLineEdit()))
        _row(f, "Address user as", self._bind_text("persona.address_user_as", QLineEdit()))
        style = QLineEdit(); style.setPlaceholderText("(longer style is best edited in config.yaml)")
        self._bind_text("persona.style", style)
        _row(f, "Style hint", style)
        return w

    def _build_llm_tab(self, section: str, _title: str) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w)

        backend_box = QGroupBox("Backend")
        bf = QFormLayout(backend_box)
        _row(bf, "Backend", self._bind_combo(f"{section}.backend", QComboBox(), ["claude_cli", "openai_compat"]))
        v.addWidget(backend_box)

        cli_box = QGroupBox("claude -p (CLI)")
        cf = QFormLayout(cli_box)
        _row(cf, "Binary", self._bind_text(f"{section}.claude_cli.binary", QLineEdit()))
        timeout = QSpinBox(); timeout.setRange(10, 24 * 3600)
        _row(cf, "Timeout (s)", self._bind_int(f"{section}.claude_cli.timeout_seconds", timeout))
        extra = QLineEdit()
        extra.setText(" ".join(self.cfg.get(f"{section}.claude_cli.extra_args") or []))
        extra.setPlaceholderText("--model claude-opus-4-7")
        self._bindings.append((f"{section}.claude_cli.extra_args",
                               lambda e=extra: [x for x in e.text().split() if x]))
        _row(cf, "Extra args", extra)
        v.addWidget(cli_box)

        api_box = QGroupBox("OpenAI-compatible API")
        af = QFormLayout(api_box)
        _row(af, "Base URL", self._bind_text(f"{section}.openai_compat.base_url", QLineEdit()))
        _row(af, "Model", self._bind_text(f"{section}.openai_compat.model", QLineEdit()))
        key = QLineEdit(); key.setEchoMode(QLineEdit.EchoMode.Password)
        _row(af, "API key", self._bind_text(f"{section}.openai_compat.api_key", key))
        _row(af, "API key env var", self._bind_text(f"{section}.openai_compat.api_key_env", QLineEdit()))
        if section == "llm":
            temp = QDoubleSpinBox(); temp.setRange(0.0, 2.0); temp.setSingleStep(0.1)
            _row(af, "Temperature", self._bind_float(f"{section}.openai_compat.temperature", temp))
        v.addWidget(api_box)
        v.addStretch(1)
        return w

    def _build_tts_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(self._bind_bool("tts.enabled", QCheckBox("Enable text-to-speech")))

        box = QGroupBox("Backend")
        f = QFormLayout(box)
        _row(f, "Backend", self._bind_combo("tts.backend", QComboBox(), ["local", "remote", "none"]))
        v.addWidget(box)

        local = QGroupBox("Local (pyttsx3)")
        lf = QFormLayout(local)
        _row(lf, "Voice hint", self._bind_text("tts.local.voice_hint", QLineEdit()))
        rate = QSpinBox(); rate.setRange(50, 400); _row(lf, "Rate", self._bind_int("tts.local.rate", rate))
        vol = QDoubleSpinBox(); vol.setRange(0.0, 1.0); vol.setSingleStep(0.05)
        _row(lf, "Volume", self._bind_float("tts.local.volume", vol))
        v.addWidget(local)

        remote = QGroupBox("Remote (HTTP)")
        rf = QFormLayout(remote)
        _row(rf, "Base URL", self._bind_text("tts.remote.base_url", QLineEdit()))
        _row(rf, "Model", self._bind_text("tts.remote.model", QLineEdit()))
        _row(rf, "Voice", self._bind_text("tts.remote.voice", QLineEdit()))
        key = QLineEdit(); key.setEchoMode(QLineEdit.EchoMode.Password)
        _row(rf, "API key", self._bind_text("tts.remote.api_key", key))
        _row(rf, "API key env var", self._bind_text("tts.remote.api_key_env", QLineEdit()))
        _row(rf, "Audio format", self._bind_text("tts.remote.format", QLineEdit()))
        v.addWidget(remote)
        v.addStretch(1)
        return w

    def _build_stt_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(self._bind_bool("stt.enabled", QCheckBox("Enable speech-to-text")))

        box = QGroupBox("Backend")
        f = QFormLayout(box)
        _row(f, "Backend", self._bind_combo("stt.backend", QComboBox(), ["local", "remote", "none"]))
        v.addWidget(box)

        local = QGroupBox("Local (faster-whisper)")
        lf = QFormLayout(local)
        _row(lf, "Model", self._bind_text("stt.local.model", QLineEdit()))
        _row(lf, "Device", self._bind_combo("stt.local.device", QComboBox(), ["auto", "cpu", "cuda"]))
        v.addWidget(local)

        remote = QGroupBox("Remote (HTTP)")
        rf = QFormLayout(remote)
        _row(rf, "Base URL", self._bind_text("stt.remote.base_url", QLineEdit()))
        _row(rf, "Model", self._bind_text("stt.remote.model", QLineEdit()))
        key = QLineEdit(); key.setEchoMode(QLineEdit.EchoMode.Password)
        _row(rf, "API key", self._bind_text("stt.remote.api_key", key))
        _row(rf, "API key env var", self._bind_text("stt.remote.api_key_env", QLineEdit()))
        v.addWidget(remote)
        v.addStretch(1)
        return w

    def _build_voice_tab(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w)
        _row(f, "Mode", self._bind_combo("voice_activation.mode", QComboBox(),
                                          ["wake_word", "push_to_talk", "off"]))
        _row(f, "Wake word model", self._bind_text("voice_activation.wake_word.model", QLineEdit()))
        thr = QDoubleSpinBox(); thr.setRange(0.0, 1.0); thr.setSingleStep(0.05)
        _row(f, "Wake word threshold", self._bind_float("voice_activation.wake_word.threshold", thr))
        ww_to = QSpinBox(); ww_to.setRange(1, 120)
        _row(f, "Wake word silence timeout (s)",
             self._bind_int("voice_activation.wake_word.silence_timeout_seconds", ww_to))
        _row(f, "Push-to-talk hotkey",
             self._bind_text("voice_activation.push_to_talk.hotkey", QLineEdit()))
        ptt_to = QSpinBox(); ptt_to.setRange(1, 120)
        _row(f, "Push-to-talk silence timeout (s)",
             self._bind_int("voice_activation.push_to_talk.silence_timeout_seconds", ptt_to))
        return w

    def _build_overlay_tab(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w)
        f.addRow(self._bind_bool("overlay.enabled", QCheckBox("Show overlay")))
        size = QSpinBox(); size.setRange(48, 320); _row(f, "Size (px)", self._bind_int("overlay.size_px", size))
        margin = QSpinBox(); margin.setRange(0, 200); _row(f, "Margin (px)", self._bind_int("overlay.margin_px", margin))
        _row(f, "Position", self._bind_combo("overlay.position", QComboBox(),
                                              ["top_left", "top_right", "bottom_left", "bottom_right"]))
        f.addRow(self._bind_bool("overlay.click_to_talk", QCheckBox("Click overlay to start listening")))
        return w

    def _build_git_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(QLabel("Scan roots (one per line):"))
        from PyQt6.QtWidgets import QPlainTextEdit
        roots = QPlainTextEdit()
        roots.setPlainText("\n".join(self.cfg.get("git.scan_roots") or []))
        self._bindings.append(("git.scan_roots",
                               lambda r=roots: [ln.strip() for ln in r.toPlainText().splitlines() if ln.strip()]))
        v.addWidget(roots, 1)
        v.addWidget(QLabel("Hosts are edited directly in config.yaml (kind/base_url/token_env)."))
        return w

    # ------------------------------------------------------------------
    def _save(self) -> None:
        try:
            for key, getter in self._bindings:
                self.cfg.set(key, getter())
            self.cfg.save()
            # Rebuild LLM in case backend changed.
            from ..core.llm import build_llm
            self.assistant.llm = build_llm(self.cfg, "llm")
            if self.assistant.scheduler:
                self.assistant.scheduler.reload()
            self.accept()
        except Exception as e:                                 # noqa: BLE001
            QMessageBox.critical(self, "Save failed", str(e))
