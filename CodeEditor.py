from typing import Optional

from PyQt5.QtCore import Qt, QTimer, QRect, QSize
from PyQt5.QtGui import QFont, QTextCursor, QPainter, QWheelEvent
from PyQt5.QtWidgets import QPlainTextEdit, QToolTip, QWidget

from PythonHighlighter import PythonHighlighter
from Theme import EditorPalette
from Calltips import get_builtin_calltip

class CodeEditor(QPlainTextEdit):
	"""QPlainTextEdit with Python helpers."""

	INDENT = "    "
	BRACKETS = {"(": ")", "[": "]", "{": "}"}

	def __init__(self, palette: Optional[EditorPalette] = None) -> None:
		super().__init__()
		font = QFont("Consolas", 11)
		font.setStyleHint(QFont.StyleHint.Monospace)
		self.setFont(font)
		self._default_font_size = font.pointSize()
		self._palette = palette or EditorPalette()
		self._apply_palette()
		self.highlighter = PythonHighlighter(self.document(), self._palette)
		self.cursorPositionChanged.connect(self._handle_cursor_change)

		# Line number area setup
		self._lineNumberArea = _LineNumberArea(self)
		self.blockCountChanged.connect(self._update_line_number_area_width)
		self.updateRequest.connect(self._update_line_number_area)
		self._update_line_number_area_width(0)

		self._calltip_timer = QTimer(self)
		self._calltip_timer.setSingleShot(True)
		self._calltip_timer.timeout.connect(QToolTip.hideText)

	def _apply_palette(self) -> None:
		p = self._palette
		self.setStyleSheet(
			f"QPlainTextEdit {{ background-color: {p.background.name()}; color: {p.foreground.name()}; }}"
		)
		if hasattr(self, "_lineNumberArea"):
			self._lineNumberArea.update()

	def set_font_size(self, size: int) -> None:
		"""Set absolute font size (clamped)."""
		size = max(6, min(72, int(size)))
		font = self.font()
		if font.pointSize() == size:
			return
		font.setPointSize(size)
		self.setFont(font)
		self._update_line_number_area_width(0)

	def adjust_font_size(self, delta: int) -> None:
		"""Adjust current font size by delta."""
		self.set_font_size(self.font().pointSize() + delta)

	def reset_font_size(self) -> None:
		"""Reset font size to default captured at init."""
		self.set_font_size(self._default_font_size)

	def set_palette(self, palette: EditorPalette) -> None:
		self._palette = palette
		self._apply_palette()
		if hasattr(self, "highlighter"):
			self.highlighter.palette = palette
			self.highlighter.rehighlight()
		self._update_line_number_area_width(0)

	def lineNumberAreaWidth(self) -> int:
		"""Return width of line number area in pixels.

		Используем метрики шрифта редактора и небольшой запас,
		чтобы при увеличении шрифта цифры не налезали на текст.
		"""
		digits = len(str(max(1, self.blockCount())))
		fm = self.fontMetrics()
		char_width = fm.horizontalAdvance('9')
		padding = 8  # слева/справа
		return padding + char_width * digits

	def _update_line_number_area_width(self, _):
		self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

	def _update_line_number_area(self, rect, dy):
		if dy:
			self._lineNumberArea.scroll(0, dy)
		else:
			self._lineNumberArea.update(0, rect.y(), self._lineNumberArea.width(), rect.height())
		if rect.contains(self.viewport().rect()):
			self._update_line_number_area_width(0)

	def resizeEvent(self, event):  # type: ignore[override]
		super().resizeEvent(event)
		r = QRect(0, 0, self.lineNumberAreaWidth(), self.height())
		self._lineNumberArea.setGeometry(r)

	def wheelEvent(self, event: QWheelEvent):  # type: ignore[override]
		# Ctrl + колёсико — масштаб шрифта
		if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
			angle = event.angleDelta().y()
			if angle == 0:
				return
			step = 1 if angle > 0 else -1
			self.adjust_font_size(step)
			event.accept()
			return

		# Обычная прокрутка
		super().wheelEvent(event)

	def _lineNumberAreaPaintEvent(self, event) -> None:
		painter = QPainter(self._lineNumberArea)
		painter.setFont(self.font())
		# Background
		bg = self._palette.background
		painter.fillRect(event.rect(), bg)
		# Правая белая граница между гаттером и текстом
		painter.setPen(Qt.GlobalColor.white)
		x = self._lineNumberArea.width() - 1
		painter.drawLine(x, event.rect().top(), x, event.rect().bottom())

		# Numbers
		block = self.firstVisibleBlock()
		block_number = block.blockNumber()
		top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
		bottom = top + int(self.blockBoundingRect(block).height())

		pen_color = self._palette.comment if hasattr(self._palette, 'comment') else self._palette.foreground
		painter.setPen(pen_color)

		while block.isValid() and top <= event.rect().bottom():
			if block.isVisible() and bottom >= event.rect().top():
				num = str(block_number + 1)
				painter.drawText(0, top, self._lineNumberArea.width() - 4, self.fontMetrics().height(),
							   Qt.AlignmentFlag.AlignRight, num)
			block = block.next()
			block_number += 1
			top = bottom
			bottom = top + int(self.blockBoundingRect(block).height())

	def keyPressEvent(self, event):  
		text = event.text()

		mods = event.modifiers()
		if event.key() == Qt.Key.Key_Space and (mods & Qt.KeyboardModifier.ControlModifier) and (mods & Qt.KeyboardModifier.ShiftModifier):
			self._try_show_calltip_at_cursor()
			return

		if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
			QToolTip.hideText()
			if event.key() == Qt.Key.Key_Escape:
				return

		if text and text in self.BRACKETS:
			closing = self.BRACKETS[text]
			super().keyPressEvent(event)
			cursor = self.textCursor()
			cursor.insertText(closing)
			cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
			self.setTextCursor(cursor)
			if text == "(":
				self._try_show_calltip_before_paren()
			return

		if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
			self._insert_auto_indentation()
			return

		if event.key() == Qt.Key.Key_Tab:
			self.textCursor().insertText(self.INDENT)
			return

		if event.key() == Qt.Key.Key_Backtab:
			self._unindent_selection()
			return

		if text and text in self.BRACKETS.values():
			cursor = self.textCursor()
			if cursor.hasSelection():
				super().keyPressEvent(event)
				return
			next_char_cursor = QTextCursor(cursor)
			next_char_cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
			next_char = next_char_cursor.document().characterAt(next_char_cursor.position() - 1)
			if next_char == text:
				cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
				self.setTextCursor(cursor)
				if text == ")":
					QToolTip.hideText()
				return

		if text == "(":
			self._try_show_calltip_before_paren()

		super().keyPressEvent(event)

	def _word_before_cursor(self) -> Optional[str]:
		cursor = self.textCursor()
		block_text = cursor.block().text()
		pos = cursor.positionInBlock()
		before = block_text[:pos]
		import re
		m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)$", before)
		return m.group(1) if m else None

	def _try_show_calltip_at_cursor(self) -> None:
		name = self._word_before_cursor()
		if not name:
			return
		parent = self.parent()
		show = True
		if parent is not None and hasattr(parent, "_settings"):
			show = parent._settings.get("show_calltips", True)
		if not show:
			return
		text = get_builtin_calltip(name)
		if text:
			pt = self.cursorRect().bottomLeft()
			QToolTip.showText(self.mapToGlobal(pt), text, self)
			duration = 2500
			parent = self.parent()
			if parent is not None and hasattr(parent, "_settings"):
				duration = int(parent._settings.get("calltip_timeout_ms", duration))
			self._calltip_timer.start(max(500, duration))

	def _try_show_calltip_before_paren(self) -> None:
		cursor = self.textCursor()
		cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
		self.setTextCursor(cursor)
		try:
			self._try_show_calltip_at_cursor()
		finally:
			cursor = self.textCursor()
			cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
			self.setTextCursor(cursor)

	def _insert_auto_indentation(self) -> None:
		cursor = self.textCursor()
		cursor.beginEditBlock()

		current_block = cursor.block()
		current_text = current_block.text()[: cursor.positionInBlock()]
		indent = len(current_text) - len(current_text.lstrip())
		indent_text = " " * indent

		extra_indent = self.INDENT if current_text.rstrip().endswith(":") else ""

		cursor.removeSelectedText()
		cursor.insertText("\n" + indent_text + extra_indent)
		cursor.endEditBlock()
		self.setTextCursor(cursor)

	def _unindent_selection(self) -> None:
		cursor = self.textCursor()
		cursor.beginEditBlock()
		if cursor.hasSelection():
			start = cursor.selectionStart()
			end = cursor.selectionEnd()
			cursor.setPosition(start)
			while cursor.position() < end:
				cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
				if cursor.block().text().startswith(self.INDENT):
					cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, len(self.INDENT))
					cursor.removeSelectedText()
				cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
				end = cursor.selectionEnd()
		else:
			cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
			if cursor.block().text().startswith(self.INDENT):
				cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, len(self.INDENT))
				cursor.removeSelectedText()

		cursor.endEditBlock()
		self.setTextCursor(cursor)

	def _handle_cursor_change(self) -> None:
		cursor = self.textCursor()
		block = cursor.blockNumber() + 1
		column = cursor.positionInBlock() + 1
		self.parent().update_status(block, column)  
		# Update line number area for current line highlight (repaint small area)
		self._lineNumberArea.update()


class _LineNumberArea(QWidget):
	def __init__(self, editor: CodeEditor) -> None:
		super().__init__(editor)
		self._editor = editor

	def sizeHint(self):
		return QSize(self._editor.lineNumberAreaWidth(), 0)

	def paintEvent(self, event):  # type: ignore[override]
		self._editor._lineNumberAreaPaintEvent(event)