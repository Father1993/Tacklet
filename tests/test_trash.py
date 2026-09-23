"""Regression checks for the 30-day deleted-note history."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sticky.app import StickyApp
from sticky.storage import NoteData, TrashEntry, prune_trash


class TrashTests(unittest.TestCase):
    def test_expired_entry_is_pruned_after_thirty_days(self):
        old = TrashEntry(
            note=NoteData(text='old'),
            deleted_at=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        )
        fresh = TrashEntry(note=NoteData(text='fresh'))
        self.assertEqual(prune_trash([old, fresh]), [fresh])

    def test_deleting_a_note_moves_it_to_trash_before_destroying_window(self):
        note = NoteData(title='План')
        spare = NoteData(title='Запасная')
        events = []
        app = SimpleNamespace(notes=[note, spare], trash=[],
                              schedule_save=lambda: events.append('save'))
        window = SimpleNamespace(note=note,
                                 sync_to_note=lambda: events.append('sync'),
                                 update_geometry_from_screen=lambda: events.append('geometry'),
                                 destroy=lambda: events.append('destroy'))

        StickyApp.delete_note(app, window)

        self.assertEqual(events, ['sync', 'geometry', 'destroy', 'save'])
        self.assertEqual(app.notes, [spare])
        self.assertEqual(app.trash[0].note, note)

    def test_restoring_returns_note_to_active_collection(self):
        entry = TrashEntry(note=NoteData(title='Вернуть'))
        restored = []
        app = SimpleNamespace(
            notes=[], trash=[entry],
            restore_note=lambda note: restored.append(note),
            schedule_save=lambda: None,
        )

        StickyApp.restore_from_trash(app, entry)

        self.assertEqual(app.notes, [entry.note])
        self.assertEqual(app.trash, [])
        self.assertEqual(restored, [entry.note])
        self.assertFalse(entry.note.hidden)

    def test_trash_keeps_embedded_blocks_for_recovery(self):
        note = NoteData(blocks=[
            {'id': 'code', 'kind': 'code', 'text': 'git status'},
            {'id': 'checks', 'kind': 'checklist', 'items': [
                {'id': 'ci', 'text': 'CI', 'checked': True},
            ]},
        ])
        restored = TrashEntry.from_dict(TrashEntry(note).to_dict())

        self.assertEqual(restored.note.blocks[0]['text'], 'git status')
        self.assertTrue(restored.note.blocks[1]['items'][0]['checked'])


if __name__ == '__main__':
    unittest.main()
