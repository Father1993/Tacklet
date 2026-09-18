"""Точка входа приложения."""

import os
import sys

from gi.repository import GLib


def _launcher_path():
    """Абсолютный путь к скрипту запуска (для .desktop-файла)."""
    if sys.argv and sys.argv[0] and os.path.isabs(sys.argv[0]):
        return sys.argv[0]
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, '..', 'tacklet.py'))


def main(argv=None):
    from .app import StickyApp
    app = StickyApp(launcher_path=_launcher_path())

    # Режим самотестирования: STICKY_SMOKE=<сек> завершает приложение сам.
    smoke = os.environ.get('STICKY_SMOKE')
    if smoke is not None:
        try:
            delay_ms = int(float(smoke) * 1000)
        except ValueError:
            delay_ms = 4000
        GLib.timeout_add(delay_ms, lambda: (app.quit(), GLib.SOURCE_REMOVE)[1])

    return app.run(argv if argv is not None else sys.argv)


if __name__ == '__main__':
    sys.exit(main())
