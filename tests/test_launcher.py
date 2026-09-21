"""Tests for backend selection before GTK is imported."""

import os
import sys
import types
import unittest
from unittest.mock import patch

from sticky import launcher


class LauncherTests(unittest.TestCase):
    def _run_launcher(self, args, backend=None):
        previous_backend = os.environ.get('GDK_BACKEND')
        if backend is None:
            os.environ.pop('GDK_BACKEND', None)
        else:
            os.environ['GDK_BACKEND'] = backend

        observed = []
        fake_main = types.ModuleType('sticky.main')
        fake_main.main = lambda: observed.append(os.environ.get('GDK_BACKEND'))
        try:
            with patch.object(sys, 'argv', ['tacklet', *args]), patch.dict(
                    sys.modules, {'sticky.main': fake_main}):
                launcher.main()
        finally:
            if previous_backend is None:
                os.environ.pop('GDK_BACKEND', None)
            else:
                os.environ['GDK_BACKEND'] = previous_backend
        return observed

    def test_x11_is_the_default_for_reliable_position_restore(self):
        self.assertEqual(self._run_launcher([]), ['x11'])

    def test_wayland_is_an_explicit_opt_in(self):
        self.assertEqual(self._run_launcher(['--wayland']), ['wayland'])

    def test_explicit_backend_environment_is_respected(self):
        self.assertEqual(self._run_launcher([], backend='broadway'), ['broadway'])

    def test_conflicting_backend_options_fail_before_startup(self):
        with patch.object(sys, 'argv', ['tacklet', '--x11', '--wayland']):
            with self.assertRaises(SystemExit):
                launcher.main()


if __name__ == '__main__':
    unittest.main()
