from __future__ import annotations

"""
Эти функции не зависят от Qt и могут использоваться и
тестироваться отдельно от GUI. CodeEditor делегирует им
часть работы по вычислению отступов.
"""

from typing import Final

DEFAULT_INDENT: Final[str] = "    "

def compute_newline_with_indentation(current_line_prefix: str, indent_unit: str = DEFAULT_INDENT) -> str:
    """Вернуть строку для вставки при автоотступе после Enter.
    current_line_prefix — текст от начала строки до курсора.
    """
    # Количество ведущих пробелов
    indent = len(current_line_prefix) - len(current_line_prefix.lstrip(" "))
    indent_text = " " * indent
    extra_indent = indent_unit if current_line_prefix.rstrip().endswith(":") else ""
    return "\n" + indent_text + extra_indent


def unindent_line(line: str, indent_unit: str = DEFAULT_INDENT) -> str:
    """Вернуть строку без одного уровня indent_unit в начале (если он есть)."""
    if line.startswith(indent_unit):
        return line[len(indent_unit) :]
    return line
