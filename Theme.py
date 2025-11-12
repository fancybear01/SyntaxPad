from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import Qt, QRegularExpression, QTimer, QProcess
from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QSyntaxHighlighter
from PyQt5.QtWidgets import (
	QAction,
	QApplication,
	QFileDialog,
	QMainWindow,
	QMessageBox,
	QPlainTextEdit,
	QStatusBar,
	QActionGroup,
    QToolTip,
    QDockWidget,
    QTextEdit,
)

@dataclass
class EditorPalette:
	background: QColor = QColor("#1e1e1e")
	foreground: QColor = QColor("#d4d4d4")
	keyword: QColor = QColor("#569cd6")
	builtin: QColor = QColor("#4ec9b0")
	comment: QColor = QColor("#6a9955")
	string: QColor = QColor("#ce9178")
	number: QColor = QColor("#b5cea8")
	function: QColor = QColor("#dcdcaa")


class Theme(str, Enum):
	DARK = "dark"
	LIGHT = "light"


LIGHT_PALETTE = EditorPalette(
	background=QColor("#ffffff"),
	foreground=QColor("#24292e"),
	keyword=QColor("#0000ff"),
	builtin=QColor("#795e26"),
	comment=QColor("#008000"),
	string=QColor("#a31515"),
	number=QColor("#098658"),
	function=QColor("#001080"),
)

DARK_PALETTE = EditorPalette()
