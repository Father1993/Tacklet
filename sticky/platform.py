"""Работа с геометрией окон.

GNOME / Wayland не позволяет приложению задавать позицию окна (протокол
xdg-shell оставляет это композитору), поэтому «родные» окна открываются там,
где решит композитор. Чтобы позиции заметок действительно сохранялись между
запусками, окна можно запустить через XWayland (--x11): в этом случае
геометрию читаем/пишем утилитой xdotool напрямую к X-окну.

На родном Wayland-бэкенде всегда сохраняется как минимум размер окна.
"""

import os
import shutil
import subprocess


def is_x11():
    """True, если приложение запущено с бэкендом GDK_BACKEND=x11 (XWayland)."""
    return os.environ.get('GDK_BACKEND', '') == 'x11'


def supports_geometry():
    """True, когда можно управлять точной позицией окна."""
    return is_x11() and shutil.which('xdotool') is not None and bool(os.environ.get('DISPLAY'))


def _xid(win):
    """X-идентификатор окна (только для X11/XWayland окна), либо None."""
    try:
        surface = win.get_surface()
        if surface is None:
            return None
        get_xid = getattr(surface, 'get_xid', None)
        return get_xid() if get_xid else None
    except Exception:
        return None


def _run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=4)
    except Exception:
        return None


def move(win, x, y):
    """Перемещает окно в точку (x, y). True при успехе."""
    wid = _xid(win)
    if wid is None:
        return False
    result = _run(['xdotool', 'windowmove', str(wid), str(int(x)), str(int(y))])
    return result is not None and result.returncode == 0


def geometry(win):
    """Текущие (x, y, w, h) окна на экране, либо None."""
    wid = _xid(win)
    if wid is None:
        return None
    result = _run(['xdotool', 'getwindowgeometry', '--shell', str(wid)])
    if result is None or result.returncode != 0:
        return None
    values = {}
    for line in result.stdout.splitlines():
        if '=' in line:
            key, val = line.split('=', 1)
            values[key.strip()] = int(val.strip())
    if all(k in values for k in ('X', 'Y', 'WIDTH', 'HEIGHT')):
        return values['X'], values['Y'], values['WIDTH'], values['HEIGHT']
    return None


def raise_above(win):
    """Поднимает окно над остальными («показать заметки над всеми окнами»)."""
    wid = _xid(win)
    if wid is not None:
        _run(['xdotool', 'windowraise', str(wid)])
    try:
        win.present()
    except Exception:
        pass