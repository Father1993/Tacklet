"""Regression coverage for Alt+S/tray toggling with auxiliary GTK dialogs."""

import unittest
from types import SimpleNamespace

from sticky.app import StickyApp


class ToggleAllTests(unittest.TestCase):
    @staticmethod
    def _note(hidden=False):
        events = []
        note = SimpleNamespace(hidden=hidden)
        window = SimpleNamespace(
            note=note,
            hide_note=lambda: (events.append('hide'), setattr(note, 'hidden', True)),
            show_note=lambda: (events.append('show'), setattr(note, 'hidden', False)),
        )
        return window, events

    @staticmethod
    def _app(windows, save=lambda: None):
        app = SimpleNamespace(get_windows=lambda: windows, schedule_save=save)
        app._note_windows = lambda: StickyApp._note_windows(app)
        return app

    def test_hides_only_visible_notes_and_ignores_settings_dialog(self):
        visible, visible_events = self._note(False)
        already_hidden, hidden_events = self._note(True)
        settings = SimpleNamespace()
        saves = []
        app = self._app([visible, settings, already_hidden],
                        lambda: saves.append('save'))

        StickyApp.toggle_all(app)

        self.assertEqual(visible_events, ['hide'])
        self.assertEqual(hidden_events, [])
        self.assertTrue(visible.note.hidden)
        self.assertTrue(already_hidden.note.hidden)
        self.assertEqual(saves, ['save'])

    def test_shows_all_hidden_notes_and_ignores_settings_dialog(self):
        first, first_events = self._note(True)
        second, second_events = self._note(True)
        app = self._app([first, SimpleNamespace(), second])

        StickyApp.toggle_all(app)

        self.assertEqual(first_events, ['show'])
        self.assertEqual(second_events, ['show'])
        self.assertFalse(first.note.hidden)
        self.assertFalse(second.note.hidden)

    def test_repeated_cycles_keep_auxiliary_windows_out_of_note_actions(self):
        note, events = self._note(False)
        app = self._app([SimpleNamespace(), note])

        StickyApp.toggle_all(app)
        StickyApp.toggle_all(app)

        self.assertEqual(events, ['hide', 'show'])
