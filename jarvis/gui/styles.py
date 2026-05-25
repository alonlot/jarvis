"""Global QSS stylesheet — dark theme with cyan Jarvis accents."""

JARVIS_QSS = """
* {
    color: #c9d1d9;
    font-family: "Segoe UI", "SF Pro Text", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 11pt;
}

QMainWindow, QWidget#mainCentral {
    background-color: #0d1117;
}

QWidget#sidebar {
    background-color: #010409;
    border-right: 1px solid #21262d;
}

QLabel#brand {
    color: #c9d1d9;
    font-size: 13pt;
    font-weight: 500;
    letter-spacing: 0.5px;
    padding: 0;
}

QPushButton#navBtn {
    background-color: transparent;
    color: #8b949e;
    border: none;
    border-left: 2px solid transparent;
    padding: 11px 22px;
    text-align: left;
    font-size: 11pt;
}
QPushButton#navBtn:hover {
    color: #c9d1d9;
}
QPushButton#navBtn:checked {
    background-color: #0d1117;
    color: #58a6ff;
    border-left: 2px solid #58a6ff;
}

QWidget#headerArea {
    background-color: #0d1117;
}
QLabel#stateLabel {
    color: #6e7681;
    font-size: 10pt;
    letter-spacing: 1.5px;
}

QLabel#emptyTitle {
    color: #c9d1d9;
    font-size: 16pt;
    font-weight: 400;
    letter-spacing: 0.3px;
}
QLabel#emptyHint {
    color: #6e7681;
    font-size: 10pt;
}

QScrollArea, QScrollArea > QWidget > QWidget {
    background-color: #0d1117;
    border: none;
}
QScrollBar:vertical {
    background: #0d1117;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #484f58; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QFrame#bubbleUser {
    background-color: #1f6feb;
    color: #ffffff;
    border-radius: 14px;
    padding: 10px 14px;
}
QFrame#bubbleAssistant {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 14px;
    padding: 10px 14px;
}
QLabel#bubbleText { background: transparent; }
QLabel#bubbleMeta {
    color: #6e7681;
    font-size: 9pt;
    padding: 2px 6px;
}

QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 12px;
    selection-background-color: #1f6feb;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #58a6ff;
}
QLineEdit#chatInput {
    font-size: 11pt;
    padding: 12px 14px;
}

QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 16px;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #58a6ff;
}
QPushButton:disabled {
    color: #484f58;
    background-color: #161b22;
}
QPushButton#primary {
    background-color: #238636;
    border: 1px solid #2ea043;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#primary:hover { background-color: #2ea043; }
QPushButton#micBtn {
    background-color: transparent;
    border: 1px solid #30363d;
    border-radius: 22px;
    min-width: 44px;
    min-height: 44px;
    font-size: 16pt;
}
QPushButton#micBtn:hover { border-color: #58a6ff; color: #58a6ff; }

QTabWidget::pane {
    border: 1px solid #21262d;
    border-radius: 6px;
    background-color: #0d1117;
    top: -1px;
}
QTabBar::tab {
    background-color: #0d1117;
    color: #8b949e;
    padding: 8px 16px;
    border: 1px solid transparent;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    color: #c9d1d9;
    background-color: #161b22;
    border-color: #21262d;
}
QTabBar::tab:hover:!selected { color: #c9d1d9; }

QGroupBox {
    border: 1px solid #21262d;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 12px;
    color: #8b949e;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #58a6ff;
}

QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #58a6ff;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
}

QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #30363d;
    border-radius: 3px;
    background-color: #0d1117;
}
QCheckBox::indicator:checked { background-color: #238636; border-color: #2ea043; }

QTableWidget {
    background-color: #0d1117;
    gridline-color: #21262d;
    border: 1px solid #21262d;
    border-radius: 6px;
    selection-background-color: #1f6feb;
}
QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #21262d;
    border-right: 1px solid #21262d;
}

QMenuBar, QMenu {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #21262d;
}
QMenu::item:selected, QMenuBar::item:selected { background-color: #1f6feb; }

QStatusBar { background-color: #010409; color: #8b949e; }
QStatusBar::item { border: none; }
"""
