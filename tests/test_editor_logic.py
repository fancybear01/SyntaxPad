from EditorLogic import compute_newline_with_indentation, unindent_line, DEFAULT_INDENT


def test_auto_indent_without_colon():
    prefix = """    x = 1"""
    result = compute_newline_with_indentation(prefix, DEFAULT_INDENT)
    # Ожидаем перенос строки и тот же базовый отступ
    assert result == "\n" + " " * 4


def test_auto_indent_after_colon():
    prefix = """    if True:"""
    result = compute_newline_with_indentation(prefix, DEFAULT_INDENT)
    # Базовый отступ + один уровень indent_unit
    assert result == "\n" + " " * 8


def test_unindent_line_removes_one_level():
    line = """    x = 1"""
    assert unindent_line(line, DEFAULT_INDENT) == "x = 1"


def test_unindent_line_without_indent_keeps_text():
    line = "x = 1"
    assert unindent_line(line, DEFAULT_INDENT) == line
