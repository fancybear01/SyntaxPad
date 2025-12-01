import sys

from PyQt5.QtWidgets import QApplication

from CodeEditor import CodeEditor
from Theme import EditorPalette


def _get_app() -> QApplication:
    """Создаёт (или возвращает уже созданный) экземпляр QApplication для тестов."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_codeeditor_font_size_changes_and_affects_line_number_width() -> None:
    """Изменение размера шрифта должно менять ширину области номеров строк."""
    _get_app()
    editor = CodeEditor(EditorPalette())

    initial_width = editor.lineNumberAreaWidth()
    initial_size = editor.font().pointSize()

    editor.set_font_size(initial_size + 4)
    increased_width = editor.lineNumberAreaWidth()

    assert increased_width > initial_width


def test_codeeditor_reset_font_restores_default_size() -> None:
    """Сброс размера шрифта возвращает его к значению по умолчанию."""
    _get_app()
    editor = CodeEditor(EditorPalette())

    default_size = editor.font().pointSize()
    editor.set_font_size(default_size + 5)
    assert editor.font().pointSize() == default_size + 5

    editor.reset_font_size()
    assert editor.font().pointSize() == default_size
