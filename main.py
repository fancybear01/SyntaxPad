"""SyntaxPad – a lightweight Python-focused text editor built with PyQt."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QRegularExpression
from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QSyntaxHighlighter
from PyQt5.QtWidgets import (
	QAction,
	QApplication,
	QFileDialog,
	QMainWindow,
	QMessageBox,
	QPlainTextEdit,
	QStatusBar,
)


KEYWORDS = {
	"False",
	"None",
	"True",
	"and",
	"as",
	"assert",
	"async",
	"await",
	"break",
	"class",
	"continue",
	"def",
	"del",
	"elif",
	"else",
	"except",
	"finally",
	"for",
	"from",
	"global",
	"if",
	"import",
	"in",
	"is",
	"lambda",
	"nonlocal",
	"not",
	"or",
	"pass",
	"raise",
	"return",
	"try",
	"while",
	"with",
	"yield",
}


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


class PythonHighlighter(QSyntaxHighlighter):
	"""Minimal syntax highlighter for Python code."""

	def __init__(self, document, palette: Optional[EditorPalette] = None) -> None:
		super().__init__(document)
		self.palette = palette or EditorPalette()
		self._rules = []
		self._init_rules()

	def _init_rules(self) -> None:
		def fmt(color: QColor, bold: bool = False, italic: bool = False) -> QTextCharFormat:
			char_format = QTextCharFormat()
			char_format.setForeground(color)
			if bold:
				char_format.setFontWeight(QFont.Weight.Bold)
			if italic:
				char_format.setFontItalic(True)
			return char_format

		keyword_pattern = QRegularExpression(r"\b(" + "|".join(sorted(KEYWORDS)) + r")\b")
		self._rules.append((keyword_pattern, fmt(self.palette.keyword, bold=True)))

		builtin_pattern = QRegularExpression(r"\b(__?[a-zA-Z_]+__?|print|len|range|enumerate|zip|map|filter)\b")
		self._rules.append((builtin_pattern, fmt(self.palette.builtin)))

		number_pattern = QRegularExpression(r"\b(0x[0-9a-fA-F]+|\d+(\.\d+)?)\b")
		self._rules.append((number_pattern, fmt(self.palette.number)))

		string_pattern = QRegularExpression(r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\"|'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\")")
		self._rules.append((string_pattern, fmt(self.palette.string)))

		comment_pattern = QRegularExpression(r"#[^\n]*")
		self._rules.append((comment_pattern, fmt(self.palette.comment, italic=True)))

		function_pattern = QRegularExpression(r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)")
		func_format = fmt(self.palette.function)
		func_format.setFontUnderline(True)
		self._rules.append((function_pattern, func_format))

	def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt API)
		for pattern, text_format in self._rules:
			match_iterator = pattern.globalMatch(text)
			while match_iterator.hasNext():
				match = match_iterator.next()
				start = match.capturedStart()
				length = match.capturedLength()
				if pattern.pattern().startswith("\\bdef") and match.lastCapturedIndex() >= 1:
					# Highlight only the function name capture group.
					start = match.capturedStart(1)
					length = match.capturedLength(1)
				self.setFormat(start, length, text_format)


class CodeEditor(QPlainTextEdit):
	"""Custom QPlainTextEdit with Python-friendly helpers."""

	INDENT = "    "
	BRACKETS = {"(": ")", "[": "]", "{": "}"}

	def __init__(self) -> None:
		super().__init__()
		font = QFont("Consolas", 11)
		font.setStyleHint(QFont.StyleHint.Monospace)
		self.setFont(font)
		palette = EditorPalette()
		self.setStyleSheet(
			f"QPlainTextEdit {{ background-color: {palette.background.name()}; color: {palette.foreground.name()}; }}"
		)
		self.highlighter = PythonHighlighter(self.document(), palette)
		self.cursorPositionChanged.connect(self._handle_cursor_change)

	def keyPressEvent(self, event):  # type: ignore[override]
		text = event.text()

		if text and text in self.BRACKETS:
			closing = self.BRACKETS[text]
			super().keyPressEvent(event)
			cursor = self.textCursor()
			cursor.insertText(closing)
			cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
			self.setTextCursor(cursor)
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
				return

		super().keyPressEvent(event)

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
		self.parent().update_status(block, column)  # type: ignore[call-arg]


class SyntaxPadWindow(QMainWindow):
	"""Main application window wrapping the code editor."""

	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("SyntaxPad")
		self.resize(900, 650)

		self.editor = CodeEditor()
		self.setCentralWidget(self.editor)

		self.status_bar = QStatusBar()
		self.setStatusBar(self.status_bar)

		self._current_file: Optional[Path] = None
		self._create_actions()
		self._create_menu_bar()

	def _create_actions(self) -> None:
		self.new_action = QAction("&New", self)
		self.new_action.setShortcut("Ctrl+N")
		self.new_action.triggered.connect(self.new_file)

		self.open_action = QAction("&Open…", self)
		self.open_action.setShortcut("Ctrl+O")
		self.open_action.triggered.connect(self.open_file)

		self.save_action = QAction("&Save", self)
		self.save_action.setShortcut("Ctrl+S")
		self.save_action.triggered.connect(self.save_file)

		self.save_as_action = QAction("Save &As…", self)
		self.save_as_action.setShortcut("Ctrl+Shift+S")
		self.save_as_action.triggered.connect(self.save_file_as)

		self.exit_action = QAction("E&xit", self)
		self.exit_action.setShortcut("Ctrl+Q")
		self.exit_action.triggered.connect(self.close)

	def _create_menu_bar(self) -> None:
		menu_bar = self.menuBar()
		file_menu = menu_bar.addMenu("&File")
		file_menu.addAction(self.new_action)
		file_menu.addAction(self.open_action)
		file_menu.addSeparator()
		file_menu.addAction(self.save_action)
		file_menu.addAction(self.save_as_action)
		file_menu.addSeparator()
		file_menu.addAction(self.exit_action)

	def new_file(self) -> None:
		if not self._maybe_discard_changes():
			return
		self.editor.clear()
		self._current_file = None
		self._update_window_title()

	def open_file(self) -> None:
		if not self._maybe_discard_changes():
			return
		file_path, _ = QFileDialog.getOpenFileName(self, "Open File", str(Path.home()), "Python Files (*.py);;All Files (*.*)")
		if file_path:
			with open(file_path, "r", encoding="utf-8") as fh:
				self.editor.setPlainText(fh.read())
			self._current_file = Path(file_path)
			self._update_window_title()

	def save_file(self) -> None:
		if self._current_file is None:
			self.save_file_as()
			return
		self._write_to_path(self._current_file)

	def save_file_as(self) -> None:
		file_path, _ = QFileDialog.getSaveFileName(self, "Save File As", str(Path.home()), "Python Files (*.py);;All Files (*.*)")
		if file_path:
			self._current_file = Path(file_path)
			self._write_to_path(self._current_file)
			self._update_window_title()

	def closeEvent(self, event):  # type: ignore[override]
		if self._maybe_discard_changes():
			event.accept()
		else:
			event.ignore()

	def update_status(self, line: int, column: int) -> None:
		path = str(self._current_file) if self._current_file else "Untitled"
		self.status_bar.showMessage(f"{path} — Line {line}, Column {column}")

	def _maybe_discard_changes(self) -> bool:
		if not self.editor.document().isModified():
			return True
		response = QMessageBox.warning(
			self,
			"Unsaved Changes",
			"The document has unsaved changes. Do you want to continue without saving?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No,
		)
		return response == QMessageBox.StandardButton.Yes

	def _write_to_path(self, path: Path) -> None:
		with open(path, "w", encoding="utf-8") as fh:
			fh.write(self.editor.toPlainText())
		self.editor.document().setModified(False)

	def _update_window_title(self) -> None:
		suffix = f" — {self._current_file.name}" if self._current_file else ""
		self.setWindowTitle(f"SyntaxPad{suffix}")


def run() -> None:
	app = QApplication(sys.argv)
	window = SyntaxPadWindow()
	window.show()
	sys.exit(app.exec_())


if __name__ == "__main__":
	run()