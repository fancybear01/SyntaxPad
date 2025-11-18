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
	# Базовые цвета по умолчанию (тёмная тема)
	background: QColor = QColor("#0d1117")
	foreground: QColor = QColor("#c9d1d9")
	keyword: QColor = QColor("#79c0ff")
	builtin: QColor = QColor("#d2a8ff")
	comment: QColor = QColor("#8b949e")
	string: QColor = QColor("#7ee787")
	number: QColor = QColor("#ffa657")
	function: QColor = QColor("#d2a8ff")


class Theme(str, Enum):
	DARK = "dark"
	LIGHT = "light"


LIGHT_PALETTE = EditorPalette(
	background=QColor("#ffffff"),
	foreground=QColor("#24292f"),
	keyword=QColor("#0550ae"),
	builtin=QColor("#8250df"),
	comment=QColor("#6e7781"),
	string=QColor("#a31515"),
	number=QColor("#116329"),
	function=QColor("#953800"),
)

# Тёмная палитра по умолчанию (см. значения в EditorPalette)
DARK_PALETTE = EditorPalette()
