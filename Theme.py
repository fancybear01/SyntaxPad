from dataclasses import dataclass
from enum import Enum
from PyQt5.QtGui import QColor

@dataclass
class EditorPalette:
	# Базовые цвета по умолчанию (мягкая тёмная схема, One Dark-подобная)
	background: QColor = QColor("#282c34")
	foreground: QColor = QColor("#abb2bf")
	keyword: QColor = QColor("#c678dd")
	builtin: QColor = QColor("#61afef")
	comment: QColor = QColor("#5c6370")
	string: QColor = QColor("#98c379")
	number: QColor = QColor("#d19a66")
	function: QColor = QColor("#e5c07b")


class Theme(str, Enum):
	DARK = "dark"
	LIGHT = "light"



# Мягкая светлая палитра
LIGHT_PALETTE = EditorPalette(
	background=QColor("#fafafa"),
	foreground=QColor("#383a42"),
	keyword=QColor("#a626a4"),
	builtin=QColor("#0184bc"),
	comment=QColor("#6a737d"),
	string=QColor("#50a14f"),
	number=QColor("#986801"),
	function=QColor("#795da3"),
)

# Тёмная палитра по умолчанию (см. значения в EditorPalette)
DARK_PALETTE = EditorPalette()
