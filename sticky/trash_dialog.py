"""Recover deleted notes retained for 30 days."""

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


class TrashDialog(Gtk.Window):
    def __init__(self, app):
        super().__init__(application=app, title='Корзина заметок')
        self.app = app
        self.set_default_size(420, 360)
        self.set_hide_on_close(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        self.set_child(box)

        title = Gtk.Label()
        title.set_markup('<span size="x-large"><b>Корзина</b></span>')
        title.set_xalign(0)
        box.append(title)

        hint = Gtk.Label(label='Удалённые заметки хранятся 30 дней, затем удаляются автоматически.')
        hint.set_wrap(True)
        hint.set_xalign(0)
        hint.set_opacity(0.7)
        box.append(hint)

        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class('boxed-list')
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self._list)
        box.append(scroll)

        close = Gtk.Button(label='Закрыть')
        close.set_halign(Gtk.Align.END)
        close.connect('clicked', lambda *_: self.close())
        box.append(close)

    def refresh(self):
        while row := self._list.get_first_child():
            self._list.remove(row)

        if not self.app.trash:
            empty = Gtk.Label(label='Корзина пуста')
            empty.set_margin_top(18)
            empty.set_margin_bottom(18)
            self._list.append(empty)
            return

        for entry in reversed(self.app.trash):
            row = Gtk.Box(spacing=8)
            row.set_margin_top(6)
            row.set_margin_bottom(6)
            row.set_margin_start(8)
            row.set_margin_end(8)

            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            details.set_hexpand(True)
            name = Gtk.Label(label=entry.note.title or 'Без названия')
            name.set_xalign(0)
            details.append(name)
            date = Gtk.Label(label=f'Удалена: {entry.deleted_at[:10]}')
            date.set_xalign(0)
            date.set_opacity(0.65)
            details.append(date)
            row.append(details)

            restore = Gtk.Button(label='Восстановить')
            restore.connect('clicked', lambda _, item=entry: self._restore(item))
            row.append(restore)
            delete = Gtk.Button()
            delete.set_icon_name('user-trash-symbolic')
            delete.set_tooltip_text('Удалить навсегда')
            delete.add_css_class('destructive-action')
            delete.connect('clicked', lambda _, item=entry: self._remove(item))
            row.append(delete)
            self._list.append(row)

    def _restore(self, entry):
        self.app.restore_from_trash(entry)
        self.refresh()

    def _remove(self, entry):
        self.app.remove_from_trash(entry)
        self.refresh()
