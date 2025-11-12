"""Calltip utilities for SyntaxPad."""
import inspect
import builtins
from typing import Optional


def get_builtin_calltip(name: str) -> Optional[str]:
    """Return a minimal calltip (signature + first doc line) for a builtin name."""
    obj = getattr(builtins, name, None)
    if obj is None or not callable(obj):
        return None
    try:
        sig = str(inspect.signature(obj))
    except (ValueError, TypeError):
        sig = "(…)"
    doc = getattr(obj, "__doc__", None) or ""
    first = doc.strip().splitlines()[0] if doc else ""
    return f"{name}{sig}\n{first}".strip() if first else f"{name}{sig}".strip()
