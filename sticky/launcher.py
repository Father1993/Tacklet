"""CLI entry point; choose the graphics backend before GTK is imported."""

import os
import sys


def main():
    force_x11 = '--x11' in sys.argv
    force_wayland = '--wayland' in sys.argv
    if force_x11 and force_wayland:
        raise SystemExit('Use either --x11 or --wayland, not both.')

    for option in ('--x11', '--wayland'):
        if option in sys.argv:
            sys.argv.remove(option)

    # GNOME Wayland deliberately leaves the placement of application windows
    # to the compositor. XWayland is therefore the default: it lets Tacklet
    # restore the saved position of every note with xdotool. An explicitly
    # selected GDK_BACKEND is respected for packaging and debugging.
    if force_x11 or (not force_wayland and 'GDK_BACKEND' not in os.environ):
        os.environ['GDK_BACKEND'] = 'x11'
    elif force_wayland:
        os.environ['GDK_BACKEND'] = 'wayland'

    from .main import main as run
    return run()
