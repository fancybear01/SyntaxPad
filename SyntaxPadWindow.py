from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import (
	QAction,
	QFileDialog,
	QMainWindow,
	QMessageBox,
	QStatusBar,
	QActionGroup,
    QDockWidget,
    QTextEdit,
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

		view_menu = menu_bar.addMenu("&View")
		self.view_menu = view_menu

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
		if not self._settings_path.exists():
			return {"theme": Theme.DARK.value}
		try:
			with open(self._settings_path, "r", encoding="utf-8") as fh:
				return json.load(fh)
		except Exception:
			return {"theme": Theme.DARK.value}

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
