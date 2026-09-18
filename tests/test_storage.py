"""Регрессии формата данных заметок без запуска графической оболочки."""

import unittest
import json
import tempfile
from pathlib import Path

from sticky import storage
from sticky.storage import AppConfig, NoteData


class StorageTests(unittest.TestCase):
    def test_keeps_zero_coordinates(self):
        note = NoteData.from_dict({'x': 0, 'y': 0, 'w': 0, 'h': 0})
        self.assertEqual((note.x, note.y), (0, 0))
        self.assertEqual((note.w, note.h), (180, 140))

    def test_local_font_formats_are_normalized(self):
        note = NoteData.from_dict({
            'text': 'привет',
            'formats': [
                {'start': 1, 'end': 5, 'font_size': 24},
                {'start': -1, 'end': 99, 'font_size': 'bad'},
                {'start': 3, 'end': 3, 'font_size': 18},
                'not a format',
            ],
        })
        self.assertEqual(note.formats, [
            {'start': 1, 'end': 5, 'font_size': 24},
            {'start': 0, 'end': 6, 'font_size': 14},
        ])

    def test_invalid_config_does_not_prevent_startup(self):
        config = AppConfig.from_dict({
            'opacity': 'invalid',
            'font_size': None,
            'color': 'invalid',
        })
        self.assertEqual(config.opacity, 0.85)
        self.assertEqual(config.font_size, 14)
        self.assertEqual(config.color, '#fdf6d8')

    def test_non_object_config_uses_defaults(self):
        self.assertEqual(AppConfig.from_dict(['not', 'a', 'mapping']).font_size, 14)

    def test_imports_legacy_data_once_new_path_is_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = storage.NOTES_FILE, storage.LEGACY_NOTES_FILE
            storage.NOTES_FILE = root / 'tacklet' / 'notes.json'
            storage.LEGACY_NOTES_FILE = root / 'sticky-notes' / 'notes.json'
            storage.LEGACY_NOTES_FILE.parent.mkdir()
            storage.LEGACY_NOTES_FILE.write_text(json.dumps({
                'config': {}, 'notes': [{'text': 'remember me'}],
            }), encoding='utf-8')
            try:
                state = storage.load()
            finally:
                storage.NOTES_FILE, storage.LEGACY_NOTES_FILE = original
        self.assertEqual([note.text for note in state.notes], ['remember me'])


if __name__ == '__main__':
    unittest.main()
