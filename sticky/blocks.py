"""Reusable GTK sections embedded below a Tacklet note's main text."""

import gi

gi.require_version('Gdk', '4.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gdk, GLib, Gtk

from . import storage


class NoteBlocks(Gtk.Box):
    """Render and edit the code/checklist blocks owned by one NoteData."""

    def __init__(self, app, note):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.app = app
        self.note = note
        self.add_css_class('note-blocks')
        for block in self.note.blocks:
            self._append_card(block)

    def add_code(self):
        self._add_block('code')

    def add_checklist(self):
        self._add_block('checklist')

    def _add_block(self, kind):
        block = storage.new_block(kind)
        self.note.blocks.append(block)
        self._append_card(block)
        self.app.schedule_save()

    def remove_block(self, card):
        self.note.blocks.remove(card.block)
        self.remove(card)
        self.app.schedule_save()

    def _append_card(self, block):
        if block['kind'] == 'code':
            self.append(CodeBlock(self, block))
        elif block['kind'] == 'checklist':
            self.append(ChecklistBlock(self, block))


class _BlockCard(Gtk.Box):
    def __init__(self, owner, block, title):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.owner = owner
        self.block = block
        self.add_css_class('note-block')

        header = Gtk.Box(spacing=4)
        header.add_css_class('note-block-header')
        label = Gtk.Label(label=title)
        label.set_xalign(0)
        label.set_hexpand(True)
        label.add_css_class('note-block-title')
        header.append(label)
        self.header = header
        self.append(header)

        delete = Gtk.Button(label='×')
        delete.set_tooltip_text('Удалить блок')
        delete.add_css_class('flat')
        delete.connect('clicked', lambda *_: self.owner.remove_block(self))
        header.append(delete)

    def changed(self):
        self.owner.app.schedule_save()


class CodeBlock(_BlockCard):
    def __init__(self, owner, block):
        super().__init__(owner, block, 'Code snippet')
        copy = Gtk.Button(label='Copy')
        copy.set_tooltip_text('Скопировать code snippet')
        copy.add_css_class('flat')
        copy.connect('clicked', self._copy)
        self.header.prepend(copy)
        self._copy_button = copy

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(88)
        scroll.set_max_content_height(220)
        scroll.add_css_class('note-code-scroll')

        view = Gtk.TextView()
        view.set_monospace(True)
        view.set_wrap_mode(Gtk.WrapMode.NONE)
        view.set_left_margin(8)
        view.set_right_margin(8)
        view.set_top_margin(6)
        view.set_bottom_margin(6)
        view.add_css_class('note-code')
        buffer = view.get_buffer()
        buffer.set_text(block['text'])
        buffer.connect('changed', self._on_changed)
        scroll.set_child(view)
        self.append(scroll)
        self._buffer = buffer

    def _on_changed(self, *_):
        start = self._buffer.get_start_iter()
        end = self._buffer.get_end_iter()
        self.block['text'] = self._buffer.get_text(start, end, True)
        self.changed()

    def _copy(self, *_):
        display = Gdk.Display.get_default()
        if display is None:
            return
        display.get_clipboard().set(self.block['text'])
        self._copy_button.set_label('Copied')
        GLib.timeout_add(1200, self._reset_copy_label)

    def _reset_copy_label(self):
        self._copy_button.set_label('Copy')
        return GLib.SOURCE_REMOVE


class ChecklistBlock(_BlockCard):
    def __init__(self, owner, block):
        super().__init__(owner, block, 'Чек-лист')
        self._rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._item_widgets = {}
        self.append(self._rows)

        add = Gtk.Button(label='+ Пункт')
        add.set_halign(Gtk.Align.START)
        add.add_css_class('flat')
        add.connect('clicked', lambda *_: self._add_item())
        self.append(add)
        for item in self.block['items']:
            self._insert_row(item)

    def _insert_row(self, item, after=None):
        row = Gtk.Box(spacing=4)
        row.add_css_class('note-checklist-row')
        check = Gtk.CheckButton()
        check.set_active(item['checked'])
        check.connect('toggled', self._on_toggled, item)
        row.append(check)

        entry = Gtk.Entry()
        entry.set_text(item['text'])
        entry.set_hexpand(True)
        entry.set_placeholder_text('Пункт списка')
        entry.connect('changed', self._on_text_changed, item)
        key = Gtk.EventControllerKey()
        key.connect('key-pressed', self._on_item_key, item)
        entry.add_controller(key)
        row.append(entry)

        delete = Gtk.Button(label='×')
        delete.set_tooltip_text('Удалить пункт')
        delete.add_css_class('flat')
        delete.connect('clicked', lambda *_: self._delete_item(item))
        row.append(delete)

        if after is None:
            self._rows.append(row)
        else:
            sibling, _ = self._item_widgets[after['id']]
            self._rows.insert_child_after(row, sibling)
        self._item_widgets[item['id']] = (row, entry)

    def _on_toggled(self, button, item):
        item['checked'] = button.get_active()
        self.changed()

    def _on_text_changed(self, entry, item):
        item['text'] = entry.get_text()
        self.changed()

    def _on_item_key(self, _controller, keyval, _keycode, _state, item):
        if keyval != Gdk.KEY_Return:
            return False
        self._add_item(item)
        return True

    def _add_item(self, after=None):
        item = storage.new_checklist_item()
        if after is None:
            self.block['items'].append(item)
        else:
            index = self.block['items'].index(after)
            self.block['items'].insert(index + 1, item)
        self._insert_row(item, after)
        self.changed()
        GLib.idle_add(self._focus_item, item['id'])

    def _delete_item(self, item):
        if item in self.block['items']:
            self.block['items'].remove(item)
            row, _ = self._item_widgets.pop(item['id'])
            self._rows.remove(row)
            self.changed()

    def _focus_item(self, item_id):
        widgets = self._item_widgets.get(item_id)
        if widgets is not None:
            _, entry = widgets
            entry.grab_focus()
        return GLib.SOURCE_REMOVE
