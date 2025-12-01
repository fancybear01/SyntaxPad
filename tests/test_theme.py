from Theme import LIGHT_PALETTE, DARK_PALETTE


def test_palettes_have_different_backgrounds() -> None:
    """Светлая и тёмная темы должны отличаться по фоновому цвету."""
    assert LIGHT_PALETTE.background != DARK_PALETTE.background


def test_palettes_have_basic_roles_filled() -> None:
    """В палитрах должны быть заданы ключевые роли цветов."""
    for palette in (LIGHT_PALETTE, DARK_PALETTE):
        assert palette.foreground is not None
        assert palette.background is not None
        assert palette.keyword is not None
        assert palette.string is not None
        assert palette.comment is not None
        assert palette.number is not None
        assert palette.builtin is not None
        assert palette.function is not None
