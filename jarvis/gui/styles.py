"""Global QSS — Stark Industries / Iron Man HUD aesthetic.

Pure black backgrounds, electric cyan accents, ALL CAPS labels with
letter-spacing, sharp corners, monospace tech typography. Falls back
cleanly across systems that don't have Orbitron/Rajdhani installed.
"""

# Centralised palette so widgets that paint by hand stay in sync.
PALETTE = {
    "bg":            "#000508",
    "bg_surface":    "#001018",
    "bg_elevated":   "#00182a",
    "bg_panel":      "#00101c",
    "border":        "#0a3a5a",
    "border_bright": "#00aedb",
    "cyan":          "#00d4ff",
    "cyan_dim":      "#0096b8",
    "cyan_glow":     "#7be9ff",
    "white":         "#e0f7ff",
    "muted":         "#5a8fa8",
    "amber":         "#ffaa00",
    "danger":        "#ff4060",
}

JARVIS_QSS = f"""
* {{
    color: {PALETTE['white']};
    font-family: "Orbitron", "Rajdhani", "Eurostile", "JetBrains Mono",
                 "Consolas", "Cascadia Mono", "DejaVu Sans Mono", monospace;
    font-size: 10pt;
}}

QMainWindow, QWidget#mainCentral {{
    background-color: {PALETTE['bg']};
}}

/* ───────────── HUD top status bar ───────────── */

QWidget#hudBar {{
    background-color: {PALETTE['bg']};
    border-bottom: 1px solid {PALETTE['border']};
}}
QLabel#hudCorner {{
    color: {PALETTE['cyan']};
    font-size: 9pt;
    letter-spacing: 2px;
    padding: 0 14px;
}}
QLabel#hudStatus {{
    color: {PALETTE['muted']};
    font-size: 9pt;
    letter-spacing: 3px;
}}
QLabel#hudStatus[severity="ok"]      {{ color: {PALETTE['cyan']}; }}
QLabel#hudStatus[severity="warn"]    {{ color: {PALETTE['amber']}; }}
QLabel#hudStatus[severity="danger"]  {{ color: {PALETTE['danger']}; }}

/* ───────────── Sidebar ───────────── */

QWidget#sidebar {{
    background-color: {PALETTE['bg']};
    border-right: 1px solid {PALETTE['border']};
}}

QLabel#brand {{
    color: {PALETTE['cyan']};
    font-size: 14pt;
    font-weight: 700;
    letter-spacing: 6px;
    padding: 0;
}}
QLabel#brandSub {{
    color: {PALETTE['muted']};
    font-size: 8pt;
    letter-spacing: 3px;
}}

QPushButton#navBtn {{
    background-color: transparent;
    color: {PALETTE['muted']};
    border: none;
    border-left: 2px solid transparent;
    padding: 14px 20px;
    text-align: left;
    font-size: 10pt;
    letter-spacing: 3px;
}}
QPushButton#navBtn:hover {{
    background-color: {PALETTE['bg_surface']};
    color: {PALETTE['cyan_glow']};
}}
QPushButton#navBtn:checked {{
    background-color: {PALETTE['bg_surface']};
    color: {PALETTE['cyan']};
    border-left: 2px solid {PALETTE['cyan']};
}}

QLabel#navCode {{
    color: {PALETTE['cyan_dim']};
    font-size: 8pt;
    letter-spacing: 2px;
    padding: 0 20px;
}}

/* ───────────── Chat header reactor area ───────────── */

QWidget#headerArea {{
    background-color: {PALETTE['bg']};
    border-bottom: 1px solid {PALETTE['border']};
}}
QLabel#stateLabel {{
    color: {PALETTE['cyan']};
    font-size: 11pt;
    letter-spacing: 8px;
    font-weight: 600;
}}
QLabel#stateSub {{
    color: {PALETTE['muted']};
    font-size: 8pt;
    letter-spacing: 4px;
}}
QLabel#telemetry {{
    color: {PALETTE['cyan_dim']};
    font-size: 8pt;
    letter-spacing: 2px;
    padding: 0 24px;
}}

/* ───────────── Scrollbars ───────────── */

QScrollArea, QScrollArea > QWidget > QWidget {{
    background-color: {PALETTE['bg']};
    border: none;
}}
QScrollBar:vertical {{
    background: {PALETTE['bg']};
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {PALETTE['border']};
    border-radius: 0;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {PALETTE['cyan_dim']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ───────────── Message frames ───────────── */

QLabel#roleLabel {{
    color: {PALETTE['cyan']};
    font-size: 8pt;
    letter-spacing: 4px;
    padding: 0;
}}
QLabel#roleLabelUser {{
    color: {PALETTE['cyan_glow']};
    font-size: 8pt;
    letter-spacing: 4px;
    padding: 0;
}}
QLabel#bubbleText {{
    background: transparent;
    color: {PALETTE['white']};
    padding: 0;
}}
QLabel#bubbleMeta {{
    color: {PALETTE['cyan_dim']};
    font-size: 8pt;
    letter-spacing: 2px;
    padding: 2px 4px;
}}

/* ───────────── Input bar ───────────── */

QWidget#inputBar {{
    background-color: {PALETTE['bg']};
    border-top: 1px solid {PALETTE['border']};
}}

QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: {PALETTE['bg_surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 0;
    padding: 10px 14px;
    color: {PALETTE['white']};
    selection-background-color: {PALETTE['cyan_dim']};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {PALETTE['cyan']};
}}
QLineEdit#chatInput {{
    font-size: 10pt;
    letter-spacing: 1px;
    padding: 12px 16px;
}}

/* ───────────── Buttons ───────────── */

QPushButton {{
    background-color: {PALETTE['bg_surface']};
    color: {PALETTE['cyan']};
    border: 1px solid {PALETTE['border_bright']};
    border-radius: 0;
    padding: 10px 18px;
    letter-spacing: 3px;
    font-size: 9pt;
}}
QPushButton:hover {{
    background-color: {PALETTE['bg_elevated']};
    color: {PALETTE['cyan_glow']};
    border-color: {PALETTE['cyan']};
}}
QPushButton:disabled {{
    color: {PALETTE['muted']};
    border-color: {PALETTE['border']};
    background-color: {PALETTE['bg']};
}}
QPushButton#primary {{
    background-color: {PALETTE['cyan_dim']};
    color: {PALETTE['bg']};
    border: 1px solid {PALETTE['cyan']};
    font-weight: 700;
}}
QPushButton#primary:hover {{
    background-color: {PALETTE['cyan']};
}}
QPushButton#danger {{
    color: {PALETTE['danger']};
    border-color: {PALETTE['danger']};
}}
QPushButton#micBtn {{
    background-color: transparent;
    border: 1px solid {PALETTE['cyan']};
    border-radius: 0;
    min-width: 46px;
    min-height: 46px;
    font-size: 14pt;
    color: {PALETTE['cyan']};
}}
QPushButton#micBtn:hover {{
    background-color: {PALETTE['bg_elevated']};
    color: {PALETTE['cyan_glow']};
}}

/* ───────────── Panels (settings, routines) ───────────── */

QLabel#panelTitle {{
    color: {PALETTE['cyan']};
    font-size: 16pt;
    font-weight: 700;
    letter-spacing: 8px;
}}
QLabel#panelSub {{
    color: {PALETTE['muted']};
    font-size: 9pt;
    letter-spacing: 2px;
}}

QTabWidget::pane {{
    border: 1px solid {PALETTE['border']};
    background-color: {PALETTE['bg_panel']};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {PALETTE['bg']};
    color: {PALETTE['muted']};
    padding: 10px 18px;
    border: 1px solid {PALETTE['border']};
    border-bottom: none;
    letter-spacing: 3px;
    font-size: 9pt;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    color: {PALETTE['cyan']};
    background-color: {PALETTE['bg_panel']};
    border-color: {PALETTE['cyan']};
}}
QTabBar::tab:hover:!selected {{ color: {PALETTE['cyan_glow']}; }}

QGroupBox {{
    border: 1px solid {PALETTE['border']};
    border-radius: 0;
    margin-top: 16px;
    padding-top: 14px;
    color: {PALETTE['muted']};
    font-size: 9pt;
    letter-spacing: 3px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: {PALETTE['cyan']};
    background-color: {PALETTE['bg']};
}}

/* ───────────── Form inputs ───────────── */

QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {PALETTE['bg_surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 0;
    padding: 6px 10px;
    min-height: 26px;
    color: {PALETTE['white']};
}}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {PALETTE['cyan']};
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ width: 8px; height: 8px; }}
QComboBox QAbstractItemView {{
    background-color: {PALETTE['bg_surface']};
    border: 1px solid {PALETTE['cyan_dim']};
    color: {PALETTE['white']};
    selection-background-color: {PALETTE['cyan_dim']};
    selection-color: {PALETTE['bg']};
    outline: none;
}}

QCheckBox {{
    spacing: 10px;
    color: {PALETTE['white']};
    letter-spacing: 2px;
    font-size: 9pt;
}}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {PALETTE['cyan']};
    background-color: {PALETTE['bg_surface']};
}}
QCheckBox::indicator:checked {{
    background-color: {PALETTE['cyan']};
    border-color: {PALETTE['cyan_glow']};
}}

QLabel {{
    color: {PALETTE['white']};
    letter-spacing: 1px;
}}

/* ───────────── Tables (routines) ───────────── */

QTableWidget {{
    background-color: {PALETTE['bg_panel']};
    gridline-color: {PALETTE['border']};
    border: 1px solid {PALETTE['border']};
    border-radius: 0;
    selection-background-color: {PALETTE['cyan_dim']};
    selection-color: {PALETTE['bg']};
    color: {PALETTE['white']};
}}
QHeaderView::section {{
    background-color: {PALETTE['bg']};
    color: {PALETTE['cyan']};
    padding: 10px;
    border: none;
    border-bottom: 1px solid {PALETTE['cyan_dim']};
    border-right: 1px solid {PALETTE['border']};
    letter-spacing: 3px;
    font-size: 9pt;
}}

QMenuBar {{
    background-color: {PALETTE['bg']};
    color: {PALETTE['cyan']};
    border-bottom: 1px solid {PALETTE['border']};
    letter-spacing: 2px;
}}
QMenuBar::item {{ padding: 6px 12px; background: transparent; }}
QMenuBar::item:selected {{ background-color: {PALETTE['bg_surface']}; }}
QMenu {{
    background-color: {PALETTE['bg_surface']};
    color: {PALETTE['white']};
    border: 1px solid {PALETTE['cyan_dim']};
    letter-spacing: 2px;
}}
QMenu::item:selected {{
    background-color: {PALETTE['cyan_dim']};
    color: {PALETTE['bg']};
}}

QStatusBar {{
    background-color: {PALETTE['bg']};
    color: {PALETTE['cyan_dim']};
    border-top: 1px solid {PALETTE['border']};
    letter-spacing: 2px;
    font-size: 8pt;
}}
QStatusBar::item {{ border: none; }}

QToolTip {{
    background-color: {PALETTE['bg_surface']};
    color: {PALETTE['cyan']};
    border: 1px solid {PALETTE['cyan']};
    padding: 4px 8px;
    letter-spacing: 1px;
}}
"""
