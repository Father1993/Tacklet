"""Небольшие вспомогательные функции."""

import gi

gi.require_version('Gdk', '4.0')
from gi.repository import Gdk


def clamp(value, low, high):
    """Ограничивает value внутри [low, high]."""
    return max(low, min(high, value))


def rgba_from_hex(hex_color):
    """Gdk.RGBA из строки вида '#rrggbb'. При ошибке — цвет по умолчанию."""
    rgba = Gdk.RGBA()
    if not rgba.parse(str(hex_color)):
        rgba.parse('#fdf6d8')
    return rgba


def hex_from_rgba(rgba):
    """Строка '#rrggbb' из Gdk.RGBA."""
    r = int(round(rgba.red * 255))
    g = int(round(rgba.green * 255))
    b = int(round(rgba.blue * 255))
    return f'#{r:02x}{g:02x}{b:02x}'


def contrast_color(hex_color):
    """Чёрный или белый цвет текста, контрастирующий с фоном.

    Используется относительная яркость по sRGB (YC_к). Порог подобран так,
    чтобы на жёлтом (`#fdf6d8`) был чёрный текст, а на тёмных цветах — белый.
    """
    r, g, b = rgba_from_hex(hex_color).red, rgba_from_hex(hex_color).green, rgba_from_hex(hex_color).blue
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return '#1d1d1b' if luminance > 0.45 else '#f5f5f4'
