"""Основное Gtk-приложение: управление заметками, хоткеем, треем и сохранением."""

import gi

gi.require_version('Gdk', '4.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gdk, Gio, GLib, Gtk

from . import storage
from .hotkey import (GnomeShortcut, new_note_from_clipboard_command,
                     toggle_command)
from .note_window import NoteWindow
from .settings_dialog import SettingsDialog
from .tray import StatusNotifierItem


class StickyApp(Gtk.Application):
    def __init__(self, launcher_path):
        super().__init__(application_id='io.github.father1993.Tacklet')
        self._held = False

        self.config = storage.AppConfig()
        self.notes = []

        self._save_timer = None
        self._hotkey = GnomeShortcut(toggle_command(launcher_path),
                                     new_note_from_clipboard_command())
        self._settings = None
        self._tray = None

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action('app.quit', ['<Control>q'])

        toggle_action = Gio.SimpleAction.new('toggle-all', None)
        toggle_action.connect('activate', lambda *_: self.toggle_all())
        self.add_action(toggle_action)

        new_note_action = Gio.SimpleAction.new('new-note', None)
        new_note_action.connect('activate', lambda *_: self.new_note())
        self.add_action(new_note_action)

        paste_note_action = Gio.SimpleAction.new('new-from-clipboard', None)
        paste_note_action.connect('activate', lambda *_: self.new_note_from_clipboard())
        self.add_action(paste_note_action)

        preferences_action = Gio.SimpleAction.new('preferences', None)
        preferences_action.connect('activate', lambda *_: self.open_settings())
        self.add_action(preferences_action)

        self.connect('shutdown', self._on_shutdown)

    # ---- запуск ----------------------------------------------------------

    def do_startup(self):
        Gtk.Application.do_startup(self)
        # Скрытые окна GTK не удерживают приложение живым. Без hold() вместе с
        # последней скрытой заметкой исчезали трей и глобальная клавиша.
        self.hold()
        self._held = True

    def do_activate(self):
        note_windows = [w for w in self.get_windows() if hasattr(w, 'note')]
        if note_windows:
            visible = [w for w in note_windows if not w.note.hidden]
            if visible:
                for window in visible:
                    window.present()
            else:
                print('[app] все заметки скрыты — показываю при активации')
                for window in note_windows:
                    window.show_note()
            return

        state = storage.load()
        self.config = state.config
        self.notes = state.notes

        for note in self.notes:
            NoteWindow(self, note)

        if not self.notes:
            self.new_note()
        else:
            for window in self.get_windows():
                if hasattr(window, 'note') and not window.note.hidden:
                    window.show_note()

        self._start_tray()
        if self.config.hotkey_enabled:
            self._hotkey.enable()
        self.schedule_save()

    def _start_tray(self):
        if self._tray is not None:
            return
        self._tray = StatusNotifierItem(Gio.bus_get_sync(Gio.BusType.SESSION, None))
        self._tray.set_menu([
            (1, 'Показать / скрыть все', self.toggle_all),
            (2, 'Новая заметка', self.new_note),
            (3, 'Новая заметка из буфера (Alt+V)', self.new_note_from_clipboard),
            (4, 'Настройки', self.open_settings),
            (5, '---', None),
            (6, 'Завершить программу', self.quit_tray),
        ])
        self._tray.start()

    def _stop_tray(self):
        if self._tray is not None:
            self._tray.stop()
            self._tray = None

    def quit_tray(self):
        self.quit()

    # ---- заметки ----------------------------------------------------------

    def new_note(self, text=''):
        count = len(self.notes)
        note = storage.NoteData(
            text=text or '',
            x=90 + (count % 8) * 28,
            y=90 + (count % 8) * 28,
            color=self.config.color,
            font_size=self.config.font_size,
            opacity=self.config.opacity,
        )
        self.notes.append(note)
        window = NoteWindow(self, note)
        window.show_note()
        GLib.idle_add(window.focus_editor)
        self.schedule_save()
        return note

    def new_note_from_clipboard(self):
        """Создаёт заметку с текстом из системного буфера обмена GTK4.

        Чтение асинхронное, поэтому не блокирует главный цикл и работает в
        Wayland без X11-утилит или прямого доступа к буферу другого клиента.
        """
        display = Gdk.Display.get_default()
        if display is None:
            self.new_note()
            return
        clipboard = display.get_clipboard()
        clipboard.read_text_async(None, self._on_clipboard_text_ready)

    def _on_clipboard_text_ready(self, clipboard, result, *_):
        try:
            text = clipboard.read_text_finish(result)
        except GLib.Error as exc:
            print('[clipboard] не удалось прочитать текст:', exc)
            text = None
        self.new_note(text)

    def delete_note(self, window):
        if window.note in self.notes:
            self.notes.remove(window.note)
        window.destroy()
        if not self.notes:
            self.new_note()
        self.schedule_save()

    def restore_note(self, note):
        window = NoteWindow(self, note)
        if not note.hidden:
            window.show_note()
        return window

    # ---- показ/скрытие по Alt+S -----------------------------------------

    def toggle_all(self):
        windows = self.get_windows()
        any_visible = any(getattr(w, 'note', None) and not w.note.hidden for w in windows)
        if any_visible:
            for window in windows:
                window.hide_note()
        else:
            for window in windows:
                window.show_note()
        self.schedule_save()

    # ---- применение настроек ---------------------------------------------

    def apply_opacity(self, value):
        self.config.opacity = value
        for window in self.get_windows():
            window.note.opacity = value
            window.refresh_opacity()
        self.schedule_save()

    def apply_font_size(self, value):
        self.config.font_size = value
        for window in self.get_windows():
            window.note.font_size = value
            window._render_css()
        self.schedule_save()

    def apply_color(self, hex_color):
        self.config.color = hex_color
        for window in self.get_windows():
            window.note.color = hex_color
            window._render_css()
        self.schedule_save()

    def open_settings(self):
        if self._settings is None:
            self._settings = SettingsDialog(self)
        self._settings.present()

    def apply_hotkey_enabled(self, enabled):
        """Включает/выключает собственную привязку Alt+S в GNOME."""
        success = self._hotkey.enable() if enabled else self._hotkey.disable()
        if not success:
            print('[hotkey] GNOME custom keybindings недоступны')
            return False
        self.config.hotkey_enabled = bool(enabled)
        self.schedule_save()
        return True

    # ---- сохранение -------------------------------------------------------

    def schedule_save(self):
        """Сохраняет с задержкой, чтобы не писать файл на каждое нажатие."""
        if self._save_timer is not None:
            GLib.source_remove(self._save_timer)
        self._save_timer = GLib.timeout_add(500, self._flush_save)

    def _flush_save(self):
        self._save_timer = None
        for window in self.get_windows():
            note = getattr(window, 'note', None)
            if note is not None:
                window.sync_to_note()
                window.update_geometry_from_screen()
        storage.save(storage.AppState(self.config, self.notes))
        return GLib.SOURCE_REMOVE

    def _on_shutdown(self, *_):
        if self._save_timer is not None:
            GLib.source_remove(self._save_timer)
            self._save_timer = None
            self._flush_save()
        self._stop_tray()
        if self._held:
            self.release()
            self._held = False
