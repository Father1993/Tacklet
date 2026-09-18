"""CLI entry point; set the graphics backend before GTK is imported."""

import os
import sys


def main():
    if '--x11' in sys.argv:
        sys.argv.remove('--x11')
        os.environ['GDK_BACKEND'] = 'x11'

    from .main import main as run
    return run()
