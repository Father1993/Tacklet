"""Keep public package metadata aligned with the application contract."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageMetadataTests(unittest.TestCase):
    def test_debian_control_declares_runtime_requirements(self):
        control = (ROOT / 'debian/control').read_text(encoding='utf-8')
        self.assertIn('Architecture: all', control)
        self.assertIn('python3-gi', control)
        self.assertIn('gir1.2-gtk-4.0 (>= 4.10)', control)
        self.assertIn('xdotool', control)

    def test_package_installs_both_public_commands(self):
        install = (ROOT / 'debian/tacklet.install').read_text(encoding='utf-8')
        self.assertIn('debian/tacklet usr/bin', install)
        self.assertIn('debian/tacklet-update usr/bin', install)
