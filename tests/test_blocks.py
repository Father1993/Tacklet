"""Headless regressions for code copy and checklist mutations."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sticky import blocks
from sticky.blocks import ChecklistBlock, CodeBlock


class BlocksTests(unittest.TestCase):
    def test_copy_uses_the_gtk_clipboard_for_this_code_block(self):
        clipboard = SimpleNamespace(set_text=lambda text: setattr(clipboard, 'text', text))
        display = SimpleNamespace(get_clipboard=lambda: clipboard)
        button = SimpleNamespace(set_label=lambda text: setattr(button, 'label', text))
        card = SimpleNamespace(block={'text': 'git status\n'}, _copy_button=button,
                               _reset_copy_label=lambda: False)

        with patch('sticky.blocks.Gdk.Display.get_default', return_value=display), \
             patch('sticky.blocks.GLib.timeout_add') as timeout:
            CodeBlock._copy(card)

        self.assertEqual(clipboard.text, 'git status\n')
        self.assertEqual(button.label, 'Copied')
        timeout.assert_called_once_with(1200, card._reset_copy_label)

    def test_enter_inserts_an_empty_checklist_item_after_current(self):
        first = {'id': 'first', 'text': 'Проверить CI', 'checked': False}
        events = []
        card = SimpleNamespace(
            block={'items': [first]},
            _render_items=lambda: events.append('render'),
            changed=lambda: events.append('save'),
            _focus_item=lambda _id: False,
        )
        card._add_item = lambda after: ChecklistBlock._add_item(card, after)
        with patch('sticky.blocks.GLib.idle_add') as idle:
            handled = ChecklistBlock._on_item_key(
                card, None, blocks.Gdk.KEY_Return, 0, 0, first)

        self.assertTrue(handled)
        self.assertEqual(len(card.block['items']), 2)
        self.assertEqual(events, ['render', 'save'])
        idle.assert_called_once()

    def test_delete_removes_only_the_selected_checklist_item(self):
        first = {'id': 'first', 'text': 'A', 'checked': False}
        second = {'id': 'second', 'text': 'B', 'checked': False}
        events = []
        card = SimpleNamespace(
            block={'items': [first, second]},
            _render_items=lambda: events.append('render'),
            changed=lambda: events.append('save'),
        )

        ChecklistBlock._delete_item(card, first)

        self.assertEqual(card.block['items'], [second])
        self.assertEqual(events, ['render', 'save'])
