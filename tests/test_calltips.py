import builtins

import pytest

from Calltips import get_builtin_calltip


@pytest.mark.parametrize("name", ["len", "print", "range"])
def test_get_builtin_calltip_known_builtin_returns_text(name: str) -> None:
    """Для известных встроенных функций должна возвращаться непустая подсказка."""
    tip = get_builtin_calltip(name)
    assert tip is not None
    assert isinstance(tip, str)
    # Подсказка начинается с имени функции и содержит скобки
    assert tip.startswith(name)
    assert "(" in tip and ")" in tip


def test_get_builtin_calltip_unknown_name_returns_none() -> None:
    """Для несуществующего имени подсказка не формируется."""
    tip = get_builtin_calltip("definitely_no_such_builtin_function")
    assert tip is None


def test_get_builtin_calltip_non_callable_returns_none() -> None:
    """Если имя ссылается на невызываемый объект, функция возвращает None."""
    # Например, встроенная константа __spec__ или другое поле модуля
    non_callable_name = "__spec__" if hasattr(builtins, "__spec__") else "__doc__"
    tip = get_builtin_calltip(non_callable_name)
    assert tip is None
