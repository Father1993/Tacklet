"""Regression test: source uninstall never removes notes by default."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SourceLifecycleTests(unittest.TestCase):
    def test_install_migrates_legacy_code_without_touching_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            legacy = home / '.local/share/tacklet'
            legacy.mkdir(parents=True)
            (legacy / 'notes.json').write_text('{"notes": [{"text": "keep"}]}', encoding='utf-8')
            (legacy / 'tacklet.py').write_text('"""Tacklet legacy launcher."""\n', encoding='utf-8')
            (legacy / 'sticky').mkdir()
            (legacy / 'sticky' / '__init__.py').write_text('', encoding='utf-8')

            env = os.environ | {'HOME': str(home), 'XDG_DATA_HOME': str(home / '.local/share')}
            result = subprocess.run(['bash', str(ROOT / 'install.sh')], env=env,
                                    capture_output=True, text=True, check=False)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((legacy / 'notes.json').read_text(encoding='utf-8'),
                             '{"notes": [{"text": "keep"}]}')
            self.assertFalse((legacy / 'tacklet.py').exists())
            self.assertFalse((legacy / 'sticky').exists())
            self.assertTrue((home / '.local/lib/tacklet/sticky/launcher.py').exists())

    def test_uninstall_keeps_notes_and_removes_owned_files(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            data = home / '.local/share/tacklet'
            app = home / '.local/lib/tacklet'
            bin_dir = home / '.local/bin'
            applications = home / '.local/share/applications'
            data.mkdir(parents=True)
            app.mkdir(parents=True)
            bin_dir.mkdir(parents=True)
            applications.mkdir(parents=True)
            (data / 'notes.json').write_text('{"notes": []}', encoding='utf-8')
            (app / 'tacklet.py').write_text('', encoding='utf-8')
            (bin_dir / 'tacklet').symlink_to(app / 'tacklet.py')
            desktop = applications / 'io.github.father1993.Tacklet.desktop'
            desktop.write_text('[Desktop Entry]\n', encoding='utf-8')

            env = os.environ | {'HOME': str(home), 'XDG_DATA_HOME': str(home / '.local/share')}
            result = subprocess.run(['bash', str(ROOT / 'uninstall.sh')], env=env,
                                    capture_output=True, text=True, check=False)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((data / 'notes.json').exists())
            self.assertFalse(app.exists())
            self.assertFalse((bin_dir / 'tacklet').exists())
            self.assertFalse(desktop.exists())
