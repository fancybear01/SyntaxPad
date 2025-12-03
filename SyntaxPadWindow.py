from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QFont, QTextCursor, QKeySequence
from PyQt5.QtWidgets import (
	QAction,
	QFileDialog,
	QMainWindow,
	QMessageBox,
	QStatusBar,
	QActionGroup,
	QDockWidget,
	QTextEdit,
	QLineEdit,
	QCheckBox,
	QPushButton,
	QGridLayout,
	QWidget,
)

from CodeEditor import CodeEditor
from Theme import DARK_PALETTE, LIGHT_PALETTE, EditorPalette, Theme

class SyntaxPadWindow(QMainWindow):
	"""Main application window wrapping the code editor."""

	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("SyntaxPad")
		self.resize(900, 650)
		self._settings_path = Path.home() / ".syntaxpad.json"
		self._settings = self._load_settings()
		palette = DARK_PALETTE if self._settings.get("theme") == Theme.DARK.value else LIGHT_PALETTE

		self.editor = CodeEditor(palette)
		# Apply persisted font size if present
		self.editor.set_font_size(self._settings.get("font_size", 13))
		self.setCentralWidget(self.editor)

		self.status_bar = QStatusBar()
		self.setStatusBar(self.status_bar)

		self._init_search_dock()

		self._current_file: Optional[Path] = None
		self._create_actions()
		self._create_menu_bar()
		self._create_settings_menu()
		self._apply_global_theme(palette)

		# Применяем сохранённое состояние переноса строк
		wrap_enabled = bool(self._settings.get("word_wrap", True))
		self.editor.set_word_wrap_enabled(wrap_enabled)
		self.word_wrap_action.setChecked(wrap_enabled)

	def _init_search_dock(self) -> None:
		"""Создать док-панель поиска и замены."""
		self._search_dock = QDockWidget("Search / Replace", self)
		self._search_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)
		container = QWidget(self._search_dock)
		layout = QGridLayout(container)
		layout.setContentsMargins(4, 4, 4, 4)
		layout.setHorizontalSpacing(6)
		layout.setVerticalSpacing(4)

		self._search_edit = QLineEdit(container)
		self._replace_edit = QLineEdit(container)
		self._match_case_cb = QCheckBox("Match case", container)
		self._whole_word_cb = QCheckBox("Whole word", container)
		self._find_next_btn = QPushButton("Find next", container)
		self._find_prev_btn = QPushButton("Find previous", container)
		self._replace_btn = QPushButton("Replace", container)
		self._replace_all_btn = QPushButton("Replace all", container)

		layout.addWidget(self._search_edit, 0, 0, 1, 2)
		layout.addWidget(self._find_prev_btn, 0, 2)
		layout.addWidget(self._find_next_btn, 0, 3)
		layout.addWidget(self._replace_edit, 1, 0, 1, 2)
		layout.addWidget(self._replace_btn, 1, 2)
		layout.addWidget(self._replace_all_btn, 1, 3)
		layout.addWidget(self._match_case_cb, 2, 0)
		layout.addWidget(self._whole_word_cb, 2, 1)

		container.setLayout(layout)
		self._search_dock.setWidget(container)
		self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._search_dock)
		self._search_dock.hide()

		self._find_next_btn.clicked.connect(self._find_next)
		self._find_prev_btn.clicked.connect(lambda: self._find_next(backwards=True))
		self._replace_btn.clicked.connect(self._replace_one)
		self._replace_all_btn.clicked.connect(self._replace_all)
		self._search_edit.returnPressed.connect(self._find_next)

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

		self.run_action = QAction("&Run", self)
		self.run_action.setShortcut("F5")
		self.run_action.triggered.connect(self.run_script)

		self.stop_action = QAction("&Stop", self)
		self.stop_action.setShortcut("Shift+F5")
		self.stop_action.triggered.connect(self.stop_script)
		self.stop_action.setEnabled(False)

		# Font size actions
		self.increase_font_action = QAction("Increase Font", self)
		self.increase_font_action.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])
		self.increase_font_action.triggered.connect(lambda: self._adjust_font_size(1))

		self.decrease_font_action = QAction("Decrease Font", self)
		self.decrease_font_action.setShortcut(QKeySequence("Ctrl+-"))
		self.decrease_font_action.triggered.connect(lambda: self._adjust_font_size(-1))

		self.reset_font_action = QAction("Reset Font Size", self)
		self.reset_font_action.setShortcut(QKeySequence("Ctrl+0"))
		self.reset_font_action.triggered.connect(self._reset_font_size)

		# Search
		self.search_toggle_action = QAction("Search/Replace", self)
		self.search_toggle_action.setShortcut(QKeySequence("Ctrl+F"))
		self.search_toggle_action.triggered.connect(self._toggle_search_dock)

		# Word wrap
		self.word_wrap_action = QAction("Word Wrap", self, checkable=True)
		self.word_wrap_action.triggered.connect(self._toggle_word_wrap)

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

		view_menu = menu_bar.addMenu("&View")
		self.view_menu = view_menu
		view_menu.addAction(self.increase_font_action)
		view_menu.addAction(self.decrease_font_action)
		view_menu.addAction(self.reset_font_action)
		view_menu.addSeparator()
		view_menu.addAction(self.word_wrap_action)
		view_menu.addAction(self.search_toggle_action)

		run_menu = menu_bar.addMenu("&Run")
		run_menu.addAction(self.run_action)
		run_menu.addAction(self.stop_action)

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
		defaults = {"theme": Theme.DARK.value, "show_calltips": True, "font_size": 13, "word_wrap": True}
		if not self._settings_path.exists():
			return defaults
		try:
			with open(self._settings_path, "r", encoding="utf-8") as fh:
				data = json.load(fh)
				for k, v in defaults.items():
					data.setdefault(k, v)
				return data
		except Exception:
			return defaults

	def _save_settings(self) -> None:
		try:
			with open(self._settings_path, "w", encoding="utf-8") as fh:
				json.dump(self._settings, fh, indent=2)
		except Exception:
			pass

	def _create_settings_menu(self) -> None:
		menu_bar = self.menuBar()
		settings_menu = menu_bar.addMenu("&Settings")

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

		settings_menu.addSeparator()
		self.calltips_action = QAction("Show Calltips", self, checkable=True)
		self.calltips_action.setChecked(self._settings.get("show_calltips", True))
		self.calltips_action.toggled.connect(self._toggle_calltips)
		settings_menu.addAction(self.calltips_action)

	def _set_theme(self, theme_value: str) -> None:
		if theme_value == Theme.DARK.value:
			palette = DARK_PALETTE
		else:
			palette = LIGHT_PALETTE

		self._settings["theme"] = theme_value
		self._save_settings()
		self.editor.set_palette(palette)
		self._apply_global_theme(palette)

	def _apply_global_theme(self, palette: EditorPalette) -> None:
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

	def _adjust_font_size(self, delta: int) -> None:
		self.editor.adjust_font_size(delta)
		self._settings["font_size"] = self.editor.font().pointSize()
		self._save_settings()

	def _reset_font_size(self) -> None:
		self.editor.reset_font_size()
		self._settings["font_size"] = self.editor.font().pointSize()
		self._save_settings()

	def _toggle_search_dock(self) -> None:
		"""Показать или скрыть панель поиска/замены."""
		if self._search_dock.isVisible():
			self._search_dock.hide()
		else:
			self._search_dock.show()
			self._search_edit.setFocus()

	def _toggle_word_wrap(self, checked: bool) -> None:
		self.editor.set_word_wrap_enabled(bool(checked))
		self._settings["word_wrap"] = bool(checked)
		self._save_settings()

	def _find_next(self, backwards: bool = False) -> None:
		text = self._search_edit.text()
		case_sensitive = self._match_case_cb.isChecked()
		whole_word = self._whole_word_cb.isChecked()
		found = self.editor.find_text(text, case_sensitive=case_sensitive, whole_word=whole_word, backwards=backwards)
		if not found:
			self.status_bar.showMessage("Не найдено совпадений", 2000)

	def _replace_one(self) -> None:
		pattern = self._search_edit.text()
		replacement = self._replace_edit.text()
		case_sensitive = self._match_case_cb.isChecked()
		whole_word = self._whole_word_cb.isChecked()
		# Если текущее выделение не совпадает с шаблоном, сначала ищем
		cursor = self.editor.textCursor()
		if not cursor.hasSelection() or cursor.selectedText() != pattern:
			if not self.editor.find_text(pattern, case_sensitive=case_sensitive, whole_word=whole_word):
				self.status_bar.showMessage("Не найдено совпадений", 2000)
				return
		self.editor.replace_current(replacement)

	def _replace_all(self) -> None:
		pattern = self._search_edit.text()
		replacement = self._replace_edit.text()
		case_sensitive = self._match_case_cb.isChecked()
		whole_word = self._whole_word_cb.isChecked()
		count = self.editor.replace_all(pattern, replacement, case_sensitive=case_sensitive, whole_word=whole_word)
		self.status_bar.showMessage(f"Заменено: {count}", 3000)


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

	def closeEvent(self, event):  
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
		if self._current_file is None:
			self.save_file_as()
			if self._current_file is None:
				return
		else:
			self.save_file()

		if self._process.state() != QProcess.NotRunning:
			return  

		self._output_text.clear()
		self._output_dock.show()
		self.status_bar.showMessage("Running...")
		self.run_action.setEnabled(False)
		self.stop_action.setEnabled(True)

		env_python = sys.executable  
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
			text = text
		self._output_text.moveCursor(QTextCursor.MoveOperation.End)
		self._output_text.insertPlainText(text)
		self._output_text.moveCursor(QTextCursor.MoveOperation.End)

	def _process_finished(self) -> None:
		code = self._process.exitCode()
		self.status_bar.showMessage(f"Finished with exit code {code}")
		self.run_action.setEnabled(True)
		self.stop_action.setEnabled(False)
