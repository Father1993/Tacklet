"""Regressions for delayed writes and recovery paths."""

from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from sticky import storage
from sticky.app import StickyApp
from gi.repository import GLib, Gtk


class AutosaveTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        folder = Path(stack.enter_context(TemporaryDirectory()))
        self.notes_file = folder / 'tacklet' / 'notes.json'
        self.legacy_file = folder / 'sticky-notes' / 'notes.json'
        stack.enter_context(patch.multiple(storage, NOTES_FILE=self.notes_file,
                                           LEGACY_NOTES_FILE=self.legacy_file))
        self.app = StickyApp('/usr/bin/tacklet')
        stack.enter_context(patch.object(self.app, '_start_tray'))
        stack.enter_context(patch.object(self.app._hotkey, 'enable'))
        self.alert = stack.enter_context(patch.object(self.app, '_show_file_error'))
        self.addCleanup(self.app._cancel_save)

    def test_no_existing_file_is_a_first_launch(self):
        self.assertEqual(storage.load(), storage.AppState())

    def test_corrupt_file_is_preserved_on_startup_and_exit(self):
        self.notes_file.parent.mkdir()
        original = b'{"notes": [{"text": "keep the original bytes'
        self.notes_file.write_bytes(original)
        storage.export_file(self.legacy_file, storage.AppState(notes=[
            storage.NoteData(text='older data'),
        ]))
        with patch('sticky.app.NoteWindow'), patch('sticky.app.GLib.idle_add'):
            self.app.do_activate()
        self.app._flush_save()
        self.app.notes[0].text = 'new work from this session'
        self.app.schedule_save()
        self.app._on_shutdown()

        self.assertEqual(self.notes_file.read_bytes(), original)
        self.assertEqual(sorted(self.notes_file.parent.glob('notes-recovery-*.json')),
                         [self.app._recovery_path])
        recovery = storage.load_file(self.app._recovery_path)
        self.assertEqual(recovery.notes[0].text, 'new work from this session')
        self.assertEqual(self.app._recovery_path.stat().st_mode & 0o777, 0o600)
        self.alert.assert_called_once()

        dialog = Mock()
        dialog.get_file().get_path.return_value = str(self.notes_file)
        self.app._on_export_response(dialog, Gtk.ResponseType.ACCEPT)
        self.assertEqual(self.notes_file.read_bytes(), original)
        dialog.destroy.assert_called_once()

    def test_read_error_does_not_select_the_older_store(self):
        with patch.object(Path, 'read_text', side_effect=PermissionError):
            with self.assertRaises(storage.NotesLoadError) as error:
                storage.load()
        self.assertEqual(error.exception.source, self.notes_file)

    def test_export_cancels_pending_save_and_next_edit_survives_exit(self):
        note = storage.NoteData(text='before export')
        self.app.notes = [note]
        self.app.schedule_save()
        context = GLib.MainContext.default()
        first_timer = context.find_source_by_id(self.app._save_timer)

        with patch('sticky.app.Gtk.FileChooserNative.new', return_value=Mock()), \
             patch.object(storage, 'save', wraps=storage.save) as save:
            self.app.export_notes()
            self.assertTrue(first_timer.is_destroyed())
            self.assertEqual(save.call_count, 1)
            note.text = 'after export'
            self.app.schedule_save()
            self.app._on_shutdown()
            self.assertEqual(save.call_count, 2)

        self.assertEqual(storage.load().notes[0].text, 'after export')
