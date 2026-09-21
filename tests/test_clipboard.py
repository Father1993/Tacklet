"""Регрессия создания заметки из асинхронного GTK clipboard callback."""

import unittest

from sticky.app import StickyApp


class ClipboardCallbackTests(unittest.TestCase):
    def test_clipboard_text_becomes_new_note_content(self):
        class Clipboard:
            @staticmethod
            def read_text_finish(_result):
                return 'Copied text\nsecond line'

        class App:
            created_text = None

            def new_note(self, text=''):
                self.created_text = text

        app = App()
        StickyApp._on_clipboard_text_ready(app, Clipboard(), object())
        self.assertEqual(app.created_text, 'Copied text\nsecond line')


if __name__ == '__main__':
    unittest.main()
