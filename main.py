"""SyntaxPad – a lightweight Python-focused text editor built with PyQt."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import inspect
import builtins
from typing import Optional

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


def get_builtin_calltip(name: str) -> Optional[str]:
	"""Return a simple calltip for a builtin by name: signature + first doc line.

	If the symbol isn't a builtin or isn't callable, returns None.
	"""
	obj = getattr(builtins, name, None)
	if obj is None or not callable(obj):
		return None
	# Try to get a signature; some builtins may not expose it
	try:
		sig = str(inspect.signature(obj))
	except (ValueError, TypeError):
		sig = "(…)"
	# Get the first line of the docstring
	doc = getattr(obj, "__doc__", None) or ""
	first = doc.strip().splitlines()[0] if doc else ""
	return f"{name}{sig}\n{first}".strip()


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


# Predefined palettes for light and dark themes. Keep them simple and readable.
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

	def __init__(self, palette: Optional[EditorPalette] = None) -> None:
		super().__init__()
		font = QFont("Consolas", 11)
		font.setStyleHint(QFont.StyleHint.Monospace)
		self.setFont(font)
		self._palette = palette or EditorPalette()
		self._apply_palette()
		self.highlighter = PythonHighlighter(self.document(), self._palette)
		self.cursorPositionChanged.connect(self._handle_cursor_change)

		# Auto-hide timer for calltips
		self._calltip_timer = QTimer(self)
		self._calltip_timer.setSingleShot(True)
		self._calltip_timer.timeout.connect(QToolTip.hideText)

	def _apply_palette(self) -> None:
		p = self._palette
		self.setStyleSheet(
			f"QPlainTextEdit {{ background-color: {p.background.name()}; color: {p.foreground.name()}; }}"
		)

	def set_palette(self, palette: EditorPalette) -> None:
		self._palette = palette
		self._apply_palette()
		if hasattr(self, "highlighter"):
			self.highlighter.palette = palette
			self.highlighter.rehighlight()

	def keyPressEvent(self, event):  # type: ignore[override]
		text = event.text()

		# Manual trigger: Ctrl+Shift+Space shows calltip for symbol at cursor
		mods = event.modifiers()
		if event.key() == Qt.Key.Key_Space and (mods & Qt.KeyboardModifier.ControlModifier) and (mods & Qt.KeyboardModifier.ShiftModifier):
			self._try_show_calltip_at_cursor()
			return

		# Hide calltip on Escape or when committing a line
		if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
			QToolTip.hideText()
			# For Enter we still want to process indentation below, so don't return here for Enter
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

		# If user typed '(', try to show a calltip for the preceding identifier
		if text == "(":
			self._try_show_calltip_before_paren()
			# Continue with normal handling so the '(' appears

		super().keyPressEvent(event)

	def _word_before_cursor(self) -> Optional[str]:
		cursor = self.textCursor()
		block_text = cursor.block().text()
		pos = cursor.positionInBlock()
		before = block_text[:pos]
		# Extract trailing identifier
		import re
		m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)$", before)
		return m.group(1) if m else None

	def _try_show_calltip_at_cursor(self) -> None:
		name = self._word_before_cursor()
		if not name:
			return
		# Check settings flag from parent window, default True if missing
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
			# Start/restart auto-hide timer (default 2500ms, configurable in settings)
			duration = 2500
			parent = self.parent()
			if parent is not None and hasattr(parent, "_settings"):
				duration = int(parent._settings.get("calltip_timeout_ms", duration))
			self._calltip_timer.start(max(500, duration))

	def _try_show_calltip_before_paren(self) -> None:
		# When '(' is typed, cursor is after '(', so check word before it
		cursor = self.textCursor()
		cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
		self.setTextCursor(cursor)
		try:
			self._try_show_calltip_at_cursor()
		finally:
			# Restore cursor (move back after '(')
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
		self.parent().update_status(block, column)  # type: ignore[call-arg]


class SyntaxPadWindow(QMainWindow):
	"""Main application window wrapping the code editor."""

	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("SyntaxPad")
		self.resize(900, 650)
		# Load settings first so theme choice can be applied to the editor instance.
		self._settings_path = Path.home() / ".syntaxpad.json"
		self._settings = self._load_settings()
		palette = DARK_PALETTE if self._settings.get("theme") == Theme.DARK.value else LIGHT_PALETTE

		self.editor = CodeEditor(palette)
		self.setCentralWidget(self.editor)

		self.status_bar = QStatusBar()
		self.setStatusBar(self.status_bar)

		self._current_file: Optional[Path] = None
		self._create_actions()
		self._create_menu_bar()
		self._create_settings_menu()
		self._apply_global_theme(palette)

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

		# Run actions
		self.run_action = QAction("&Run", self)
		self.run_action.setShortcut("F5")
		self.run_action.triggered.connect(self.run_script)

		self.stop_action = QAction("&Stop", self)
		self.stop_action.setShortcut("Shift+F5")
		self.stop_action.triggered.connect(self.stop_script)
		self.stop_action.setEnabled(False)

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

		# View menu placeholder for future panes
		view_menu = menu_bar.addMenu("&View")
		self.view_menu = view_menu

		# Run menu
		run_menu = menu_bar.addMenu("&Run")
		run_menu.addAction(self.run_action)
		run_menu.addAction(self.stop_action)

		# Initialize process and output dock
		self._process = QProcess(self)
		self._process.readyReadStandardOutput.connect(self._read_stdout)
		self._process.readyReadStandardError.connect(self._read_stderr)
		self._process.finished.connect(self._process_finished)

		self._output_dock = QDockWidget("Output", self)
		self._output_text = QTextEdit(self._output_dock)
		self._output_text.setReadOnly(True)
		self._output_text.setFont(QFont("Consolas", 10))
		self._output_dock.setWidget(self._output_text)
		self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._output_dock)
		self._output_dock.hide()

	def _load_settings(self) -> dict:
		"""Load settings from disk. Returns a dict with at least 'theme'."""
		if not self._settings_path.exists():
			return {"theme": Theme.DARK.value}
		try:
			with open(self._settings_path, "r", encoding="utf-8") as fh:
				return json.load(fh)
		except Exception:
			# If parsing fails, fall back to defaults.
			return {"theme": Theme.DARK.value}

	def _save_settings(self) -> None:
		try:
			with open(self._settings_path, "w", encoding="utf-8") as fh:
				json.dump(self._settings, fh, indent=2)
		except Exception:
			# Ignore write errors for now; desktop app shouldn't crash.
			pass

	def _create_settings_menu(self) -> None:
		menu_bar = self.menuBar()
		settings_menu = menu_bar.addMenu("&Settings")

		# Theme submenu with exclusive choices
		theme_menu = settings_menu.addMenu("Theme")
		action_group = QActionGroup(self)
		action_group.setExclusive(True)

		self.dark_theme_action = QAction("Dark", self, checkable=True)
		self.light_theme_action = QAction("Light", self, checkable=True)
		action_group.addAction(self.dark_theme_action)
		action_group.addAction(self.light_theme_action)

		theme_menu.addAction(self.dark_theme_action)
		theme_menu.addAction(self.light_theme_action)

		current = self._settings.get("theme", Theme.DARK.value)
		self.dark_theme_action.setChecked(current == Theme.DARK.value)
		self.light_theme_action.setChecked(current == Theme.LIGHT.value)

		self.dark_theme_action.triggered.connect(lambda: self._set_theme(Theme.DARK.value))
		self.light_theme_action.triggered.connect(lambda: self._set_theme(Theme.LIGHT.value))

		# Toggle for calltips
		settings_menu.addSeparator()
		self.calltips_action = QAction("Show Calltips", self, checkable=True)
		self.calltips_action.setChecked(self._settings.get("show_calltips", True))
		self.calltips_action.toggled.connect(self._toggle_calltips)
		settings_menu.addAction(self.calltips_action)

	def _set_theme(self, theme_value: str) -> None:
		"""Apply a theme value ('dark' or 'light') and persist settings."""
		if theme_value == Theme.DARK.value:
			palette = DARK_PALETTE
		else:
			palette = LIGHT_PALETTE

		self._settings["theme"] = theme_value
		self._save_settings()
		# Update editor and highlighter
		self.editor.set_palette(palette)
		self._apply_global_theme(palette)

	def _apply_global_theme(self, palette: EditorPalette) -> None:
		"""Apply stylesheet to non-editor UI elements (menus, status bar, dock)."""
		bg = palette.background.name()
		fg = palette.foreground.name()
		accent = palette.keyword.name()
		stylesheet = f"""
QMainWindow {{ background-color: {bg}; }}
QMenuBar {{ background-color: {bg}; color: {fg}; }}
QMenuBar::item:selected {{ background: {accent}; }}
QMenu {{ background-color: {bg}; color: {fg}; }}
QMenu::item:selected {{ background: {accent}; }}
QStatusBar {{ background-color: {bg}; color: {fg}; }}
QDockWidget {{ background-color: {bg}; color: {fg}; }}
QDockWidget::title {{ background: {bg}; color: {fg}; padding-left: 4px; }}
QTextEdit {{ background-color: {bg}; color: {fg}; }}
"""
		self.setStyleSheet(stylesheet)

	def _toggle_calltips(self, enabled: bool) -> None:
		self._settings["show_calltips"] = bool(enabled)
		self._save_settings()


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

	def run_script(self) -> None:
		"""Run current script (or unsaved buffer) using the current Python executable."""
		# Auto-save if file path exists or ask for path first
		if self._current_file is None:
			# Prompt save-as before running
			self.save_file_as()
			if self._current_file is None:
				return
		else:
			self.save_file()

		if self._process.state() != QProcess.NotRunning:
			return  # Already running

		self._output_text.clear()
		self._output_dock.show()
		self.status_bar.showMessage("Running...")
		self.run_action.setEnabled(False)
		self.stop_action.setEnabled(True)

		env_python = sys.executable  # Use the same interpreter
		self._process.setProgram(env_python)
		self._process.setArguments([str(self._current_file)])
		self._process.start()

	def stop_script(self) -> None:
		if self._process.state() != QProcess.NotRunning:
			self._process.kill()
			self.status_bar.showMessage("Process terminated")

	def _read_stdout(self) -> None:
		data = bytes(self._process.readAllStandardOutput()).decode(errors="replace")
		self._append_output(data)

	def _read_stderr(self) -> None:
		data = bytes(self._process.readAllStandardError()).decode(errors="replace")
		self._append_output(data, error=True)

	def _append_output(self, text: str, error: bool = False) -> None:
		if error:
			# Simple styling: prefix errors
			text = text
		self._output_text.moveCursor(QTextCursor.MoveOperation.End)
		self._output_text.insertPlainText(text)
		self._output_text.moveCursor(QTextCursor.MoveOperation.End)

	def _process_finished(self) -> None:
		code = self._process.exitCode()
		self.status_bar.showMessage(f"Finished with exit code {code}")
		self.run_action.setEnabled(True)
		self.stop_action.setEnabled(False)


def run() -> None:
	app = QApplication(sys.argv)
	window = SyntaxPadWindow()
	window.show()
	sys.exit(app.exec_())


if __name__ == "__main__":
	run()