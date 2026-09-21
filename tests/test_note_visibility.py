"""Regression checks for saving geometry when a note is hidden."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sticky.note_window import NoteWindow


class NoteVisibilityTests(unittest.TestCase):
    def test_compact_header_button_has_an_explicit_symbolic_image(self):
        button = SimpleNamespace(
            set_child=lambda child: setattr(button, 'child', child),
            set_tooltip_text=lambda text: setattr(button, 'tooltip', text),
            add_css_class=lambda style: setattr(button, 'style', style),
            connect=lambda signal, callback: setattr(button, 'signal', signal),
        )
        image = SimpleNamespace(
            set_pixel_size=lambda size: setattr(image, 'size', size),
        )
        with patch('sticky.note_window.Gtk.Button', return_value=button), \
             patch('sticky.note_window.Gtk.Image.new_from_icon_name', return_value=image) as create_image:
            NoteWindow._mk_icon_button('list-add-symbolic', 'Добавить', lambda: None)

        create_image.assert_called_once_with('list-add-symbolic')
        self.assertIs(button.child, image)
        self.assertEqual(image.size, 16)

    def test_hiding_captures_geometry_before_unmapping(self):
        events = []
        fake_window = SimpleNamespace(
            note=SimpleNamespace(hidden=False),
            update_geometry_from_screen=lambda: events.append('geometry'),
            hide=lambda: events.append('hide'),
        )

        NoteWindow.hide_note(fake_window)

        self.assertEqual(events, ['geometry', 'hide'])
        self.assertTrue(fake_window.note.hidden)

    def test_x11_geometry_uses_only_its_position(self):
        note = SimpleNamespace(x=0, y=0, w=280, h=240)
        fake_window = SimpleNamespace(
            note=note,
            get_visible=lambda: True,
            get_size=lambda orientation: 280 if orientation.value_nick == 'horizontal' else 240,
        )

        with patch('sticky.note_window.platform.supports_geometry', return_value=True), \
             patch('sticky.note_window.platform.geometry', return_value=(500, 300, 308, 269)):
            NoteWindow.update_geometry_from_screen(fake_window)

        self.assertEqual((note.x, note.y), (500, 300))
        self.assertEqual((note.w, note.h), (280, 240))


if __name__ == '__main__':
    unittest.main()
